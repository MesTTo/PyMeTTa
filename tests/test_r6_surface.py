"""Purpose: prove R6's canonical atom vocabulary and ordered assembly door.

Guarantees:
  - TRUE, FALSE, UNIT, and HERE are immutable canonical atoms exported from
    the package [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
  - Expression consumes one iterable in order, so answer assembly preserves
    multiplicity and position [tested:
    test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=WORKTREE]
  - expr is removed rather than retained as a second spelling [tested:
    test_expr_is_not_a_second_public_door; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import petta
from petta import FALSE, HERE, TRUE, UNIT, Expr, Expression, Gnd, S, Sym


def test_the_canonical_atoms_are_public_values():
    """The vocabulary twins previously had to reconstruct by hand."""
    assert TRUE == Gnd(value=True)
    assert FALSE == Gnd(value=False)
    assert UNIT == Expr(())
    assert HERE == Expr((Sym("context-space"),))
    assert str(TRUE) == "True"
    assert str(FALSE) == "False"
    assert str(UNIT) == "()"
    assert str(HERE) == "(context-space)"
    assert {"TRUE", "FALSE", "UNIT", "HERE"} <= set(petta.__all__)


def test_expression_assembles_one_ordered_atom_from_an_iterable():
    """An answer multiset becomes an ordered object-level expression."""
    answers = [S.first, S.second, S.third]
    assembled = Expression(answers)
    assert assembled == Expr(tuple(answers))
    assert tuple(assembled) == tuple(answers)
    assert Expression(reversed(answers)) != assembled
    assert "order" in (Expression.__doc__ or "").lower()


def test_expr_is_not_a_second_public_door():
    """The settled name replaces the provisional builder."""
    assert "expr" not in petta.__all__
    assert not hasattr(petta, "expr")
