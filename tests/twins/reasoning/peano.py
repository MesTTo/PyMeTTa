"""examples/reasoning/peano.metta in Python: growing a space 300 times.

Each round reads every `(num $t)` in the space and writes `(num (S $t))` back,
refusing a duplicate, so 300 rounds leave 301 atoms. The claim is that count.

All four definitions stay at the container door, and each names the construct
that has no compiled spelling:

- `add-atom-no-duplicate` matches against a space its CALLER names, and a
  compiled `match()` takes its space as a literal, never as a parameter;
- `expand-once` is a `case`, which is what Python's `match` statement would
  spell and the subset has no lowering for yet;
- `expandK` and `demo-peano` bind with `let` and `let*` over calls to the two
  names above, which a compiled body reaches only through `m.fn`, putting back
  the very indirection the ladder is measuring.

The count stays engine-side too, and that one is measured rather than argued.
The answers are Peano terms up to 300 deep, so `len(m.eval(...))` builds them
all in Python and costs 2,549,185 inferences against the engine's 2,186,259,
+16.2%, past the lane's own 10% band; the general shape, quadratic in the term
depth, is measured in twins/performance/peanofast.py
[ai-tmp/probe/f_peano_reasoning_routes.py]. The missing door, a query that
projects or aggregates before it crosses, is filed as friction.
"""

from petta import S, V, equation, expr

#: Why this file sits below the top rung: all four definitions are at the
#: container door, and the count cannot cross into Python within the band.
RUNG = "all four definitions use a space parameter, a case, or let over them, and counting 301 deep terms in Python costs +16.2%"

#: The space the rounds read and write, named as a symbol because a term
#: carries no handle.
SELF = S["&self"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2186406 to 2186259, -147 (-0.0067%), by the twin
#: contract change: the `test` wrapper left the engine for Python's own
#: `assert`, which is all that could move; the 300 rounds and the duplicate
#: check inside them are the example. Against the example's 2194280 the ratio
#: is 0.9963 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/reasoning/peano.metta`]. Prior: ADDED 2026-08-22 at 2186406 by the
#: wave-3 twin baseline.
BUDGET = 2186259


def twin(m):
    """Expand the space 300 times, then count what is in it."""
    # Nothing is written twice: an atom that already matches is skipped.
    m += equation(S["add-atom-no-duplicate"](V.Space, V.Atom)).to(
        S["if"](expr().eq(S.collapse(S.once(S.match(V.Space, V.Atom, V.Atom)))),
                S["add-atom"](V.Space, V.Atom),
                S.empty())
    )

    # For every existing (num $t), add (num (S $t)).
    m += equation(S["expand-once"]()).to(
        S.case(S.match(SELF, S.num(V.t), V.t),
               ((V.x, S["add-atom-no-duplicate"](SELF, S.num(S.S(V.x)))),))
    )

    m += equation(S.expandK(V.n)).to(
        S["if"](V.n.eq(0), S.done, S.let(V.temp1, S["expand-once"](), S.expandK(V.n - 1)))
    )

    m += equation(S["demo-peano"](V.K)).to(
        S["let*"](((V.s, S["add-atom"](SELF, S.num(S.Z))), (V.g, S.expandK(V.K))),
                  S.match(SELF, S.num(V.stored), V.stored))
    )

    assert m.eval(S.length(S.collapse(S["demo-peano"](300)))) == [301]
