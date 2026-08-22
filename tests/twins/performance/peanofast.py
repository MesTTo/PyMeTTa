"""The Python twin of examples/performance/peanofast.metta: 2500 successors.

`expandK` stays at the container door because its body WRITES: `add-atom` is
hyphenated, and a compiled body names a function by exactly its MeTTa spelling,
which `add-atom` is not a Python identifier for. `done` is a lowercase symbol as
data in the same body, which the subset also has no spelling for. Both are
residue entries against P14.4.

`demo-peano` is an ordinary Python function: its body calls `expandK`, which the
engine knows under that exact name, and `Z` is a capitalised free name, which a
compiled body reads as the data constructor it is. The arithmetic and the
equality TERM are Python's own: `V.n.eq(0)` is `(== $n 0)` and `V.n - 1` is
`(- $n 1)`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 66870 to 68491, +1621 (+2.42%), by `demo-peano` moving
#: to the definitional decorator. The compiled clause is the same clause; the
#: charge is @m.define's per-name admission, the three reflection facts the
#: container door never writes (`(defined &self demo-peano)`,
#: `(effect demo-peano immutable)` and `(source-span &self demo-peano ...)`),
#: measured at ~1.6k inferences per decorated name and paid once at decoration.
#: Prior: ADDED 2026-08-22 at 66870 by the wave-3 twin baseline.
BUDGET = 68491


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (expandK $expression $n)
    #    (if (== $n 0)
    #        done
    #        (let $temp1 (add-atom &self (num $expression))
    #             (expandK (S $expression) (- $n 1)))))
    m += equation(S.expandK(V.expression, V.n)).to(S["if"](V.n.eq(0),
            S.done,
            S.let(V.temp1,
                S["add-atom"](S["&self"], S.num(V.expression)),
                S.expandK(S.S(V.expression), V.n - 1))))

    @m.define(name="demo-peano")
    def demo_peano(k):
        # (= (demo-peano $K) (expandK Z $K))
        return expandK(Z, k)  # noqa: F821  -- both names are MeTTa's: expandK is the equation above and Z its zero, and a compiled body is read as syntax

    # !(demo-peano 2500)
    yield m.eval(S["demo-peano"](2500))

    # !(test (length (collapse (match &self (num $1) $1))) 2500)
    yield m.eval(
        S.test(S.length(S.collapse(S.match(S["&self"], S.num(V["1"]), V["1"]))),
            2500)
    )
