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
  - derivation enumeration selects ``petta_py_limited/6`` when a scoped stack
    bound exists [tested: test_stack_limit_is_carried_to_the_limited_six_seam;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib as _importlib
from difflib import get_close_matches
from typing import Any

from ._engine import Runtime
from ._space_objects import _limits
from .atoms import Atom, Expression, Symbol, _atom_from_wire, _to_atom


def derivations(
    rt: Runtime,
    space: str,
    target: Any,
    depth: int | None,
    *,
    timeout: float | None,
    inferences: int | None,
) -> list[Any]:
    """Return each guarded derivation for one target."""
    _validate_depth(depth)
    seconds, steps, stack = _limits(timeout, inferences) or (-1.0, -1, -1)
    goal = (
        "petta_py_limited(Seconds, Steps, petta_py_derivation, Ins, Tree)"
        if stack < 0
        else "petta_py_limited(Seconds, Steps, Stack, petta_py_derivation, Ins, Tree)"
    )
    inputs = {
        "Seconds": seconds,
        "Steps": steps,
        "Ins": [space, _to_atom(target).to_wire(), -1 if depth is None else depth],
    }
    if stack >= 0:
        inputs["Stack"] = stack
    rows = rt.iter(goal, **inputs)
    derivation_type = _importlib.import_module(
        f"{__package__}.derivation"
    ).Derivation
    return [derivation_type.from_atom(_atom_from_wire(row["Tree"])) for row in rows]


def _validate_depth(depth: int | None) -> None:
    if depth is not None and (isinstance(depth, bool) or not isinstance(depth, int) or depth <= 0):
        msg = f"derivation depth must be a positive integer or None, got {depth!r}"
        raise ValueError(msg)


def _stored_with_head(space: Any, name: str) -> list[Expression]:
    return [
        atom
        for atom in space.atoms()
        if isinstance(atom, Expression) and isinstance(atom.head, Symbol) and atom.head.name == name
    ]


def _stored_explanation(atom: Expression, name: str, stored: list[Expression]) -> str:
    sizes = sorted({len(candidate) for candidate in stored})
    if len(atom) not in sizes:
        # One observed size reads as a number, not a set: "[3] elements" looks
        # like a list of one element rather than an element count of three.
        observed = str(sizes[0]) if len(sizes) == 1 else str(sizes)
        return f"{name} atoms here have {observed} elements; the pattern has {len(atom)}"
    return f"{len(stored)} {name} atom(s) exist here but none unifies with {atom}"


def _unstored_explanation(space: Any, name: str) -> str:
    if space.is_function(name):
        return (
            f"no {name} atoms are stored here; {name} is a function, so its "
            f"answers come from evaluation, not matching: try eval"
        )
    # get_close_matches already covers the near-miss this used to special-case
    # by hand: with no underscore-to-hyphen rewriting left in the surface,
    # nn_next against a stored nn-next is just a close match like any other.
    close = get_close_matches(name, space.builtins(), n=1, cutoff=0.75)
    suggestion = f"; did you mean {close[0]}?" if close else ""
    return f"nothing here is headed by {name}, and no function has that name{suggestion}"


def explain_no_match(space: Any, pattern: Any) -> str:
    """Explain the first cheap reason one pattern cannot match."""
    atom: Atom = _to_atom(pattern)
    if not isinstance(atom, Expression) or not atom.children:
        return f"{atom} is not an expression pattern"
    head = atom.head
    if not isinstance(head, Symbol):
        return f"the pattern head {head} is not a symbol"
    stored = _stored_with_head(space, head.name)
    if stored:
        return _stored_explanation(atom, head.name, stored)
    return _unstored_explanation(space, head.name)


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
