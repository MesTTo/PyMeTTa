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
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 20711 to 19483, -1228 (-5.93%), by the twin-shape
#: rewrite: the two `test` wrappers left the engine for `assert`; the
#: computed-type walk over `(cons ...)` is unchanged and is nearly the whole
#: cost. Against the example's 25435 the ratio is 0.7660 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure
#: examples/types/types_dependent.metta`]. Prior: RE-PINNED at 20711 by
#: P14.8's m.eval fuel-scope alignment.
BUDGET = 19483


class EvenNumber:
    """The computed type of an even number, named for `f`'s signature."""


class EvenNumberList:
    """The computed type of an expression of even numbers."""


def twin(m):
    """Teach get-type two new answers, then use them as declared types."""
    alpha = S["=alpha"]

    even = S["if"](alpha(V.x % 2, 0), S.EvenNumber)  # rung: the body belongs to a clause OF get-type, so it is a term (P14.4)
    m += equation(S["get-type"](V.x)).to(S.catch(even))  # rung: the head is the engine's own get-type, which the program extends (P14.4)

    @m.define
    def f(x: EvenNumber, y: EvenNumber) -> EvenNumber:
        return x + y

    assert f(2, 4) == [6]

    ends = S["if"](alpha(V.tail, Expression(())), S.EvenNumberList, S["get-type"](V.tail))  # rung: same clause, same reason
    walk = S["if"](alpha(S["get-type"](V.head), S.EvenNumber), ends)  # rung: same clause, same reason
    m += equation(S["get-type"](S.cons(V.head, V.tail))).to(walk)  # rung: the head is get-type again, over a cons cell

    @m.define
    def g(items: EvenNumberList) -> bool:  # noqa: ARG001  -- the parameter is what the signature declares; the body answers a constant
        return True

    assert g(Expression((2, 4, 6))) == [True]
