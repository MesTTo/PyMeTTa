"""examples/translation/translatorrule_cost.metta in Python: cost, and a joined head.

A bidirectional rule says two forms are equivalent, and a COST is what decides
which one the compiler emits: a rewrite fires only when it lowers the total,
and a form's cost is its node count unless a rule declares one for its head.
Declared at 10, `pow2` is expensive enough that squaring a small argument
expands and squaring a big one collapses, and the file's first three claims are
that turn.

The second half is a CONJUNCTIVE left side. `unit-of` has no equation at all;
the rule itself names the call it rewrites and a second pattern matched against
the space, so `$q` joins the two and `$u` carries the answer out. That is why
its type declaration is data rather than an annotation: there is no def to
annotate.

`pow2` is an ordinary compiled function whose parameter is annotated `Atom`, so
the argument arrives unreduced, which is what the original's own type
declaration says. Its body names `mul`, and that name takes the bracket: the
operator word table owns `S.mul` and makes it `*`, where this `mul` is a plain
data head with no equations behind it and multiplying two expressions is not
what the rule means.
"""

from typing import Any

from metta import Atom, Expression, S, V, arrow, equation, typed

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Register the costed and conjunctive rules, then exercise every case."""

    @m.define
    def pow2(x: Atom) -> Any:            # (: pow2 (-> Atom %Undefined%))
        return S.noeval(S["mul"](x, x))  # rung: the word table owns S.mul, which is *, and this mul is a data head

    m.fn.add_translator_rule(            # (add-translator-rule! pow2
        S.pow2,                          #   ((direction bidirectional) (cost 10)))
        Expression((S.direction(S.bidirectional), S.cost(10))),
    )

    # (pow2 3) costs 10 for the head plus 1 for the argument, and (mul 3 3) is
    # three nodes, so the squaring is expanded.
    assert pow2(3).one() == S["mul"](3, 3)  # rung: as above, the exact door for a data head the word table has taken

    # The same declaration collapses the multiplication back when the argument
    # is big enough to make writing it twice the more expensive side. The
    # bound namespace keeps a bracket exact for the same reason.
    large = S.a(S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert m.fn["mul"](large, large).one() == S.pow2(large)

    # A CONJUNCTIVE left side names several patterns that must all match: the
    # first is the call the rule rewrites and the rest are matched against the
    # space, so a rule can look at the program around the call.
    m += [(S.unit, S.mass, S.kg), (S.unit, S.length, S.m)]
    m += typed(S["unit-of"], arrow(Atom, Any))

    m.fn.add_translator_rule(            # (add-translator-rule! unit-of
        S["unit-of"],                    #   ((left ((unit-of $q) (unit $q $u)))
        Expression((                     #    (right (in $u))))
            S.left(Expression((S["unit-of"](V.q), S.unit(V.q, V.u)))),
            S.right(S["in"](V.u)),
        )),
    )

    assert m.fn.unit_of(S.mass).one() == S["in"](S.kg)
    assert m.fn.unit_of(S.length).one() == S["in"](S.m)

    # A call whose conjuncts do not match is a rule miss like any other, so it
    # has no answer rather than bringing the translation down.
    assert m.fn.unit_of(S.time) == []

    # The rule compiles to the equation an author would have written by hand,
    # with the conjuncts as a `match` chain: the engine's own conjunctive query
    # does the join.
    compiled = m[equation(S["unit-of"](V.q)).to(V.body)]
    assert [row.body[0] for row in compiled] == [S.match]
