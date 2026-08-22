"""The Python twin of examples/libraries/he_equalreduct.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 9738


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # (= (add 1 2) 3)
    m += expr(S["="], expr(S["add"], 1, 2), 3)

    # !(test (id 5) 5)
    yield m.eval(expr(S["test"], expr(S["id"], 5), 5))

    # !(test (=alpha (Father $X) (Father $Y)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["=alpha"], expr(S["Father"], V["X"]), expr(S["Father"], V["Y"])),
            val(value=True),
        )
    )

    # !(test (=alpha (Father $X) (Son $X)) False)
    yield m.eval(
        expr(
            S["test"],
            expr(S["=alpha"], expr(S["Father"], V["X"]), expr(S["Son"], V["X"])),
            val(value=False),
        )
    )

    # !(test (if-equal 1 1 "Equal" "Not Equal") "Equal")
    yield m.eval(
        expr(S["test"], expr(S["if-equal"], 1, 1, val("Equal"), val("Not Equal")), val("Equal"))
    )

    yield from ()
