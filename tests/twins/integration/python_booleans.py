"""The Python twin of examples/integration/python_booleans.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 5917


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (repr (py-call (str true))) "True")
    yield m.eval(
        expr(
            S["test"],
            expr(S["repr"], expr(S["py-call"], expr(S["str"], val(value=True)))),
            val("True"),
        )
    )

    # !(test (repr (py-call (str false))) "False")
    yield m.eval(
        expr(
            S["test"],
            expr(S["repr"], expr(S["py-call"], expr(S["str"], val(value=False)))),
            val("False"),
        )
    )

    # !(test (py-call (sorted (true false))) (false true))
    yield m.eval(
        expr(
            S["test"],
            expr(S["py-call"], expr(S["sorted"], expr(val(value=True), val(value=False)))),
            expr(val(value=False), val(value=True)),
        )
    )

    # !(test (py-call (len (true false true))) 3)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["py-call"],
                expr(S["len"], expr(val(value=True), val(value=False), val(value=True))),
            ),
            3,
        )
    )

    # !(test (py-call (isinstance true (py-call (type false)))) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["py-call"],
                expr(
                    S["isinstance"],
                    val(value=True),
                    expr(S["py-call"], expr(S["type"], val(value=False))),
                ),
            ),
            val(value=True),
        )
    )

    # !(test (py-call (bool 1)) true)
    yield m.eval(expr(S["test"], expr(S["py-call"], expr(S["bool"], 1)), val(value=True)))

    # !(test (py-call (bool 0)) false)
    yield m.eval(expr(S["test"], expr(S["py-call"], expr(S["bool"], 0)), val(value=False)))

    # !(test (py-call (.bit_length true)) 1)
    yield m.eval(expr(S["test"], expr(S["py-call"], expr(S[".bit_length"], val(value=True))), 1))

    # !(test (repr (py-call (.upper abc))) "ABC")
    yield m.eval(
        expr(
            S["test"], expr(S["repr"], expr(S["py-call"], expr(S[".upper"], S["abc"]))), val("ABC")
        )
    )

    yield from ()
