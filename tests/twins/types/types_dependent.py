"""Purpose: examples/types/types_dependent.metta in Python: a type computed by a program.

`get-type` is an ordinary function, so a program may add equations to it, and
these two compute a type from the VALUE: an even number is an `EvenNumber`, and
an expression of them is an `EvenNumberList`. The declared parameter types of
`f` and `g` then accept arguments nothing declared, because the computed
answer is what the check reads.

Both extensions are written as equations because the head IS `get-type`: no
decorator can name a function the space already answers, and stacking a clause
onto one is the whole point here. `EvenNumber` and `EvenNumberList` are Python
classes so that `f` and `g` say their signatures as annotations.

The comparison is `=alpha` and not `==` throughout, for the example's own
reason: each comparison crosses KNOWN and different types, which `==` refuses
by name, and `=alpha` is the comparison that takes anything.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


class EvenNumber:
    """The computed type of an even number, named for `f`'s signature."""


class EvenNumberList:
    """The computed type of an expression of even numbers."""


def twin(m):
    """Teach get-type two new answers, then use them as declared types."""
    alpha, kind = fn["=alpha"], fn.get_type

    # The head IS the engine's own get-type, which the program extends, so
    # the clause is written as the equation it is.
    #
    # Known issue: both bodies are ONE-ARMED ifs, and `if_(condition,
    # consequent, alternative)` fixes the arity at three, so the builder
    # cannot say them and Python's conditional expression cannot either. It
    # should read:
    #     even = if_(alpha(V.x % 2, 0), S.EvenNumber)
    even = fn["if"](alpha(V.x % 2, 0), S.EvenNumber)  # rung: a one-armed `if` has no builder and no Python expression (P14.4)
    m += equation(kind(V.x)).to(fn.catch(even))

    @m.define
    def f(x: EvenNumber, y: EvenNumber) -> EvenNumber:
        return x + y

    assert f(2, 4) == [6]

    ends = if_(alpha(V.tail, Expression(())), S.EvenNumberList, kind(V.tail))
    # Known issue again, and it should read `if_(alpha(kind(V.head),
    # S.EvenNumber), ends)`.
    walk = fn["if"](alpha(kind(V.head), S.EvenNumber), ends)  # rung: a one-armed `if` has no builder (P14.4)
    m += equation(kind(S.cons(V.head, V.tail))).to(walk)

    @m.define
    def g(items: EvenNumberList) -> bool:  # noqa: ARG001  -- the parameter is what the signature declares; the body answers a constant
        return True

    assert g(Expression((2, 4, 6))) == [True]
