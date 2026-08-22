"""The Python twin of examples/libraries/tabling_statistics.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 104258


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_tabling))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_tabling"])))

    # !(add-atom &self (edge a b))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["edge"], S["a"], S["b"])))

    # (= (reach $x $y) (match &self (edge $x $y) $y))
    m += expr(
        S["="],
        expr(S["reach"], V["x"], V["y"]),
        expr(S["match"], S["&self"], expr(S["edge"], V["x"], V["y"]), V["y"]),
    )

    # !(tabled (reach $x $y))
    yield m.eval(expr(S["tabled"], expr(S["reach"], V["x"], V["y"])))

    # !(collapse (reach a $y))
    yield m.eval(expr(S["collapse"], expr(S["reach"], S["a"], V["y"])))

    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 0) (reevaluated 0)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["table-stats"], expr(S["reach"], V["x"], V["y"])),
            expr(
                expr(S["tables"], 1),
                expr(S["answers"], 1),
                expr(S["complete-call"], 1),
                expr(S["invalidated"], 0),
                expr(S["reevaluated"], 0),
            ),
        )
    )

    # !(add-atom &self (edge b d))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["edge"], S["b"], S["d"])))

    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 0) (reevaluated 0)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["table-stats"], expr(S["reach"], V["x"], V["y"])),
            expr(
                expr(S["tables"], 1),
                expr(S["answers"], 1),
                expr(S["complete-call"], 1),
                expr(S["invalidated"], 0),
                expr(S["reevaluated"], 0),
            ),
        )
    )

    # !(add-atom &self (unrelated x y))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["unrelated"], S["x"], S["y"])))

    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 0) (reevaluated 0)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["table-stats"], expr(S["reach"], V["x"], V["y"])),
            expr(
                expr(S["tables"], 1),
                expr(S["answers"], 1),
                expr(S["complete-call"], 1),
                expr(S["invalidated"], 0),
                expr(S["reevaluated"], 0),
            ),
        )
    )

    # !(add-atom &self (edge a c))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["edge"], S["a"], S["c"])))

    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 1) (reevaluated 0)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["table-stats"], expr(S["reach"], V["x"], V["y"])),
            expr(
                expr(S["tables"], 1),
                expr(S["answers"], 1),
                expr(S["complete-call"], 1),
                expr(S["invalidated"], 1),
                expr(S["reevaluated"], 0),
            ),
        )
    )

    # !(test (sort-atom (collapse (reach a $y))) (b c))
    yield m.eval(
        expr(
            S["test"],
            expr(S["sort-atom"], expr(S["collapse"], expr(S["reach"], S["a"], V["y"]))),
            expr(S["b"], S["c"]),
        )
    )

    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 2) (complete-call 3) (invalidated 1) (reevaluated 1)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["table-stats"], expr(S["reach"], V["x"], V["y"])),
            expr(
                expr(S["tables"], 1),
                expr(S["answers"], 2),
                expr(S["complete-call"], 3),
                expr(S["invalidated"], 1),
                expr(S["reevaluated"], 1),
            ),
        )
    )

    yield from ()
