"""Purpose: validate, write, replace, and load named-space snapshots.
Guarantees:
  - a completed sibling is synced before it replaces the destination
    [tested: test_save_syncs_before_replacing; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - validation and write failures preserve the old destination [tested
    test_save_validation_preserves_existing_file,
    test_text_save_write_failure_preserves_existing_file; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - fast cache headers are validated before payload loading [tested
    test_fast_load_refuses_a_different_swi_version_before_payload;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - text snapshots use UTF-8 regardless of the process locale [tested
    test_text_save_uses_utf8_for_plain_and_gzip_files; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the save format type admits exactly metta and fast [tested:
    test_canonical_context_types_replace_public_newtypes; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - save validation consumes the generated SaveFormat vocabulary class rather
    than owning a second closed list [tested:
    test_a_planted_closed_policy_list_is_reported_by_the_inventory_lane;
    commit=4d01efe426a5a3b79d404afd993f3260e23a210c]
  - text and fast loads apply a scoped stack byte bound through the /6 seam
    while preserving the established guard path otherwise [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Owns resources:
  - save_space owns one sibling temporary file and removes it after every
    failed or successful save
    [tested: test_save_failure_preserves_existing_file; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import gzip
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Literal

from ._engine import Runtime
from ._space_objects import _apply_limited, _limits
from .atoms import Atom, Expression, Grounded, Handle, Symbol, _atom_from_wire
from .errors import EngineError, ResourceLimitError
from .vocabularies import SaveFormat

_FAST_PREFIX = b"METTA-CACHE\t"
_FAST_ERRORS = (
    "metta_fast_header_mismatch",
    "metta_fast_integrity_header",
    "metta_fast_integrity_mismatch",
    "metta_fast_read_failed",
    "metta_fast_payload_not_atom_list",
)


# policy-inventory-exempt: mechanism-internal; reason=rb and wt are the binary-read and UTF-8 text-write modes required by the gzip adapter; evidence=extensions/python/metta/_space_persistence.py:_open_maybe_gz
def _open_maybe_gz(path: str | os.PathLike[str], mode: Literal["rb", "wt"]):
    """Open gzip paths through gzip and all other paths through open()."""
    file = os.fspath(path)
    compressed = file.endswith(".gz")
    if mode == "rb":
        return gzip.open(file, "rb") if compressed else Path(file).open("rb")
    return (
        gzip.open(file, "wt", encoding="utf-8")
        if compressed
        else Path(file).open("wt", encoding="utf-8")
    )


def _temporary_sibling(target: Path) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=".metta-save-", suffix=target.suffix, dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    if target.exists():
        temporary.chmod(stat.S_IMODE(target.stat().st_mode))
    return temporary


def _sync_and_replace(temporary: Path, target: Path) -> None:
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(target)
    if os.name != "posix":
        return
    descriptor = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def serializable(atom: Atom) -> bool:
    """Whether an atom contains only values with a persistent spelling."""
    stack = [atom]
    while stack:
        current = stack.pop()
        # A Handle is a Grounded species with no payload slot, and it has
        # its own persistent spelling (the space name, the registry id),
        # which is the old walk's behaviour kept exact.
        if (
            isinstance(current, Grounded)
            and not isinstance(current, Handle)
            and not isinstance(current.value, (bool, int, float, str))
        ):
            return False
        if isinstance(current, Expression):
            stack.extend(current.children)
    return True


def raise_unsafe_text_atom(value: Atom, operation: str) -> None:
    """Refuse a value whose printed form does not read back as that value.

    Two classes reach here, and the engine's own
    ``metta_unwritable_symbol/2`` answers for both. A SYMBOL whose spelling
    reads back as a variable, a comment, a number, a boolean, a string or
    more than one atom, MeTTa having no quoted-symbol syntax. And a NUMBER
    whose printed form the reader has no literal for: SWI writes a non-finite
    float as ``1.0Inf``, ``-1.0Inf`` or ``1.5NaN`` and a rational as ``1r3``,
    and each of the four comes back a symbol of that spelling.
    """
    if not isinstance(value, Symbol):
        msg = (
            f"{operation} cannot write {value} as MeTTa text: its printed "
            f"form reads back as a symbol of that spelling rather than as "
            f"the value"
        )
        raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
    reason = (
        "the empty symbol writes as nothing at all, so its term reads back one element shorter"
        if not value.name
        else (
            "the text form reads back as something else: a number, a "
            "variable, a boolean, a string, or more than one atom"
        )
    )
    msg = f"{operation} cannot write symbol {value.name!r} as MeTTa text: {reason}"
    raise ValueError(msg)


def _validate_atoms(
    rt: Runtime, space: str, atoms: list[Atom], bounds: tuple[float, int, int]
) -> None:
    for atom in atoms:
        if not serializable(atom):
            msg = (
                f"{atom} carries a live Python object; a file cannot hold it. "
                f"Remove it, or persist its data explicitly."
            )
            raise ValueError(msg)
    # Which values survive a round trip is the grammar's question, so the
    # engine answers it. A blacklist kept here missed a leading $, which reads
    # back as a variable, a semicolon, which starts a comment, and any name
    # spelled like a number or a boolean; and asking about NAMES alone missed
    # a fourth class that is not a name, a number whose printed form is not
    # read back as that number. The engine enumerates, so no atom crosses the
    # wire for the question.
    seconds, steps, _stack = bounds
    row = rt.once(
        "metta_py_guarded(T, I, metta_py_unwritable_atom(Space, Bad))",
        T=seconds,
        I=steps,
        Space=space,
    )
    if row:
        raise_unsafe_text_atom(_atom_from_wire(row["Bad"]), "save")


def _write_fast(
    rt: Runtime, space: str, temporary: Path, bounds: tuple[float, int, int]
) -> int:
    result = _apply_limited(rt, bounds, "metta_py_fast_save", [str(temporary), space])
    if not isinstance(result, list) or len(result) != 2:
        msg = f"metta_py_fast_save returned an invalid result: {result!r}"
        raise EngineError(msg)
    kind, value = result
    if kind == "object":
        atom = _atom_from_wire(value)
        msg = (
            f"{atom} carries a live Python object; a file cannot hold it. "
            f"Remove it, or persist its data explicitly."
        )
        raise ValueError(msg)
    if kind == "symbol":
        raise_unsafe_text_atom(_atom_from_wire(value), "save")
    if kind != "saved":
        msg = f"metta_py_fast_save returned an unknown result: {result!r}"
        raise EngineError(msg)
    return int(value)


def _write_text(temporary: Path, atoms: list[Atom]) -> int:
    with _open_maybe_gz(temporary, "wt") as handle:
        for atom in atoms:
            handle.write(f"{atom}\n")
    return len(atoms)


def save_space(
    rt: Runtime,
    space: str,
    path: str | os.PathLike[str],
    save_format: SaveFormat,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> int:
    """Validate and atomically persist one space, bounding its engine work.

    The enumeration, the unwritable-atom scan and the fast writer are all
    linear in the space and all run under the caller's bounds, which is why the
    enumeration happens HERE rather than at the call site: an unbounded
    enumeration handed in as an argument is the largest of the three and the
    one a guard could not reach.
    """
    if save_format not in SaveFormat:
        msg = f"save format must be 'metta' or 'fast', got {save_format!r}"
        raise ValueError(msg)
    bounds = _limits(timeout, inferences) or (-1.0, -1, -1)
    atoms = _enumerate(rt, space, bounds)
    _validate_atoms(rt, space, atoms, bounds)
    target = Path(path)
    temporary = _temporary_sibling(target)
    try:
        count = (
            _write_fast(rt, space, temporary, bounds)
            if save_format == "fast"
            else _write_text(temporary, atoms)
        )
        _sync_and_replace(temporary, target)
        return count
    finally:
        temporary.unlink(missing_ok=True)


def _enumerate(rt: Runtime, space: str, bounds: tuple[float, int, int]) -> list[Atom]:
    """Every stored atom of one space, under the caller's bounds."""
    wires = _apply_limited(rt, bounds, "metta_py_atoms", [space])
    return [_atom_from_wire(wire) for wire in wires]


def _fast_header(path: str) -> list[bytes]:
    try:
        with _open_maybe_gz(path, "rb") as handle:
            actual = handle.readline(512)
    except OSError as exc:
        msg = (
            f"cannot read the fast cache header from {path!r}: {exc}; "
            f"re-save the cache from its source data"
        )
        raise EngineError(msg) from exc
    if not actual.endswith(b"\n"):
        raise _cache_rejection(path, "the header is truncated or malformed")
    fields = actual[:-1].split(b"\t")
    if len(fields) != 5:
        raise _cache_rejection(path, "the header is malformed")
    return fields


def _cache_rejection(path: str, reason: str) -> EngineError:
    return EngineError(
        f"cannot load fast cache {path!r}: {reason}; re-save it with this "
        f"MeTTa and SWI-Prolog version"
    )


def _validate_fast_header(path: str, actual: list[bytes], expected: list[bytes]) -> None:
    comparisons = (
        (0, "the cache marker is invalid"),
        (1, f"magic tag {actual[1]!r} does not match {expected[1]!r}"),
        (2, f"format version {actual[2]!r} does not match {expected[2]!r}"),
        (
            3,
            f"SWI-Prolog version {actual[3]!r} does not match the running version {expected[3]!r}",
        ),
    )
    for index, reason in comparisons:
        if actual[index] != expected[index]:
            raise _cache_rejection(path, reason)
    if not re.fullmatch(rb"[0-9a-f]{64}", actual[4]):
        raise _cache_rejection(path, "the integrity hash is malformed")


def _load_fast(
    rt: Runtime,
    space: str,
    path: str,
    bounds: tuple[float, int, int],
) -> list[list[Atom]]:
    expected = str(rt.apply_must("metta_host_fast_header")).encode("ascii").split(b"\t")
    _validate_fast_header(path, _fast_header(path), expected)
    seconds, steps, stack = bounds
    try:
        if stack < 0:
            rt.must(
                "metta_py_guarded(T, I, metta_py_fast_load(File, Space))",
                T=seconds,
                I=steps,
                File=path,
                Space=space,
            )
        else:
            _apply_limited(
                rt,
                bounds,
                "metta_py_fast_load_unit",
                [path, space],
            )
    except ResourceLimitError:
        # The caller's own bound stopped it. Reading that as a corrupt cache
        # would blame the file for the budget.
        raise
    except EngineError as exc:
        if not any(tag in str(exc) for tag in _FAST_ERRORS):
            msg = f"fast load failed while adding atoms from {path!r}: {exc}"
            raise EngineError(msg) from exc
        msg = (
            f"fast load failed for {path!r}: {exc}. The cache is corrupt or "
            f"incomplete; re-save it from the source data."
        )
        raise EngineError(msg) from exc
    return []


def load_space(
    rt: Runtime,
    space: str,
    path: str | os.PathLike[str],
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> list[list[Atom]]:
    """Load a text program or validated fast cache into a named space.

    Time and inference bounds retain the direct guarded path. A scoped stack
    bound selects the explicit ``metta_py_limited/6`` whitelist entry instead,
    so the predicate name remains closed even on the stack-aware route.
    """
    file = str(path)
    bounds = _limits(timeout, inferences) or (-1.0, -1, -1)
    try:
        with _open_maybe_gz(file, "rb") as handle:
            is_fast = handle.read(len(_FAST_PREFIX)) == _FAST_PREFIX
    except OSError:
        is_fast = False
    if is_fast:
        return _load_fast(rt, space, file, bounds)
    seconds, steps, stack = bounds
    if stack < 0:
        row = rt.must(
            "metta_py_guarded(T, I, metta_py_load(File, Space, Groups))",
            T=seconds,
            I=steps,
            File=file,
            Space=space,
        )
        groups = row.get("Groups", [])
    else:
        groups = _apply_limited(rt, bounds, "metta_py_load", [file, space])
    return [[_atom_from_wire(wire) for wire in group] for group in groups]
