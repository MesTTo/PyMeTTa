"""The Python twin of examples/libraries/tabling_equation_change.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 77656


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_tabling))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_tabling"])))

    # (= (pick $x) one)
    m += expr(S["="], expr(S["pick"], V["x"]), S["one"])

    # !(tabled (pick $x))
    yield m.eval(expr(S["tabled"], expr(S["pick"], V["x"])))

    # !(test (collapse (pick a)) (one))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["pick"], S["a"])), expr(S["one"])))

    # !(test (collapse (pick a)) (one))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["pick"], S["a"])), expr(S["one"])))

    # (= (pick $x) two)
    m += expr(S["="], expr(S["pick"], V["x"]), S["two"])

    # !(test (sort-atom (collapse (pick a))) (one two))
    yield m.eval(
        expr(
            S["test"],
            expr(S["sort-atom"], expr(S["collapse"], expr(S["pick"], S["a"]))),
            expr(S["one"], S["two"]),
        )
    )

    # !(remove-atom &self (= (pick $x) one))
    yield m.eval(
        expr(S["remove-atom"], S["&self"], expr(S["="], expr(S["pick"], V["x"]), S["one"]))
    )

    # !(test (collapse (pick a)) (two))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["pick"], S["a"])), expr(S["two"])))

    yield from ()
