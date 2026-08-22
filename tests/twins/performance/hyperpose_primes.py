"""examples/performance/hyperpose_primes.metta in Python: branches on real threads.

`hyperpose` fans a list of terms out over worker threads. The first form proves
the plumbing on three numbers, and the two after it race four primality tests,
once to completion and once until the first answer.

Only the first form is answered here. The other two are DECLINED, and the reason
is arithmetic rather than expressive: a thread that is cancelled mid-search
stops at whatever point the scheduler reached, so the inference count is not a
number any twin can pin. The residue records both against P14.14, which owns the
budget laws.

What the answered form shows is the dissolution table three times over: `let` is
an assignment, `collapse` is the answer list `m.eval` already hands back, and
`msort` is `sorted`. The two equations stay in the engine because the declined
forms are what would call them, and because they cannot be compiled anyway: a
hyphenated recursive callee has no Python spelling and `==` in a compiled body
lowers to `py-eq`, measured at +71.96% on exactly this search in
superpose_primes.py beside this file.
"""

from petta import S, V, equation

#: Why this file sits below the top rung: the two equations are the benchmark
#: the declined forms would run, and neither compiles, for the reasons
#: superpose_primes.py beside this file measures.
RUNG = "the two equations are the benchmark and neither compiles: a hyphenated recursive callee, and `==` lowering to py-eq at +71.96%"

#: The equality head, needed with a GROUND left operand, which is the one shape
#: Python's own operators cannot build: `0 == x` compares rather than building.
EQ = S["=="]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13589 to 12938, -651 (-4.79%), by the twin contract
#: change: the `test` wrapper, the `collapse` and the `msort` left the engine
#: for `assert`, the answer list `m.eval` already hands back, and `sorted`, and
#: the `let` became an assignment. The hyperposed fan-out itself did not move.
#: Form 0 runs on real threads, so its count is not identical across fresh
#: processes: ten runs measured 12937 to 12940, a spread of 3, so the pin is the
#: MIDPOINT and the lane's own 4-inference allowance covers the whole observed
#: range from there [measured 2026-08-22, ai-tmp/probe/f_hyper_spread.py].
#: Against the example's 283197773 the ratio is 0.0000457, because forms 1 and 2
#: are declined. Prior: RE-PINNED at 13589 by the same centring argument over a
#: six-run spread; ADDED 2026-08-22 at 13588 by the wave-3 twin baseline.
BUDGET = 12938


def twin(m):
    """Fan three numbers out over threads, and put the primes back together."""
    m += equation(S["find-divisor"](V.n, V["test-divisor"])).to(
        S["if"](V["test-divisor"] * V["test-divisor"] > V.n,
                V.n,
                S["if"]((EQ, 0, V.n % V["test-divisor"]),
                        V["test-divisor"],
                        S["find-divisor"](V.n, V["test-divisor"] + 1))))
    m += equation(S["prime?"](V.n)).to(V.n.eq(S["find-divisor"](V.n, 2)))

    # hyperpose takes its branches through a variable as happily as inline, and
    # the answers come back in whatever order the threads finish.
    xs = (3, 1, 2)
    assert sorted(m.eval(S.hyperpose(xs))) == [1, 2, 3]
