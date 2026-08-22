"""The Python twin of examples/libraries/foreign_rules.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 48124


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_import))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_import"])))

    # !(import_prolog_functions_from_file "./examples/libraries/_fixtures/rule_provider.pl" ())
    yield m.eval(
        expr(
            S["import_prolog_functions_from_file"],
            val("./examples/libraries/_fixtures/rule_provider.pl"),
            expr(),
        )
    )

    # !(add-atom &rule_demo (= (fdouble $x) (* 2 $x)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&rule_demo"],
            expr(S["="], expr(S["fdouble"], V["x"]), expr(S["*"], 2, V["x"])),
        )
    )

    # !(test (metta (fdouble 21) %Undefined% &rule_demo) 42)
    yield m.eval(
        expr(
            S["test"],
            expr(S["metta"], expr(S["fdouble"], 21), S["%Undefined%"], S["&rule_demo"]),
            42,
        )
    )

    # !(add-atom &rule_demo (= (fpick) one))
    yield m.eval(expr(S["add-atom"], S["&rule_demo"], expr(S["="], expr(S["fpick"]), S["one"])))

    # !(add-atom &rule_demo (= (fpick) two))
    yield m.eval(expr(S["add-atom"], S["&rule_demo"], expr(S["="], expr(S["fpick"]), S["two"])))

    # !(test (sort-atom (collapse (metta (fpick) %Undefined% &rule_demo))) (one two))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["sort-atom"],
                expr(
                    S["collapse"],
                    expr(S["metta"], expr(S["fpick"]), S["%Undefined%"], S["&rule_demo"]),
                ),
            ),
            expr(S["one"], S["two"]),
        )
    )

    # !(add-atom &rule_demo (= (fplain) settled))
    yield m.eval(
        expr(S["add-atom"], S["&rule_demo"], expr(S["="], expr(S["fplain"]), S["settled"]))
    )

    # !(test (metta (fplain) %Undefined% &rule_demo) settled)
    yield m.eval(
        expr(
            S["test"],
            expr(S["metta"], expr(S["fplain"]), S["%Undefined%"], S["&rule_demo"]),
            S["settled"],
        )
    )

    # !(add-atom &rule_demo (= (fnest) (+ 1 (* 2 3))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&rule_demo"],
            expr(S["="], expr(S["fnest"]), expr(S["+"], 1, expr(S["*"], 2, 3))),
        )
    )

    # !(test (metta (fnest) %Undefined% &rule_demo) 7)
    yield m.eval(
        expr(S["test"], expr(S["metta"], expr(S["fnest"]), S["%Undefined%"], S["&rule_demo"]), 7)
    )

    # !(add-atom &rule_demo (= (ffact $x) (if (> $x 0) (* $x (ffact (- $x 1))) 1)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&rule_demo"],
            expr(
                S["="],
                expr(S["ffact"], V["x"]),
                expr(
                    S["if"],
                    expr(S[">"], V["x"], 0),
                    expr(S["*"], V["x"], expr(S["ffact"], expr(S["-"], V["x"], 1))),
                    1,
                ),
            ),
        )
    )

    # !(test (metta (ffact 5) %Undefined% &rule_demo) 120)
    yield m.eval(
        expr(
            S["test"], expr(S["metta"], expr(S["ffact"], 5), S["%Undefined%"], S["&rule_demo"]), 120
        )
    )

    # !(add-atom &rule_demo (edge a b))
    yield m.eval(expr(S["add-atom"], S["&rule_demo"], expr(S["edge"], S["a"], S["b"])))

    # !(test (collapse (match &rule_demo (edge $x $y) ($x $y))) ((a b)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"],
                    S["&rule_demo"],
                    expr(S["edge"], V["x"], V["y"]),
                    expr(V["x"], V["y"]),
                ),
            ),
            expr(expr(S["a"], S["b"])),
        )
    )

    yield from ()
