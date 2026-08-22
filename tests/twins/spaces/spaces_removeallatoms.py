"""The Python twin of examples/spaces/spaces_removeallatoms.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 23683


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_spaces))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_spaces"])))

    # (friend tim tom)
    m += expr(S["friend"], S["tim"], S["tom"])

    # (= (f $x) 42)
    m += expr(S["="], expr(S["f"], V["x"]), 42)

    # !(remove-all-atoms &self)
    yield m.eval(expr(S["remove-all-atoms"], S["&self"]))

    # !(test (repr (remove-all-atoms &self))
    #        "(remove-all-atoms &self)")
    yield m.eval(
        expr(
            S["test"],
            expr(S["repr"], expr(S["remove-all-atoms"], S["&self"])),
            val("(remove-all-atoms &self)"),
        )
    )

    # !(test (repr (f 42))
    #        "(f 42)")
    yield m.eval(expr(S["test"], expr(S["repr"], expr(S["f"], 42)), val("(f 42)")))

    # !(test (collapse (get-atoms &self))
    #        ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["get-atoms"], S["&self"])), expr()))

    yield from ()
