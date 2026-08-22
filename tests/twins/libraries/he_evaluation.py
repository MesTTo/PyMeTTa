"""The Python twin of examples/libraries/he_evaluation.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 11926


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # (= (double $x) (+ $x $x))
    m += expr(S["="], expr(S["double"], V["x"]), expr(S["+"], V["x"], V["x"]))

    # !(test (eval (double 5)) 10)
    yield m.eval(expr(S["test"], expr(S["eval"], expr(S["double"], 5)), 10))

    # !(test (evalc (+ 5 5) &self) 10)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["+"], 5, 5), S["&self"]), 10))

    # !(test (chain (+ 2 3) $x (* $x 2)) 10)
    yield m.eval(
        expr(S["test"], expr(S["chain"], expr(S["+"], 2, 3), V["x"], expr(S["*"], V["x"], 2)), 10)
    )

    # !(test (for-each-in-atom (1 3 5 62 2 5) println!)
    #        (() () () () () ()))
    yield m.eval(
        expr(
            S["test"],
            expr(S["for-each-in-atom"], expr(1, 3, 5, 62, 2, 5), S["println!"]),
            expr(expr(), expr(), expr(), expr(), expr(), expr()),
        )
    )

    yield from ()
