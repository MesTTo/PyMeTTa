"""The Python twin of examples/syntax/repr.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 3394


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (repr 42) "42")
    yield m.eval(expr(S["test"], expr(S["repr"], 42), val("42")))

    # !(test (repr "42") "\"42\"")
    yield m.eval(expr(S["test"], expr(S["repr"], val("42")), val('"42"')))

    # !(test (repr (A (B C))) "(A (B C))")
    yield m.eval(
        expr(S["test"], expr(S["repr"], expr(S["A"], expr(S["B"], S["C"]))), val("(A (B C))"))
    )

    # !(test (repr (A (, B , C ,))) "(A (, B , C ,))")
    yield m.eval(
        expr(
            S["test"],
            expr(S["repr"], expr(S["A"], expr(S[","], S["B"], S[","], S["C"], S[","]))),
            val("(A (, B , C ,))"),
        )
    )

    # !(test (repr 2025_12_12) "2025_12_12")
    yield m.eval(expr(S["test"], expr(S["repr"], S["2025_12_12"]), val("2025_12_12")))

    # !(test (repr ()) "()")
    yield m.eval(expr(S["test"], expr(S["repr"], expr()), val("()")))

    yield from ()
