"""examples/basics/factorial.metta in Python: recursion through a conditional.

`@m.define` reads the function as syntax and writes the equation, so Python's
conditional expression IS MeTTa's `if` and the recursive call is the same call
the equation makes.

What is STORED is not quite what the original stores, and the difference is
worth reading back rather than believing. A compiled body's `==` lowers to
the prelude's `py-eq`, a host crossing, where the original writes MeTTa's own
`(== $n 0)`; the operator table calls `==` taken, for Python's own structural
equality, and the method form `a.eq(b)` that builds `(== a b)` has no body
equivalent. The two answer alike on every input this example has. The second
claim below is that reading, so the divergence is checked rather than
described, and the residue table records it against P14.4.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-23, 4665 to 5121, +456, by the p14-tabling merge, the
#: sole change between the two readings: admission analysis pricing its
#: recursive definition. Ratio 5121/5860 = 0.8739 [measured 2026-08-23 min-
#: of-3 via tools/twin_coverage.py --measure]. Prior:
#: RE-PINNED 2026-08-22, 5101 to 4665, -436 (-8.5%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`, and a second
#: claim ENTERED: the twin reads its own stored equation back to show the
#: condition's head is `py-eq` rather than MeTTa's `==`. Against the
#: example's 5297 the ratio is 0.8807 [measured 2026-08-22 min-of-3,
#: `twin_coverage.py --measure`]. The old figure priced a different
#: program.
BUDGET = 5121


def twin(m):
    """Define the factorial, run it, and read back the equation it stored."""
    @m.define(name="facF")
    def fac_f(n):
        # (= (facF $n) (if (== $n 0) 1 (* $n (facF (- $n 1)))))
        return 1 if n == 0 else n * fac_f(n - 1)

    assert fac_f(10) == [3628800]

    condition = m.query(S["="](S.facF(V.n), V.body)).one().body[1]
    assert condition[0] == S["py-eq"]
