"""The Python twin of examples/reasoning/newtons_method.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 145159


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (energy $x $n)
    #    (if (<= $n 0)
    #        (* $x $x)
    #        (+ (energy (+ (* 0.5 $x) 0.4) (- $n 1))
    #           (energy (+ (* 0.5 $x) 0.4) (- $n 1)))))
    m += expr(
        S["="],
        expr(S["energy"], V["x"], V["n"]),
        expr(
            S["if"],
            expr(S["<="], V["n"], 0),
            expr(S["*"], V["x"], V["x"]),
            expr(
                S["+"],
                expr(
                    S["energy"],
                    expr(S["+"], expr(S["*"], 0.5, V["x"]), 0.4),
                    expr(S["-"], V["n"], 1),
                ),
                expr(
                    S["energy"],
                    expr(S["+"], expr(S["*"], 0.5, V["x"]), 0.4),
                    expr(S["-"], V["n"], 1),
                ),
            ),
        ),
    )

    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(config-memoize (strategy wtinylfu) (unique-limit 100))
    yield m.eval(
        expr(S["config-memoize"], expr(S["strategy"], S["wtinylfu"]), expr(S["unique-limit"], 100))
    )

    # !(memoize energy)
    yield m.eval(expr(S["memoize"], S["energy"]))

    # !(test (energy 2.0 0) 4.0)
    yield m.eval(expr(S["test"], expr(S["energy"], 2.0, 0), 4.0))

    # !(test (energy 2.0 1) 3.9199999999999995)
    yield m.eval(expr(S["test"], expr(S["energy"], 2.0, 1), 3.9199999999999995))

    yield from ()
