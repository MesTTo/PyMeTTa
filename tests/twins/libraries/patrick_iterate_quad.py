"""The Python twin of examples/libraries/patrick_iterate_quad.metta.

A double sum written as one iterate: the step carries (row, column, total) and
advances the column until it meets the row.

Both equations stay at the container door for the reasons P14.4 records:
`quad-step` destructures its second argument IN THE HEAD, where a decorator
takes only a literal parameter default, and `quad-sum` passes `quad-step` by a
hyphenated name a compiled body cannot spell. Every arithmetic operand here
carries a variable, so Python's own operators build those terms; only `(== $i $t)`
names its head, because Python's `==` between atoms answers structural equality
rather than building a term.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 35565297 to 35565297, +0 (+0.00%), by the P14
#: twin-style rewrite: the twin's atoms are unchanged: both equations stay
#: container-door atoms and equation(...).to(...) builds what S["="](...)
#: built. Prior: ADDED 2026-08-22 at 35565297 by the wave-3 libraries
#: baseline, which recorded no cause.
BUDGET = 35565297

def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_patrick))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_patrick)))

    # (= (quad-step $dummy ($t $i $sum))
    #    (if (== $i $t)
    #        ( (+ $t 1) 1 (+ $sum (* $t $i)) )
    #        ( $t (+ $i 1) (+ $sum (* $t $i)) )))
    m += equation(S["quad-step"](V.dummy, (V.t, V.i, V.sum))).to(
        S["if"](
            S["=="](V.i, V.t),
            (V.t + 1, 1, V.sum + V.t * V.i),
            (V.t, V.i + 1, V.sum + V.t * V.i),
        )
    )

    # (= (quad-sum $n)
    #    (last (iterate 0 (/ (* $n (+ $n 1)) 2) (1 1 0) quad-step)))
    m += equation(S["quad-sum"](V.n)).to(
        S.last(S.iterate(0, V.n * (V.n + 1) / 2, (1, 1, 0), S["quad-step"]))
    )

    # !(test (quad-sum 1000) 125417041750)
    yield m.eval(S.test(S["quad-sum"](1000), 125417041750))
