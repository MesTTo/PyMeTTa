"""Purpose: teach the encoder the annotated_types refinement vocabulary.

With it ``Annotated[int, Gt(0)]`` reaches the engine as ``(Annotated Number
(Gt 0))`` through the type reader's existing rule, and the same constraints
are decided on the Python side for the property tests ``metta.testing.cases``
writes.

The vocabulary is annotated_types' because it is the one pydantic, msgspec,
beartype and Hypothesis already read, and ``Annotated`` is PEP 593's slot for
it; nothing here is a second spelling. Each constraint class encodes to the
atom whose head is its own name, ``Interval`` keeps the bounds that were
written as ``(kind limit)`` pairs, ``Len`` keeps one or two lengths, and
``doc`` encodes to ``(doc "...")``. Which of those heads REFINE a type is not
decided here: the type reader asks the generated ``Refinement`` vocabulary,
the catalog's ``(vocabulary refinement ...)`` row, so ``doc`` and ``Timezone``
travel in the annotation claim and never reach the type.
Assumes:
  - ``annotated_types`` is importable; it is a declared dependency because a
    type reader that speaks a vocabulary has to import it
    [source: extensions/python/pyproject.toml, dependencies; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
Guarantees:
  - every annotated_types constraint class encodes to the atom the design
    names, and ``encode`` answers it directly as well as through a signature
    [tested: test_each_constraint_class_projects_to_its_atom; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - ``refinement_atom`` admits an Atom, or metadata whose encoded head is in
    the refinement vocabulary, and answers None for everything else, so the
    type projection carries exactly the constraints the engine decides
    [tested: test_a_refined_signature_declares_the_refined_arrow,
    test_doc_and_timezone_stay_in_the_annotation_claim; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - ``holds`` decides Gt, Ge, Lt, Le, MultipleOf, MinLen, MaxLen and Predicate
    on a Python value with Python's own operators, answers None for a
    constraint that says nothing about values, and reads a comparison the
    value cannot make as False rather than raising
    [tested: test_holds_decides_each_constraint_the_way_the_engine_does;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, cast

import annotated_types as at

from ._atoms_core import Atom, Expression, Symbol, encode
from .vocabularies import Refinement

# Attached through the function's __dict__ in _atoms_core, which a type
# checker cannot see on a Callable; the cast names the door once.
_register = cast(Any, encode).register

#: The bound kinds an Interval may carry, in the order the atom keeps them.
_INTERVAL_BOUNDS: tuple[str, ...] = ("gt", "ge", "lt", "le")


def _claim(head: str, *parts: Any) -> Expression:
    """``(head part...)`` with every part encoded, the shape every constraint takes."""
    return Expression([Symbol(head), *(encode(part) for part in parts)])


def _interval(constraint: at.Interval) -> Expression:
    """``(Interval (ge 0) (le 1))``: only the bounds that were written."""
    bounds = [
        Expression([Symbol(kind), encode(limit)])
        for kind in _INTERVAL_BOUNDS
        if (limit := getattr(constraint, kind)) is not None
    ]
    return Expression([Symbol("Interval"), *bounds])


def _len(constraint: at.Len) -> Expression:
    """``(Len 2)`` or ``(Len 2 5)``, the positional spelling Len itself has."""
    if constraint.max_length is None:
        return _claim("Len", constraint.min_length)
    return _claim("Len", constraint.min_length, constraint.max_length)


_register(at.Gt, lambda constraint: _claim("Gt", constraint.gt))
_register(at.Ge, lambda constraint: _claim("Ge", constraint.ge))
_register(at.Lt, lambda constraint: _claim("Lt", constraint.lt))
_register(at.Le, lambda constraint: _claim("Le", constraint.le))
_register(at.Interval, _interval)
_register(at.MultipleOf, lambda constraint: _claim("MultipleOf", constraint.multiple_of))
_register(at.MinLen, lambda constraint: _claim("MinLen", constraint.min_length))
_register(at.MaxLen, lambda constraint: _claim("MaxLen", constraint.max_length))
_register(at.Len, _len)
# A Predicate's function encodes as the encoder already reads callables: a
# defined head as its symbol, a mentioned standard callable as its MeTTa name,
# any other callable as a grounded value the engine applies through the seam.
_register(at.Predicate, lambda constraint: _claim("Predicate", constraint.func))
_register(at.Unit, lambda constraint: _claim("Unit", constraint.unit))
_register(at.Timezone, lambda constraint: _claim("Timezone", constraint.tz))
_register(at.DocInfo, lambda constraint: _claim("doc", constraint.documentation))


def refinement_atom(item: Any) -> Atom | None:
    """The refinement one ``Annotated`` metadata item contributes to a type.

    An Atom already names MeTTa structure at a type boundary and travels as
    written, the rule ``arrays.Shape`` relies on. Any other item is encoded,
    and refines only when its atom's head is in the refinement vocabulary;
    ``doc("...")`` and a plain string answer None and stay in the annotation
    claim alone.
    """
    if isinstance(item, Atom):
        return item
    atom = encode(item)
    if (
        isinstance(atom, Expression)
        and atom.children
        and isinstance(atom.head, Symbol)
        and atom.head.name in Refinement
    ):
        return atom
    return None


def constraints(metadata: Iterable[Any]) -> list[at.BaseMetadata]:
    """The annotated_types constraints among Annotated metadata, grouped ones expanded.

    ``Interval(ge=0, le=1)`` iterates to ``Ge(0), Le(1)`` and ``Len(2, 5)`` to
    ``MinLen(2), MaxLen(5)``, which is the grouping protocol annotated_types
    defines and Hypothesis reads the same way.
    """
    found: list[at.BaseMetadata] = []
    for item in metadata:
        if isinstance(item, at.GroupedMetadata):
            found.extend(constraints(item))
        elif isinstance(item, at.BaseMetadata):
            found.append(item)
    return found


def _call(test: Callable[[Any], Any], value: Any) -> Any:
    return test(value)


def holds(
    constraint: at.BaseMetadata,
    value: Any,
    *,
    apply: Callable[[Callable[[Any], Any], Any], Any] | None = None,
) -> bool | None:
    """Whether ``value`` satisfies one constraint, decided with Python's own operators.

    True or False when the constraint decides the value; None when it says
    nothing about values, which is what ``Unit`` and ``Timezone`` are. A
    comparison the value cannot make, a length it does not have, or a
    remainder it cannot take reads as False, which is the engine's answer for
    the same pair. ``apply`` is how a ``Predicate``'s function is applied to
    the value; the default calls it, and a caller that knows a defined head
    evaluates through the engine passes its own.
    """
    run = _call if apply is None else apply
    try:
        match constraint:
            case at.Gt(gt=bound):
                return bool(value > bound)
            case at.Ge(ge=bound):
                return bool(value >= bound)
            case at.Lt(lt=bound):
                return bool(value < bound)
            case at.Le(le=bound):
                return bool(value <= bound)
            case at.MultipleOf(multiple_of=divisor):
                return bool(value % divisor == 0)
            case at.MinLen(min_length=least):
                return len(value) >= least
            case at.MaxLen(max_length=most):
                return len(value) <= most
            case at.Predicate(func=test):
                return bool(run(test, value))
    except (TypeError, ValueError):
        return False
    return None
