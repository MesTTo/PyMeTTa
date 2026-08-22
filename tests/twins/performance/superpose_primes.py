"""The Python twin of examples/performance/superpose_primes.metta: four searches.

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
"""

from petta import S, V, equation, val

#: The equality head, needed with a GROUND left operand, which is the one shape
#: Python's own operators cannot build.
EQ = S["=="]

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 536577 across the term-door rewrite: `equation(...).to(...)`,
#: the operators and the `(EQ, 0, ...)` tuple build the same atoms the hand-nested
#: `expr` calls built, which the atom-level differential confirms byte-for-byte.
#: The @m.define alternative was measured and REJECTED at 920726, +71.6%.
#: Prior: ADDED 2026-08-22 at 536577 by the wave-3 twin baseline.
BUDGET = 536577


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

    # !(test (with-pragma! ((max-stack-depth 1000000))
    #          ((prime? 53537257)
    #           (prime? 53781811)
    #           (prime? 54218443)
    #           (prime? 54734431)))
    #        (True True True True))
    yield m.eval(
        S.test(S["with-pragma!"]((S["max-stack-depth"](1000000),),
                (S["prime?"](53537257),
                    S["prime?"](53781811),
                    S["prime?"](54218443),
                    S["prime?"](54734431))),
            (TRUE, TRUE, TRUE, TRUE))
    )
