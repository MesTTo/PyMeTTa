"""The Python twin of examples/performance/holbenchmark.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 139184129


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (map-flat $f ()) ())
    m += expr(S["="], expr(S["map-flat"], V["f"], expr()), expr())

    # (= (map-flat $f (cons $x $xs)) (cons ($f $x) (map-flat $f $xs)))
    m += expr(
        S["="],
        expr(S["map-flat"], V["f"], expr(S["cons"], V["x"], V["xs"])),
        expr(S["cons"], expr(V["f"], V["x"]), expr(S["map-flat"], V["f"], V["xs"])),
    )

    # (= (range $n)
    #    (if (== $n 0) ()
    #        (cons $n (range (- $n 1)))))
    m += expr(
        S["="],
        expr(S["range"], V["n"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            expr(),
            expr(S["cons"], V["n"], expr(S["range"], expr(S["-"], V["n"], 1))),
        ),
    )

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (let $temp (map-flat (+ 1) (range 1000000))
    #                           (length $temp)))
    #        1000000)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["with-pragma!"],
                expr(expr(S["max-stack-depth"], 100000000)),
                expr(
                    S["let"],
                    V["temp"],
                    expr(S["map-flat"], expr(S["+"], 1), expr(S["range"], 1000000)),
                    expr(S["length"], V["temp"]),
                ),
            ),
            1000000,
        )
    )

    # (= (fold-nested $f $init ()) $init)
    m += expr(S["="], expr(S["fold-nested"], V["f"], V["init"], expr()), V["init"])

    # (= (fold-nested $f $init (cons $x $xs))
    #       (if (is-expr $x)
    #         (fold-nested $f (fold-nested $f $init $x) $xs)
    #         (fold-nested $f ($f $init $x) $xs)))
    m += expr(
        S["="],
        expr(S["fold-nested"], V["f"], V["init"], expr(S["cons"], V["x"], V["xs"])),
        expr(
            S["if"],
            expr(S["is-expr"], V["x"]),
            expr(
                S["fold-nested"], V["f"], expr(S["fold-nested"], V["f"], V["init"], V["x"]), V["xs"]
            ),
            expr(S["fold-nested"], V["f"], expr(V["f"], V["init"], V["x"]), V["xs"]),
        ),
    )

    # (= (deep-nest $n)
    #    (if (== $n 0) ()
    #        (cons (range 50) (deep-nest (- $n 1)))))
    m += expr(
        S["="],
        expr(S["deep-nest"], V["n"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            expr(),
            expr(S["cons"], expr(S["range"], 50), expr(S["deep-nest"], expr(S["-"], V["n"], 1))),
        ),
    )

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (fold-nested + 0 (deep-nest 20000)))
    #        25500000)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["with-pragma!"],
                expr(expr(S["max-stack-depth"], 100000000)),
                expr(S["fold-nested"], S["+"], 0, expr(S["deep-nest"], 20000)),
            ),
            25500000,
        )
    )

    # (= (apply-many $f $n $x)
    #    (if (== $n 0) $x
    #        (apply-many $f (- $n 1) ($f $x))))
    m += expr(
        S["="],
        expr(S["apply-many"], V["f"], V["n"], V["x"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            V["x"],
            expr(S["apply-many"], V["f"], expr(S["-"], V["n"], 1), expr(V["f"], V["x"])),
        ),
    )

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (apply-many (+ 1) 100000 0))
    #        100000)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["with-pragma!"],
                expr(expr(S["max-stack-depth"], 100000000)),
                expr(S["apply-many"], expr(S["+"], 1), 100000, 0),
            ),
            100000,
        )
    )

    # (= (poly $f $n)
    #    (if (== $n 0) 0
    #        (+ ($f $n) (poly $f (- $n 1)))))
    m += expr(
        S["="],
        expr(S["poly"], V["f"], V["n"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            0,
            expr(S["+"], expr(V["f"], V["n"]), expr(S["poly"], V["f"], expr(S["-"], V["n"], 1))),
        ),
    )

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (poly (+ 1) 1000000))
    #        500001500000)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["with-pragma!"],
                expr(expr(S["max-stack-depth"], 100000000)),
                expr(S["poly"], expr(S["+"], 1), 1000000),
            ),
            500001500000,
        )
    )

    yield from ()
