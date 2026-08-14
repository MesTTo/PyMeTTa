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

from ._engine import Runtime
from .atoms import Atom, Expr, Gnd, Sym, atom_from_wire
from .errors import EngineError

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


def unsafe_text_symbol(atom: Atom) -> Sym | None:
    """Return the first symbol that has no round-trip MeTTa text spelling."""
    stack = [atom]
    while stack:
        current = stack.pop()
        if isinstance(current, Sym) and any(
            character.isspace() or character in '()"' for character in current.name
        ):
            return current
        if isinstance(current, Expr):
            stack.extend(reversed(current.children))
    return None


def raise_unsafe_text_symbol(symbol: Atom, operation: str) -> None:
    name = symbol.name if isinstance(symbol, Sym) else str(symbol)
    raise ValueError(
        f"{operation} cannot write symbol {name!r} as MeTTa text: symbol "
        f"names containing whitespace, parentheses, or quotes have no "
        f"round-trip text spelling"
    )


def _validate_atoms(atoms: list[Atom]) -> None:
    for atom in atoms:
        if not serializable(atom):
            raise ValueError(
                f"{atom} carries a live Python object; a file cannot hold it. "
                f"Remove it, or persist its data explicitly."
            )
        bad = unsafe_text_symbol(atom)
        if bad is not None:
            raise_unsafe_text_symbol(bad, "save")


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
    format: str,
) -> int:
    """Validate and atomically persist one enumerated space."""
    if format not in ("metta", "fast"):
        raise ValueError(f"save format must be 'metta' or 'fast', got {format!r}")
    _validate_atoms(atoms)
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


def _load_fast(rt: Runtime, space: str, path: str) -> list[list[Atom]]:
    expected = str(rt.apply_must("petta_py_fast_header")).encode("ascii").split(b"\t")
    _validate_fast_header(path, _fast_header(path), expected)
    try:
        rt.do_must("petta_py_fast_load", path, space)
    except EngineError as exc:
        if not any(tag in str(exc) for tag in _FAST_ERRORS):
            raise EngineError(f"fast load failed while adding atoms from {path!r}: {exc}") from exc
        raise EngineError(
            f"fast load failed for {path!r}: {exc}. The cache is corrupt or "
            f"incomplete; re-save it from the source data."
        ) from exc
    return []


def load_space(rt: Runtime, space: str, path: str | os.PathLike[str]) -> list[list[Atom]]:
    """Load a text program or validated fast cache into a named space."""
    file = str(path)
    try:
        with _open_maybe_gz(file, "rb") as handle:
            is_fast = handle.read(len(_FAST_PREFIX)) == _FAST_PREFIX
    except OSError:
        is_fast = False
    if is_fast:
        return _load_fast(rt, space, file)
    row = rt.must("petta_py_load(File, Space, Groups)", File=file, Space=space)
    return [[atom_from_wire(wire) for wire in group] for group in row.get("Groups", [])]
