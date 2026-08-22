"""examples/performance/peanofast.metta in Python: 2500 successors, and how to count them.

`expandK` writes `(num Z)`, `(num (S Z))`, and so on down 2500 levels;
`demo-peano` starts it from `Z`. Then the space is asked how many `num` atoms
it holds.

`expandK` stays in the engine because its body WRITES: `add-atom` is
hyphenated, so a compiled body has no name for it, and `done` is a lowercase
symbol used as data in the same body, which the subset has no spelling for
either (residue, P14.4). `demo-peano` IS an ordinary Python function, decorated
and then CALLED: `expandK` is a name the engine already knows and `Z` is a
capitalised free name, which a compiled body reads as the data constructor it
is.

The count is where this file earns its keep, because the obvious Python
spelling is asymptotically wrong and the measurement says so. `len(m[pattern])`
builds a Python atom for every answer, and every answer here is a term of depth
O(K), so counting costs Θ(K²): 251,831 inferences at K=250, 1,003,611 at 500,
4,007,233 at 1000 and 16,014,711 at 2000, quadrupling per doubling, against the
engine's own `(length (collapse (match ...)))` at 1,308 / 2,058 / 3,558 / 6,558,
which is linear. At K=2000 that is 2,442x [measured 2026-08-22,
ai-tmp/probe/f_query_scaling.py]. Pushing a small TEMPLATE down instead, so the
answers that cross are constants, restores linearity at 5,802 / 11,304 / 22,302
but still costs +15.6% over the whole example here, past the lane's 10% band
[ai-tmp/probe/f_peanofast_routes.py]. So the count stays engine-side, and the
missing door, a query that projects or aggregates before it crosses, is filed
as friction.
"""

from petta import S, V, equation

#: Why this file sits below the top rung, in its two halves: `expandK` writes
#: with `add-atom`, which a compiled body has no name for, and the count stays
#: engine-side because the Python query door is quadratic in the term depth,
#: measured in the docstring above.
RUNG = "expandK writes with add-atom and cannot compile, and counting deep matches through the Python query door is quadratic"

#: The space `expandK` writes into, named as a symbol because a term carries no
#: handle.
SELF = S["&self"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 68491 to 68380, -111 (-0.16%), by the twin contract
#: change: the `test` wrapper left the engine for Python's own `assert`, which
#: is all that could move. `demo-peano` was already compiled at the previous
#: pin, so `@m.define`'s per-name admission is inside both figures, and the
#: count did NOT move, for the reason the docstring measures. Against the
#: example's 76206 the ratio is 0.8973 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/performance/peanofast.metta`]. Prior:
#: RE-PINNED at 68491, +1621, when `demo-peano` gained the decorator (~1.6k
#: inferences of admission paid once); ADDED 2026-08-22 at 66870 by the wave-3
#: twin baseline.
BUDGET = 68380


def twin(m):
    """Build 2500 Peano successors, then count them."""
    m += equation(S.expandK(V.expression, V.n)).to(
        S["if"](V.n.eq(0),
                S.done,
                S.let(V.temp1,
                      S["add-atom"](SELF, S.num(V.expression)),
                      S.expandK(S.S(V.expression), V.n - 1))))

    @m.define(name="demo-peano")
    def demo_peano(k):
        """Expand from zero, k times."""
        return expandK(Z, k)  # noqa: F821  -- both names are MeTTa's: expandK is the equation above and Z its zero, and a compiled body is read as syntax

    demo_peano(2500)
    assert m.eval(S.length(S.collapse(S.match(SELF, S.num(V.stored), V.stored)))) == [2500]
