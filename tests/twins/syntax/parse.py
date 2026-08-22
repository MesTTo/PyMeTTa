"""The Python twin of examples/syntax/parse.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 2238


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (parse "A") A)
    yield None

    # !(test (parse "(R A B)") (R A B))
    yield None

    # !(test (parse "(R A (S B C))") (R A (S B C)))
    yield None

    # !(test (parse "(* 2 21)") (noeval (* 2 21)))
    yield None

    # !(test (parse "\"42\"") "42")
    yield None

    # !(test (parse (repr "C:\\Users\\bob")) "C:\\Users\\bob")
    yield m.eval(
        expr(
            S["test"],
            expr(S["parse"], expr(S["repr"], val("C:\\Users\\bob"))),
            val("C:\\Users\\bob"),
        )
    )

    # !(test (parse (repr "say \"hi\"")) "say \"hi\"")
    yield m.eval(
        expr(S["test"], expr(S["parse"], expr(S["repr"], val('say "hi"'))), val('say "hi"'))
    )

    # !(test (parse (repr "a\\nb")) "a\\nb")
    yield m.eval(expr(S["test"], expr(S["parse"], expr(S["repr"], val("a\\nb"))), val("a\\nb")))

    yield from ()
