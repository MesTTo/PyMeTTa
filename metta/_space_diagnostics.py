"""Purpose: build derivation trees and explain unsuccessful space patterns.
Guarantees:
  - derivation depth is either absent or a positive integer [tested
    test_derivation_depth_must_be_a_positive_integer_or_none]
  - depth exhaustion remains a partial proof rather than no proof [tested
    test_depth_exhaustion_returns_a_partial_proof]
  - why() distinguishes stored-shape misses, functions, and close names
    [tested test_why]
  - why() and lint() reach one head verdict, so a translator special form is
    never reported as an unknown name and a call at an undefined arity is
    named by both [tested: test_why_and_lint_agree_about_a_special_form,
    test_why_and_lint_agree_about_a_call_at_an_undefined_arity,
    test_why_and_lint_draw_suggestions_from_one_pool; commit=bd3a1bbad63952fc7c0d7367f38237dd1c219d8b]
  - eager query explanations distinguish a pattern miss, failed join, and
    rejecting guard [tested test_query_rows_explain_empty_results]
  - derivation enumeration selects ``metta_py_limited/6`` when a scoped stack
    bound exists [tested: test_stack_limit_is_carried_to_the_limited_six_seam;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - derivation enumeration crosses through the shared execution-policy wrapper,
    so atomic, speculative, and capture scopes cover the whole proof search
    [tested: test_every_public_execution_door_honours_speculative_policy,
    test_derivation_speculation_fences_the_engine_global_self;
    commit=cf6507cfe9c3d6512ac75039ae22f178140e0cbf]
  - ordinary derivation executes effectful premises and retains their engine
    writes; the existing speculative policy is the explicit rollback boundary
    [tested:
    test_derivation_effects_are_explicit_and_speculation_discards_engine_writes;
    commit=418bed011dfc47bb2c2d9e6b51e0d2a6f7b7e729]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib as _importlib
from typing import Any

from ._engine import Runtime
from ._head_meaning import EngineRegistry, head_meaning
from ._space_execution import _controlled_run
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
    trees = _controlled_run(
        rt,
        "metta_py_derivations",
        [space, _to_atom(target).to_wire(), -1 if depth is None else depth],
        _limits(timeout, inferences),
    )
    derivation_type = _importlib.import_module(
        f"{__package__}.derivation"
    ).Derivation
    return [derivation_type.from_atom(_atom_from_wire(tree)) for tree in trees]


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


def _unstored_explanation(space: Any, name: str, arguments: int) -> str:
    """Explain a head no stored atom carries, from the shared head verdict.

    The same head_meaning() lint() reads, so the two cannot disagree about
    what carries a name. Asking fun/1 alone, which this did through 0.7.3,
    answered "nothing here is headed by if, and no function has that name;
    did you mean if?" for a translator special form used correctly.
    """
    meaning = head_meaning(name, arguments, EngineRegistry(space.runtime))
    if meaning.wrong_arity:
        return (
            f"no {name} atoms are stored here, and {name} is a function "
            f"defined for {sorted(meaning.arities)} argument(s) rather than "
            f"{arguments}, so evaluating this will not answer either"
        )
    if meaning.route == "function":
        return (
            f"no {name} atoms are stored here; {name} is a function, so its "
            f"answers come from evaluation, not matching: try eval"
        )
    if meaning.route == "translated":
        return (
            f"no {name} atoms are stored here; {name} is a special form the "
            f"translator compiles, so its answers come from evaluation, not "
            f"matching: try eval"
        )
    # The near-miss needs no special case of its own: with no
    # underscore-to-hyphen rewriting left in the surface, nn_next against a
    # stored nn-next is a close match like any other.
    suggestion = f"; did you mean {meaning.suggestion}?" if meaning.suggestion else ""
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
    return _unstored_explanation(space, head.name, len(atom) - 1)


def _first_unmatched_pattern(space: Any, patterns: tuple[Atom, ...]) -> tuple[int, Atom] | None:
    for index, pattern in enumerate(patterns, start=1):
        if not space.match(pattern, limit=1):
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
    if where is not None and space.match(*patterns, limit=1):
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
