"""The Python twin of examples/functions/multicall.metta: one head, two answers.

Both equations answer, which is why `(collapse (mycalc 1 2))` is `(3 -1)` and
not one of them. That is exactly what stacked `@m.define` clauses do NOT mean:
stacking them reads as first-match, so a later clause is guarded against every
earlier literal head, and two clauses fixing no literal at all are a
REDEFINITION of the same clause rather than an alternative beside it.

So the definitional decorator here is `@rules`, the other shape of the same
door: the generator's parameters ARE the equations' variables (`x` is `$x`),
each `yield` is one equation, and `m.add` lands the pair. Nothing is spelled
twice and no variable escapes the generator.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2295 to 2314, +19 (+0.83%), and the whole of it is
#: the BATCH door rather than the rewrite: `@rules` builds the identical two
#: equation atoms, but `m.add(a, b)` costs 1335 where `m += a` twice costs
#: 1316, a fixed 19 for the many-wire call. The equations, and therefore the
#: form that runs over them, are unchanged. The lane's parity reads 0.52 of
#: the original. Prior: ADDED 2026-08-22 at 2295 by 7f15dc1's wave-3
#: baseline.
BUDGET = 2314


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    # rung: below the function shape: the two clauses are ALTERNATIVES that both
    #   answer, which stacked @m.define clauses read as first-match (residue,
    #   P14.4; the design is P14.3's own note)
    @rules
    def mycalc(x, y):
        # (= (mycalc $x $y) (+ $x $y))
        yield equation(S.mycalc(x, y)).to(x + y)
        # (= (mycalc $x $y) (- $x $y))
        yield equation(S.mycalc(x, y)).to(x - y)

    m.add(*mycalc)

    # !(test (collapse (mycalc 1 2)) (3 -1))
    yield m.eval(S.test(S.collapse(S.mycalc(1, 2)), (3, -1)))
