"""The Python twin of examples/performance/hyperpose_primes.metta: threads racing.

`find-divisor` and `prime?` stay at the container door, and this file is where
that decision was MEASURED rather than argued. Python's `==` inside a compiled
body lowers to the prelude's `py-eq`, which answers what Python answers across
mixed numeric types, and never to MeTTa's own `==`. That sits in the inner loop
of a divisor search: the same program through `@m.define` costs 920,726
inferences against the term door's 536,577, +71.6%, which is past the lane's own
10% band and a regression in the very benchmark the example exists to run
[measured 2026-08-22, ai-tmp/probe/primes_ab.py, min of three fresh processes].
So the equation is built as the term it is, and the missing spelling is filed
against P14.4. `prime?` has a second reason on top: a compiled body names a
function by exactly its MeTTa spelling, and `find-divisor` is not a Python
identifier.

Every operator that CAN build the term does: `d * d > n` is
`(> (* $test-divisor $test-divisor) $n)`, `n % d` is `(% $n $test-divisor)`,
`d + 1` is `(+ $test-divisor 1)` and `V.n.eq(...)` is the equality TERM, since
`==` between atoms is structural equality. `(== 0 (% $n $d))` is the tuple
`(EQ, 0, ...)`, because Python has no way to put a ground operand on the LEFT of
a comparison term: `0 == x` compares, and `0 < x` reflects into `(> $x 0)`.

The second and third forms are DECLINED, not answered: `hyperpose` runs its
branches on real threads and the completion schedule decides how much of each
branch is evaluated, so the inference count is not a number a twin can pin. The
residue records both against P14.14, which owns the budget laws.
"""

from petta import S, V, equation

#: The equality head, needed with a GROUND left operand, which is the one shape
#: Python's own operators cannot build.
EQ = S["=="]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13588 to 13589, +1, and the move is a CENTRING rather
#: than a cost: form 0 runs `hyperpose` on real threads, so its inference count
#: is not deterministic across fresh processes. Six single-reading runs measured
#: 13587, 13588, 13590, 13591, 13591, 13591, a spread of 4, which the lane's own
#: 4-inference allowance covers from the midpoint but not from either end. Forms
#: 1 and 2 are DECLINED for the same reason at a scale the allowance cannot
#: cover; the residue records both against P14.14. Prior: ADDED 2026-08-22 at
#: 13588 by the wave-3 twin baseline.
BUDGET = 13589


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (find-divisor $n $test-divisor)
    #    (if (> (* $test-divisor $test-divisor) $n)
    #        $n
    #        (if (== 0 (% $n $test-divisor))
    #            $test-divisor
    #            (find-divisor $n (+ $test-divisor 1)))))
    m += equation(S["find-divisor"](V.n, V["test-divisor"])).to(
        S["if"](
            V["test-divisor"] * V["test-divisor"] > V.n,
            V.n,
            S["if"]((EQ, 0, V.n % V["test-divisor"]),
                V["test-divisor"],
                S["find-divisor"](V.n, V["test-divisor"] + 1))))

    # (= (prime? $n)
    #    (== $n (find-divisor $n 2)))
    m += equation(S["prime?"](V.n)).to(V.n.eq(S["find-divisor"](V.n, 2)))

    # !(test (msort (collapse (let $xs (3 1 2) (hyperpose $xs))))
    #        (1 2 3))
    yield m.eval(
        S.test(S.msort(S.collapse(S.let(V.xs, (3, 1, 2), S.hyperpose(V.xs)))),
            (1, 2, 3))
    )

    # !(test (collapse (hyperpose ((prime? 5353725700019)    ;cheap
    #                              (prime? 5378181100003)    ;cheap
    #                              (prime? 5421844300001)    ;cheap
    #                              (prime? 5473443100001)))) ;cheap => cheap overall
    #        (True True True True))
    yield None

    # !(test (once (hyperpose ((prime? 535372570000000063)    ;expensive
    #                          (prime? 537818110000000001)    ;expensive
    #                          (prime? 5421844300001)         ;cheap
    #                          (prime? 547344310000000013)))) ;expensive => cheap overall
    #        True)
    yield None
