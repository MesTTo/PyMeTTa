"""Purpose: validate, write, replace, and load named-space snapshots.
Guarantees:
  - a completed sibling is synced before it replaces the destination
    [tested test_save_syncs_before_replacing]
  - validation and write failures preserve the old destination [tested
    test_save_validation_preserves_existing_file,
    test_text_save_write_failure_preserves_existing_file]
  - fast cache headers are validated before payload loading [tested
    test_fast_load_refuses_a_different_swi_version_before_payload]
  - text snapshots use UTF-8 regardless of the process locale [tested
    test_text_save_uses_utf8_for_plain_and_gzip_files]
  - the save format type admits exactly metta and fast [tested
    test_public_context_types_are_distinct]
Owns:
  - save_space owns one sibling temporary file and removes it after every
    failed or successful save [tested test_save_failure_preserves_existing_file]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import gzip
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Literal

from ._api_types import SaveFormat
from ._engine import Runtime
from ._space_objects import _limits
from .atoms import Atom, Expr, Gnd, Sym, atom_from_wire
from .errors import EngineError, ResourceLimitError

_FAST_PREFIX = b"PETTA-CACHE\t"
_FAST_ERRORS = (
    "petta_fast_header_mismatch",
    "petta_fast_integrity_header",
    "petta_fast_integrity_mismatch",
    "petta_fast_read_failed",
    "petta_fast_payload_not_atom_list",
)


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
        prefix=".petta-save-", suffix=target.suffix, dir=target.parent
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
        if isinstance(current, Gnd) and not isinstance(current.value, (bool, int, float, str)):
            return False
        if isinstance(current, Expr):
            stack.extend(current.children)
    return True


def _symbol_names(atoms: list[Atom]) -> list[str]:
    """Every distinct symbol name in these atoms, first appearance first."""
    names: list[str] = []
    seen: set[str] = set()
    stack = list(reversed(atoms))
    while stack:
        current = stack.pop()
        if isinstance(current, Sym):
            if current.name not in seen:
                seen.add(current.name)
                names.append(current.name)
        elif isinstance(current, Expr):
            stack.extend(reversed(current.children))
    return names


def raise_unsafe_text_symbol(symbol: Atom, operation: str) -> None:
    name = symbol.name if isinstance(symbol, Sym) else str(symbol)
    reason = (
        "the empty symbol writes as nothing at all, so its term reads back "
        "one element shorter"
        if not name
        else (
            "the text form reads back as something else: a number, a "
            "variable, a boolean, a string, or more than one atom"
        )
    )
    raise ValueError(f"{operation} cannot write symbol {name!r} as MeTTa text: {reason}")


def _validate_atoms(rt: Runtime, atoms: list[Atom]) -> None:
    for atom in atoms:
        if not serializable(atom):
            raise ValueError(
                f"{atom} carries a live Python object; a file cannot hold it. "
                f"Remove it, or persist its data explicitly."
            )
    # Which spellings survive a round trip is the grammar's question, so the
    # engine answers it. A blacklist kept here missed a leading $, which reads
    # back as a variable, a semicolon, which starts a comment, and any name
    # spelled like a number or a boolean.
    names = _symbol_names(atoms)
    if names:
        row = rt.once("petta_py_unwritable_name(Names, Bad)", Names=names)
        if row:
            raise_unsafe_text_symbol(Sym(str(row["Bad"])), "save")


def _write_fast(rt: Runtime, space: str, temporary: Path) -> int:
    result = rt.apply_must("petta_py_fast_save", str(temporary), space)
    if not isinstance(result, list) or len(result) != 2:
        raise EngineError(f"petta_py_fast_save returned an invalid result: {result!r}")
    kind, value = result
    if kind == "object":
        atom = atom_from_wire(value)
        raise ValueError(
            f"{atom} carries a live Python object; a file cannot hold it. "
            f"Remove it, or persist its data explicitly."
        )
    if kind == "symbol":
        raise_unsafe_text_symbol(atom_from_wire(value), "save")
    if kind != "saved":
        raise EngineError(f"petta_py_fast_save returned an unknown result: {result!r}")
    return int(value)


def _write_text(temporary: Path, atoms: list[Atom]) -> int:
    with _open_maybe_gz(temporary, "wt") as handle:
        for atom in atoms:
            handle.write(f"{atom}\n")
    return len(atoms)


def save_space(
    rt: Runtime,
    space: str,
    atoms: list[Atom],
    path: str | os.PathLike[str],
    format: SaveFormat,
) -> int:
    """Validate and atomically persist one enumerated space."""
    if format not in ("metta", "fast"):
        raise ValueError(f"save format must be 'metta' or 'fast', got {format!r}")
    _validate_atoms(rt, atoms)
    target = Path(path)
    temporary = _temporary_sibling(target)
    try:
        count = (
            _write_fast(rt, space, temporary) if format == "fast" else _write_text(temporary, atoms)
        )
        _sync_and_replace(temporary, target)
        return count
    finally:
        temporary.unlink(missing_ok=True)


def _fast_header(path: str) -> list[bytes]:
    try:
        with _open_maybe_gz(path, "rb") as handle:
            actual = handle.readline(512)
    except OSError as exc:
        raise EngineError(
            f"cannot read the fast cache header from {path!r}: {exc}; "
            f"re-save the cache from its source data"
        ) from exc
    if not actual.endswith(b"\n"):
        raise _cache_rejection(path, "the header is truncated or malformed")
    fields = actual[:-1].split(b"\t")
    if len(fields) != 5:
        raise _cache_rejection(path, "the header is malformed")
    return fields


def _cache_rejection(path: str, reason: str) -> EngineError:
    return EngineError(
        f"cannot load fast cache {path!r}: {reason}; re-save it with this "
        f"PeTTa and SWI-Prolog version"
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


def _load_fast(rt: Runtime, space: str, path: str, bounds: tuple[float, int]) -> list[list[Atom]]:
    expected = str(rt.apply_must("petta_py_fast_header")).encode("ascii").split(b"\t")
    _validate_fast_header(path, _fast_header(path), expected)
    seconds, steps = bounds
    try:
        rt.must(
            "petta_py_guarded(T, I, petta_py_fast_load(File, Space))",
            T=seconds,
            I=steps,
            File=path,
            Space=space,
        )
    except ResourceLimitError:
        # The caller's own bound stopped it. Reading that as a corrupt cache
        # would blame the file for the budget.
        raise
    except EngineError as exc:
        if not any(tag in str(exc) for tag in _FAST_ERRORS):
            raise EngineError(f"fast load failed while adding atoms from {path!r}: {exc}") from exc
        raise EngineError(
            f"fast load failed for {path!r}: {exc}. The cache is corrupt or "
            f"incomplete; re-save it from the source data."
        ) from exc
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

    Both bounds go through petta_py_guarded/3, the same guard pair
    petta_py_limited applies, with the goal written here rather than named
    as data. petta_py_load is not on the shim's wrappable list, and it does
    not need to be: the whitelist exists so a predicate NAME arriving from
    Python cannot become a call, and this name is in this file's own source.
    """
    file = str(path)
    bounds = _limits(timeout, inferences) or (-1.0, -1)
    try:
        with _open_maybe_gz(file, "rb") as handle:
            is_fast = handle.read(len(_FAST_PREFIX)) == _FAST_PREFIX
    except OSError:
        is_fast = False
    if is_fast:
        return _load_fast(rt, space, file, bounds)
    seconds, steps = bounds
    row = rt.must(
        "petta_py_guarded(T, I, petta_py_load(File, Space, Groups))",
        T=seconds,
        I=steps,
        File=file,
        Space=space,
    )
    return [[atom_from_wire(wire) for wire in group] for group in row.get("Groups", [])]
