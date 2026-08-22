"""The Python twin of examples/performance/hyperpose_primes.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 13588


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (find-divisor $n $test-divisor)
    #    (if (> (* $test-divisor $test-divisor) $n)
    #        $n
    #        (if (== 0 (% $n $test-divisor))
    #            $test-divisor
    #            (find-divisor $n (+ $test-divisor 1)))))
    m += expr(
        S["="],
        expr(S["find-divisor"], V["n"], V["test-divisor"]),
        expr(
            S["if"],
            expr(S[">"], expr(S["*"], V["test-divisor"], V["test-divisor"]), V["n"]),
            V["n"],
            expr(
                S["if"],
                expr(S["=="], 0, expr(S["%"], V["n"], V["test-divisor"])),
                V["test-divisor"],
                expr(S["find-divisor"], V["n"], expr(S["+"], V["test-divisor"], 1)),
            ),
        ),
    )

    # (= (prime? $n)
    #    (== $n (find-divisor $n 2)))
    m += expr(
        S["="], expr(S["prime?"], V["n"]), expr(S["=="], V["n"], expr(S["find-divisor"], V["n"], 2))
    )

    # !(test (msort (collapse (let $xs (3 1 2) (hyperpose $xs))))
    #        (1 2 3))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["msort"],
                expr(
                    S["collapse"],
                    expr(S["let"], V["xs"], expr(3, 1, 2), expr(S["hyperpose"], V["xs"])),
                ),
            ),
            expr(1, 2, 3),
        )
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

    yield from ()
