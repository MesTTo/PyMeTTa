"""Purpose: examples/types/types_dependent.metta in Python: a type computed by a program.

`get-type` is an ordinary function, so a program may add equations to it, and
these two compute a type from the VALUE: an even number is an `EvenNumber`, and
an expression of them is an `EvenNumberList`. The declared parameter types of
`f` and `g` then accept arguments nothing declared, because the computed
answer is what the check reads.

Both extensions land as the equations they are, because the head IS `get-type`
and no `@m.define` may name a function the space already answers. The first has
a plain variable head, so it goes through the write door as one atom; the
second's head is the STRUCTURE `(cons $head $tail)`, which is what `@m.rules`
is for. `EvenNumber` and `EvenNumberList` are Python classes so that `f` and
`g` say their signatures as annotations.

The comparison is `=alpha` and not `==` throughout, for the example's own
reason: each comparison crosses KNOWN and different types, which `==` refuses
by name, and `=alpha` is the comparison that takes anything.
"""

from metta import UNIT, Expression, S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
BUDGET = 1


class EvenNumber:
    """The computed type of an even number, named for `f`'s signature."""


class EvenNumberList:
    """The computed type of an expression of even numbers."""


def twin(m):
    """Teach get-type two new answers, then use them as declared types."""
    alpha, kind = fn["=alpha"], fn.get_type

    # The body is a ONE-ARMED if, the filtering form that answers nothing
    # where its condition fails, which `if_` takes beside the three-armed
    # conditional. `%` on an atom builds the term Python's own operator means.
    # (= (get-type $x) (catch (if (=alpha (% $x 2) 0) EvenNumber)))
    m += equation(kind(V.x)).to(fn.catch(if_(alpha(V.x % 2, 0), S.EvenNumber)))

    @m.define
    def f(x: EvenNumber, y: EvenNumber) -> EvenNumber:
        """(: f (-> EvenNumber EvenNumber EvenNumber)), (= (f $x $y) (+ $x $y))."""
        return x + y

    # !(test (f 2 4) 6)
    assert f(2, 4) == [6]

    @m.rules
    def walk(head, tail):
        """The structured second clause: a list of even numbers, elementwise."""
        # (= (get-type (cons $head $tail))
        #    (if (=alpha (get-type $head) EvenNumber)
        #        (if (=alpha $tail ()) EvenNumberList (get-type $tail))))
        yield equation(kind(S.cons(head, tail))).to(
            if_(alpha(kind(head), S.EvenNumber),
                if_(alpha(tail, UNIT), S.EvenNumberList, kind(tail)))
        )

    @m.define
    def g(items: EvenNumberList) -> bool:  # noqa: ARG001  -- the parameter is what the signature declares; the body answers a constant
        """(: g (-> EvenNumberList Bool)), (= (g $L) True)."""
        return True

    # !(test (g (2 4 6)) True)
    assert g(Expression((2, 4, 6))) == [True]
