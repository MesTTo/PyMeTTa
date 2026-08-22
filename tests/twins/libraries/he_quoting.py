"""The Python twin of examples/libraries/he_quoting.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 12127


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # !(test (quote (+ 1 2)) (quote (+ 1 2)))
    yield m.eval(
        expr(S["test"], expr(S["quote"], expr(S["+"], 1, 2)), expr(S["quote"], expr(S["+"], 1, 2)))
    )

    # !(test (eval (+ 1 2)) 3)
    yield m.eval(expr(S["test"], expr(S["eval"], expr(S["+"], 1, 2)), 3))

    # !(test (unquote (quote (+ 1 2))) 3)
    yield m.eval(expr(S["test"], expr(S["unquote"], expr(S["quote"], expr(S["+"], 1, 2))), 3))

    # !(test (repr (unquote 42)) "(unquote 42)")
    yield m.eval(expr(S["test"], expr(S["repr"], expr(S["unquote"], 42)), val("(unquote 42)")))

    # !(test (noreduce-eq (+ 1 2) (+ 1 2)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["noreduce-eq"], expr(S["+"], 1, 2), expr(S["+"], 1, 2)),
            val(value=True),
        )
    )

    # !(test (noreduce-eq (+ 1 2) 3) False)
    yield m.eval(expr(S["test"], expr(S["noreduce-eq"], expr(S["+"], 1, 2), 3), val(value=False)))

    yield from ()
