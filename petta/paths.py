"""Purpose: build cycle-safe lazy structural paths for query patterns.
Guarantees:
  - a path keeps its root opaque and reads only the named attributes or keys
    after the engine has matched that root [tested:
    test_a_path_reaches_into_a_handle_without_converting_it; commit=WORKTREE]
  - repeated object identities terminate the path as a non-match [tested:
    test_a_path_reaches_into_a_handle_without_converting_it; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._atoms_core import Box
from .atoms import Expr, Gnd, Sym, atom_from_wire, encode


@dataclass(frozen=True, slots=True)
class Attr:
    """One attribute step in a lazy path."""

    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("an attribute path segment cannot be empty")


@dataclass(frozen=True, slots=True)
class Key:
    """One subscription step in a lazy path."""

    value: Any


@dataclass(frozen=True, slots=True)
class Path:
    """An immutable sequence of lazy attribute and subscription steps."""

    segments: tuple[Attr | Key, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("a lazy path needs at least one segment")

    def to(self, target: Any) -> Expr:
        """Build the query marker that binds the reached value to *target*."""
        encoded_segments = Expr(
            [Sym("segments"), *(_segment_atom(segment) for segment in self.segments)]
        )
        return Expr([Sym("path-at"), encoded_segments, encode(target)])


def path(*segments: str | int | Attr | Key, to: Any) -> Expr:
    """Reach through an opaque query value and bind only the final field.

    Strings name attributes. Integers name subscription keys. Use ``Key``
    for a string or other explicit subscription key.

        m.query(S.manager(S.ada, path("profile", "age", to=V.age)))
    """
    return Path(tuple(_normalize_segment(segment) for segment in segments)).to(to)


def _normalize_segment(segment: str | int | Attr | Key) -> Attr | Key:
    if isinstance(segment, (Attr, Key)):
        return segment
    if isinstance(segment, str):
        return Attr(segment)
    return Key(segment)


def _segment_atom(segment: Attr | Key) -> Expr:
    if isinstance(segment, Attr):
        return Expr([Sym("attr"), Gnd(segment.name)])
    return Expr([Sym("key"), encode(segment.value)])


class _PathCursor:
    __slots__ = ("current", "seen")

    def __init__(self, root: Any) -> None:
        self.current = root.value if isinstance(root, Box) else root
        self.seen: set[int] = set()
        _remember_identity(self.current, self.seen)


def _remember_identity(value: Any, seen: set[int]) -> bool:
    if type(value) in (bool, int, float, complex, str, bytes, type(None)):
        return True
    identity = id(value)
    if identity in seen:
        return False
    seen.add(identity)
    return True


def _path_begin(root: Any) -> _PathCursor:
    """Engine callback: retain one opaque root without projecting it."""
    return _PathCursor(root)


def _path_step(cursor: _PathCursor, segment_wire: Any) -> bool:
    """Engine callback: resolve exactly one path segment."""
    segment = atom_from_wire(segment_wire)
    if not isinstance(segment, Expr) or len(segment.children) != 2:
        raise ValueError(f"invalid lazy path segment {segment!r}")
    head, value_atom = segment.children
    if not isinstance(head, Sym):
        raise ValueError(f"invalid lazy path segment {segment!r}")
    value = value_atom.value if isinstance(value_atom, Gnd) else value_atom
    try:
        if head.name == "attr" and isinstance(value, str):
            reached = getattr(cursor.current, value)
        elif head.name == "key":
            reached = cursor.current[value]
        else:
            raise ValueError(f"invalid lazy path segment {segment!r}")
    except (AttributeError, IndexError, KeyError, TypeError):
        return False
    if not _remember_identity(reached, cursor.seen):
        return False
    cursor.current = reached
    return True


def _path_value(cursor: _PathCursor) -> list[Any]:
    """Engine callback: encode only the final value a path reached."""
    return encode(cursor.current).to_wire()


__all__ = ["Attr", "Key", "Path", "path"]
