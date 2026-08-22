"""The Python twin of examples/libraries/tabling_space_write.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 85285


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_tabling))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_tabling"])))

    # !(add-atom &self (edge a b))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["edge"], S["a"], S["b"])))

    # !(add-atom &self (edge b c))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["edge"], S["b"], S["c"])))

    # (= (reach $x $y) (match &self (edge $x $y) $y))
    m += expr(
        S["="],
        expr(S["reach"], V["x"], V["y"]),
        expr(S["match"], S["&self"], expr(S["edge"], V["x"], V["y"]), V["y"]),
    )

    # (= (twohop $x $z) (match &self (, (edge $x $y) (edge $y $z)) $z))
    m += expr(
        S["="],
        expr(S["twohop"], V["x"], V["z"]),
        expr(
            S["match"],
            S["&self"],
            expr(S[","], expr(S["edge"], V["x"], V["y"]), expr(S["edge"], V["y"], V["z"])),
            V["z"],
        ),
    )

    # !(tabled (reach $x $y))
    yield m.eval(expr(S["tabled"], expr(S["reach"], V["x"], V["y"])))

    # !(tabled (twohop $x $z))
    yield m.eval(expr(S["tabled"], expr(S["twohop"], V["x"], V["z"])))

    # !(test (collapse (reach a $y)) (b))
    yield m.eval(
        expr(S["test"], expr(S["collapse"], expr(S["reach"], S["a"], V["y"])), expr(S["b"]))
    )

    # !(test (collapse (twohop a $z)) (c))
    yield m.eval(
        expr(S["test"], expr(S["collapse"], expr(S["twohop"], S["a"], V["z"])), expr(S["c"]))
    )

    # !(add-atom &self (edge a c))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["edge"], S["a"], S["c"])))

    # !(test (sort-atom (collapse (reach a $y))) (b c))
    yield m.eval(
        expr(
            S["test"],
            expr(S["sort-atom"], expr(S["collapse"], expr(S["reach"], S["a"], V["y"]))),
            expr(S["b"], S["c"]),
        )
    )

    # !(remove-atom &self (edge a b))
    yield m.eval(expr(S["remove-atom"], S["&self"], expr(S["edge"], S["a"], S["b"])))

    # !(test (collapse (reach a $y)) (c))
    yield m.eval(
        expr(S["test"], expr(S["collapse"], expr(S["reach"], S["a"], V["y"])), expr(S["c"]))
    )

    # !(add-atom &self (edge c d))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["edge"], S["c"], S["d"])))

    # !(test (collapse (twohop b $z)) (d))
    yield m.eval(
        expr(S["test"], expr(S["collapse"], expr(S["twohop"], S["b"], V["z"])), expr(S["d"]))
    )

    # (= (bypattern $p) (match &self $p $p))
    m += expr(S["="], expr(S["bypattern"], V["p"]), expr(S["match"], S["&self"], V["p"], V["p"]))

    # !(test (repr (catch (tabled (bypattern $p))))
    #        "(Error (petta_tabling_unresolved_read match $_0) none)")
    yield m.eval(
        expr(
            S["test"],
            expr(S["repr"], expr(S["catch"], expr(S["tabled"], expr(S["bypattern"], V["p"])))),
            val("(Error (petta_tabling_unresolved_read match $_0) none)"),
        )
    )

    yield from ()
