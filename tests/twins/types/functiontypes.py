"""Purpose: examples/types/functiontypes.metta in Python: what a signature does.

Three functions over one shape of body, and the declared signature decides what
reaches it and what comes back. `wu1` takes its second argument as `Atom`, so
that argument arrives unrun; `wu2` is `Number` throughout and adds; `wu3`
answers a plain expression on one branch and a number on the other, which
`%Undefined%` allows.

All three say their types as ANNOTATIONS, which is the whole declaration: `int`
is Number, `Atom` is the Atom metatype, and `Any` is `%Undefined%`, all through
the one conversion table, so each arrow is written once and the engine checks
it. Inside the compiled bodies Python's own syntax is the MeTTa: `if a < 10`
is the guard, `a + b` builds `(+ $a $b)`, and wu3's other branch builds the
five-symbol expression `(a list not a number)` by calling its head, which is
what building a term by its head means whether or not anything defines that
head. Nothing here defines `a`, and the expression is data.

Note what the twin does NOT need: the example wraps its expected answers in
`noeval` because MeTTa's `test` evaluates them. Python's `==` evaluates
nothing, so the expected term is written as itself. It is written through
`Expression` rather than as a bare tuple because comparison is the one door a
tuple does not cross as an expression (P14.28).
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

from typing import Any

from metta import Atom, Expression, S

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Declare three signatures, then watch each one shape its call."""

    @m.define
    def wu1(a: int, b: Atom) -> Any:
        """(: wu1 (-> Number Atom %Undefined%)), (= (wu1 $a $b) (42 $a $b))."""
        return (42, a, b)

    @m.define
    def wu2(a: int, b: int) -> int:
        """(: wu2 (-> Number Number Number)), (= (wu2 $a $b) (+ $a $b))."""
        return a + b

    @m.define
    def wu3(a: int, b: int) -> Any:
        """(: wu3 (-> Number Number %Undefined%)), guarded on (< $a 10)."""
        if a < 10:
            return a + b
        return S.a(S.list, S["not"], S.a, S.number)

    # The Atom-typed argument arrives unevaluated; the Number-typed one does
    # not, so only the first of the two sums survives into the answer.
    # !(test (wu1 (+ 2 4) (+ 4 2)) (noeval (42 6 (+ 4 2))))
    assert wu1(S.add(2, 4), S.add(4, 2)) == [Expression((42, 6, S.add(4, 2)))]
    # !(test (wu2 (+ 2 4) (+ 4 2)) 12)
    assert wu2(S.add(2, 4), S.add(4, 2)) == [12]

    # %Undefined% output: either branch is acceptable to the checker.
    # !(test (wu3 42 0) (a list not a number))
    assert wu3(42, 0) == [S.a(S.list, S["not"], S.a, S.number)]
    # !(test (wu3 2 0) 2)
    assert wu3(2, 0) == [2]
