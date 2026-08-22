"""The Python twin of examples/performance/superpose_primes.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 536577


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

    # !(test (with-pragma! ((max-stack-depth 1000000))
    #          ((prime? 53537257)
    #           (prime? 53781811)
    #           (prime? 54218443)
    #           (prime? 54734431)))
    #        (True True True True))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["with-pragma!"],
                expr(expr(S["max-stack-depth"], 1000000)),
                expr(
                    expr(S["prime?"], 53537257),
                    expr(S["prime?"], 53781811),
                    expr(S["prime?"], 54218443),
                    expr(S["prime?"], 54734431),
                ),
            ),
            expr(val(value=True), val(value=True), val(value=True), val(value=True)),
        )
    )

    yield from ()
