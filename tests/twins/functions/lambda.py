"""The Python twin of examples/functions/lambda.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 15085


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (: apply (-> Atom %Undefined% %Undefined%))
    m += expr(S[":"], S["apply"], expr(S["->"], S["Atom"], S["%Undefined%"], S["%Undefined%"]))

    # (= (apply (lambda $var $body) $arg)
    #    (eval (let $var $arg $body)))
    m += expr(
        S["="],
        expr(S["apply"], expr(S["lambda"], V["var"], V["body"]), V["arg"]),
        expr(S["eval"], expr(S["let"], V["var"], V["arg"], V["body"])),
    )

    # (= (applyL1)
    #    (apply (lambda $x (+ $x 1)) 2))
    m += expr(
        S["="],
        expr(S["applyL1"]),
        expr(S["apply"], expr(S["lambda"], V["x"], expr(S["+"], V["x"], 1)), 2),
    )

    # (= (applyL2)
    #    (apply (lambda ($x $y) (+ $x $y)) (2 7)))
    m += expr(
        S["="],
        expr(S["applyL2"]),
        expr(
            S["apply"],
            expr(S["lambda"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
            expr(2, 7),
        ),
    )

    # !(test (applyL1) 3)
    yield m.eval(expr(S["test"], expr(S["applyL1"]), 3))

    # !(test (applyL2) 9)
    yield m.eval(expr(S["test"], expr(S["applyL2"]), 9))

    # !(test (maplist (|-> ($a) (+ 1 $a)) (1 2 3))
    #        (2 3 4))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["maplist"], expr(S["|->"], expr(V["a"]), expr(S["+"], 1, V["a"])), expr(1, 2, 3)
            ),
            expr(2, 3, 4),
        )
    )

    # !(test ((|-> ($acc $e) (or (== 1 $e) $acc)) False 1)
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                expr(
                    S["|->"],
                    expr(V["acc"], V["e"]),
                    expr(S["or"], expr(S["=="], 1, V["e"]), V["acc"]),
                ),
                val(value=False),
                1,
            ),
            val(value=True),
        )
    )

    # (= (myfunc $a $b) (cons $a $b))
    m += expr(S["="], expr(S["myfunc"], V["a"], V["b"]), expr(S["cons"], V["a"], V["b"]))

    # !(test (let $f (myfunc 42)
    #             ((|-> ($x) ($f ($x 2 3))) 43))
    #        (42 43 2 3))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["f"],
                expr(S["myfunc"], 42),
                expr(expr(S["|->"], expr(V["x"]), expr(V["f"], expr(V["x"], 2, 3))), 43),
            ),
            expr(42, 43, 2, 3),
        )
    )

    # !(test (((|-> ($x $y) (42 $x $y)) 43) 44)
    #        (42 43 44))
    yield m.eval(
        expr(
            S["test"],
            expr(expr(expr(S["|->"], expr(V["x"], V["y"]), expr(42, V["x"], V["y"])), 43), 44),
            expr(42, 43, 44),
        )
    )

    # (= (myfunc2 $mylambda)
    #    ($mylambda 43 44))
    m += expr(S["="], expr(S["myfunc2"], V["mylambda"]), expr(V["mylambda"], 43, 44))

    # !(test (let* (($k 45)
    #               ($lambda (|-> ($x $y) (42 $x $y $k))))
    #              (myfunc2 $lambda))
    #        (42 43 44 45))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let*"],
                expr(
                    expr(V["k"], 45),
                    expr(
                        V["lambda"],
                        expr(S["|->"], expr(V["x"], V["y"]), expr(42, V["x"], V["y"], V["k"])),
                    ),
                ),
                expr(S["myfunc2"], V["lambda"]),
            ),
            expr(42, 43, 44, 45),
        )
    )

    yield from ()
