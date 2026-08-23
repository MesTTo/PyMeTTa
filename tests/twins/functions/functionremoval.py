"""examples/functions/functionremoval.metta in Python: equations move.

An equation is an ATOM, so it can be taken out of the space and put back, and
the function answers differently while it is gone. When both clauses are gone
`(f g)` matches nothing and answers itself.

Both definitions are decorated Python functions. `g` is a computation. `f`'s
two clauses are ALTERNATIVES that both answer, and a generator body says
exactly that: each independent yield stores one equation under the one head,
so the pair is two atoms rather than a first-match ladder.

The point of the file then writes itself, because an equation is a VALUE:
`equation(head).to(body)` builds the same atom the decorator stored, and `-=`
and `+=` take it as the atom it is.

The last claim reads through the engine's own reducer rather than `m.eval`,
for the reason examples/functions/dispatch_policies.metta's twin measures:
with both clauses gone the call is not reducible, and `m.eval` drops that
answer where a runnable form keeps it.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Take one clause out, put it back, take the other, then both."""

    @m.define
    def g(x):
        # (= (g $x) (+ $x 1))
        return x + 1

    @m.define
    def f(g):
        # (= (f $g) ($g 1))
        yield (g, 1)
        # (= (f $g) 42)
        yield 42

    call = equation(S.f(V.g)).to((V.g, 1))
    const = equation(S.f(V.g)).to(42)

    assert m.eval(S.f(S.g)) == [2, 42]

    m -= const
    assert m.eval(S.f(S.g)) == [2]

    m += const
    m -= call
    assert m.eval(S.f(S.g)) == [42]

    m -= const
    assert m.fn.reduce(S.f(S.g)) == [S.f(S.g)]
