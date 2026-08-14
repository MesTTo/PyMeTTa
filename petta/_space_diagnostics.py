"""Purpose: build derivation trees and explain unsuccessful space patterns.
Guarantees:
  - derivation depth is either absent or a positive integer [tested
    test_derivation_depth_must_be_a_positive_integer_or_none]
  - depth exhaustion remains a partial proof rather than no proof [tested
    test_depth_exhaustion_returns_a_partial_proof]
  - why() distinguishes stored-shape misses, functions, and close names
    [tested test_why]
  - eager query explanations distinguish a pattern miss, failed join, and
    rejecting guard [tested test_query_rows_explain_empty_results]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any

from ._engine import Runtime
from ._space_objects import _limits
from .atoms import Atom, Expr, Sym, _to_atom, atom_from_wire
from .derivation import Derivation


def derivations(
    rt: Runtime,
    space: str,
    target: Any,
    depth: int | None,
    *,
    timeout: float | None,
    inferences: int | None,
) -> list[Derivation]:
    """Return each guarded derivation for one target."""
    _validate_depth(depth)
    seconds, steps = _limits(timeout, inferences) or (-1.0, -1)
    rows = rt.iter(
        "petta_py_limited(Seconds, Steps, petta_py_derivation, Ins, Tree)",
        Seconds=seconds,
        Steps=steps,
        Ins=[space, _to_atom(target).to_wire(), -1 if depth is None else depth],
    )
    return [Derivation.from_atom(atom_from_wire(row["Tree"])) for row in rows]


def _validate_depth(depth: int | None) -> None:
    if depth is not None and (isinstance(depth, bool) or not isinstance(depth, int) or depth <= 0):
        raise ValueError(f"derivation depth must be a positive integer or None, got {depth!r}")


def _stored_with_head(space: Any, name: str) -> list[Expr]:
    return [
        atom
        for atom in space.atoms()
        if isinstance(atom, Expr) and isinstance(atom.head, Sym) and atom.head.name == name
    ]


def _stored_explanation(atom: Expr, name: str, stored: list[Expr]) -> str:
    sizes = sorted({len(candidate) for candidate in stored})
    if len(atom) not in sizes:
        return f"{name} atoms here have {sizes} elements; the pattern has {len(atom)}"
    return f"{len(stored)} {name} atom(s) exist here but none unifies with {atom}"


def _unstored_explanation(space: Any, name: str) -> str:
    if space.is_function(name):
        return (
            f"no {name} atoms are stored here; {name} is a function, so its "
            f"answers come from evaluation, not matching: try eval"
        )
    renamed = name.replace("_", "-")
    if renamed != name and space.is_function_here(renamed):
        return (
            f"nothing here is headed by {name}, and no function has that name; "
            f"did you mean {renamed}? define() and register_op() both read "
            f"underscores as hyphens"
        )
    close = get_close_matches(name, space.builtins(), n=1, cutoff=0.75)
    suggestion = f"; did you mean {close[0]}?" if close else ""
    return f"nothing here is headed by {name}, and no function has that name{suggestion}"


def explain_no_match(space: Any, pattern: Any) -> str:
    """Explain the first cheap reason one pattern cannot match."""
    atom: Atom = _to_atom(pattern)
    if not isinstance(atom, Expr) or not atom.children:
        return f"{atom} is not an expression pattern"
    head = atom.head
    if not isinstance(head, Sym):
        return f"the pattern head {head} is not a symbol"
    stored = _stored_with_head(space, head.name)
    if stored:
        return _stored_explanation(atom, head.name, stored)
    return _unstored_explanation(space, head.name)


def strict_violation(space: Any, atom: Any) -> str | None:
    """Say why one answer looks like silence, or None when it looks intended.

    An unreduced call is a legitimate answer in MeTTa, so this reports only
    the case with no innocent reading: an expression whose head names neither
    a function nor anything stored here, which is what a typo produces. A
    function that matched no clause answers nothing rather than answering
    itself, so it never reaches here.
    """
    if not isinstance(atom, Expr) or not atom.children:
        return None
    head = atom.head
    if not isinstance(head, Sym):
        return None
    if space.is_function(head.name) or space.is_function_here(head.name):
        return None
    if _stored_with_head(space, head.name):
        return None
    return f"{atom} came back unreduced: {_unstored_explanation(space, head.name)}"


def _first_unmatched_pattern(space: Any, patterns: tuple[Atom, ...]) -> tuple[int, Atom] | None:
    for index, pattern in enumerate(patterns, start=1):
        if not space.query(pattern, limit=1):
            return index, pattern
    return None


def explain_empty_query(
    space: Any,
    patterns: tuple[Atom, ...],
    where: Atom | None,
) -> str:
    """Explain which stage removed every answer from one eager query."""
    if len(patterns) == 1 and where is None:
        return explain_no_match(space, patterns[0])
    if where is not None and space.query(*patterns, limit=1):
        return (
            f"the patterns match together, but the where guard {where} "
            "rejects every joined row"
        )
    unmatched = _first_unmatched_pattern(space, patterns)
    if unmatched is not None:
        index, pattern = unmatched
        detail = explain_no_match(space, pattern)
        if len(patterns) == 1:
            return detail
        return f"pattern {index} cannot match: {detail}"
    if len(patterns) > 1:
        return (
            "each pattern matches on its own, but no shared variable binding "
            "satisfies them together"
        )
    return "the empty query returned no rows"
