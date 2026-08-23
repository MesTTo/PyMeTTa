"""Purpose: examples/types/functiontypes.metta in Python: what a signature does.

Three functions over one shape of body, and the declared signature decides what
reaches it and what comes back. `wu1` takes its second argument as `Atom`, so
that argument arrives unrun; `wu2` is `Number` throughout and adds; `wu3`
answers a plain expression on one branch and a number on the other, which
`%Undefined%` allows.

`wu1` and `wu2` say their types as ANNOTATIONS, which is the whole declaration:
`int` is Number, `Atom` is the Atom metatype, and `Any` is `%Undefined%`, all
through the one conversion table, so the arrow is written once and the engine
checks it. `arrow(int, int, Any)` is that same table at the TERM door, which is
what `wu3` needs: it is written at the container door because its second branch
answers `(a list not a number)`, four lowercase SYMBOLS, and a compiled body
reads a lowercase free name as a function to call.

Note what the twin does NOT need: the example wraps its expected answers in
`noeval` because MeTTa's `test` evaluates them. Python's `==` evaluates
nothing, so the expected term is written as itself.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from typing import Any

from petta import Atom, Expression, S, V, arrow, equation, fn, if_, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Declare three signatures, then watch each one shape its call."""
    not_a_number = S.a(S.list, S["not"], S.a, S.number)

    @m.define
    def wu1(a: int, b: Atom) -> Any:
        return (42, a, b)

    @m.define
    def wu2(a: int, b: int) -> int:
        return a + b

    m += typed(S.wu3, arrow(int, int, Any))
    # Known issue: `<` is the one comparison that no longer builds its term.
    # Appendix stamp 6 gave `Atom.__lt__` to the engine's sort order, so
    # `V.a < 10` raises TypeError while `<=`, `>` and `>=` still build. It
    # should read:
    #     m += equation(S.wu3(V.a, V.b)).to(if_(V.a < 10, V.a + V.b, not_a_number))
    m += equation(S.wu3(V.a, V.b)).to(if_(fn["<"](V.a, 10), V.a + V.b, not_a_number))

    # The Atom-typed argument arrives unevaluated; the Number-typed one does
    # not, so only the first of the two sums survives into the answer.
    assert wu1(S["+"](2, 4), S["+"](4, 2)) == [Expression((42, 6, S["+"](4, 2)))]
    assert wu2(S["+"](2, 4), S["+"](4, 2)) == [12]

    # %Undefined% output: either branch is acceptable to the checker.
    assert m.fn.wu3(42, 0) == [not_a_number]
    assert m.fn.wu3(2, 0) == [2]
