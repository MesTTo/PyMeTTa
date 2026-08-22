"""The Python twin of examples/integration/c_space/c_space.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 141295


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_import))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_import"])))

    # !(import! &self (library lib_file))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_file"])))

    # !(import! &self (library lib_conformance))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_conformance"])))

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (let "./examples/integration/c_space/cstore.pl" (consult_global) provider)
    #      (println! "SKIPPED c_space: cstore.so is not built, see the README beside this file"))
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_space/cstore.so")),
            expr(
                S["let"],
                val("./examples/integration/c_space/cstore.pl"),
                expr(S["consult_global"]),
                S["provider"],
            ),
            expr(
                S["println!"],
                val("SKIPPED c_space: cstore.so is not built, see the README beside this file"),
            ),
        )
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (progn (add-atom &cstore (edge a b))
    #             (add-atom &cstore (edge a c))
    #             (add-atom &cstore (edge b c))
    #             (test (collapse (match &cstore (edge a $x) $x)) (b c)))
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_space/cstore.so")),
            expr(
                S["progn"],
                expr(S["add-atom"], S["&cstore"], expr(S["edge"], S["a"], S["b"])),
                expr(S["add-atom"], S["&cstore"], expr(S["edge"], S["a"], S["c"])),
                expr(S["add-atom"], S["&cstore"], expr(S["edge"], S["b"], S["c"])),
                expr(
                    S["test"],
                    expr(
                        S["collapse"],
                        expr(S["match"], S["&cstore"], expr(S["edge"], S["a"], V["x"]), V["x"]),
                    ),
                    expr(S["b"], S["c"]),
                ),
            ),
            val(value=True),
        )
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (progn (remove-atom &cstore (edge a $any))
    #             (test (size-atom (collapse (match &cstore (edge $x $y) ($x $y)))) 2)
    #             (remove-atom &cstore (edge a $other))
    #             (test (collapse (match &cstore (edge $x $y) ($x $y))) ((b c))))
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_space/cstore.so")),
            expr(
                S["progn"],
                expr(S["remove-atom"], S["&cstore"], expr(S["edge"], S["a"], V["any"])),
                expr(
                    S["test"],
                    expr(
                        S["size-atom"],
                        expr(
                            S["collapse"],
                            expr(
                                S["match"],
                                S["&cstore"],
                                expr(S["edge"], V["x"], V["y"]),
                                expr(V["x"], V["y"]),
                            ),
                        ),
                    ),
                    2,
                ),
                expr(S["remove-atom"], S["&cstore"], expr(S["edge"], S["a"], V["other"])),
                expr(
                    S["test"],
                    expr(
                        S["collapse"],
                        expr(
                            S["match"],
                            S["&cstore"],
                            expr(S["edge"], V["x"], V["y"]),
                            expr(V["x"], V["y"]),
                        ),
                    ),
                    expr(expr(S["b"], S["c"])),
                ),
            ),
            val(value=True),
        )
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (progn (add-atom &cstore (dup 1))
    #             (add-atom &cstore (dup 1))
    #             (add-atom &cstore (dup 1))
    #             (remove-atom &cstore (dup 1))
    #             (test (size-atom (collapse (match &cstore (dup $n) $n))) 2)
    #             (remove-atom &cstore (dup 1))
    #             (remove-atom &cstore (dup 1))
    #             (test (size-atom (collapse (match &cstore (dup $n) $n))) 0))
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_space/cstore.so")),
            expr(
                S["progn"],
                expr(S["add-atom"], S["&cstore"], expr(S["dup"], 1)),
                expr(S["add-atom"], S["&cstore"], expr(S["dup"], 1)),
                expr(S["add-atom"], S["&cstore"], expr(S["dup"], 1)),
                expr(S["remove-atom"], S["&cstore"], expr(S["dup"], 1)),
                expr(
                    S["test"],
                    expr(
                        S["size-atom"],
                        expr(
                            S["collapse"],
                            expr(S["match"], S["&cstore"], expr(S["dup"], V["n"]), V["n"]),
                        ),
                    ),
                    2,
                ),
                expr(S["remove-atom"], S["&cstore"], expr(S["dup"], 1)),
                expr(S["remove-atom"], S["&cstore"], expr(S["dup"], 1)),
                expr(
                    S["test"],
                    expr(
                        S["size-atom"],
                        expr(
                            S["collapse"],
                            expr(S["match"], S["&cstore"], expr(S["dup"], V["n"]), V["n"]),
                        ),
                    ),
                    0,
                ),
            ),
            val(value=True),
        )
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (test (check-space-provider &cstore)
    #            ("enumerate: declared, seam:foreign_atoms/2 has clauses"
    #             "add: declared, seam:foreign_add/2 has clauses"
    #             "remove: declared, seam:foreign_remove/3 has clauses"
    #             "clear: declared, seam:foreign_clear/1 has clauses"
    #             "match: over-approximation holds over 1 atoms"
    #             "pushdown: 0 of 1 patterns claimed exact, and are"
    #             "plan: not declared, so a conjunction takes the engine's split"))
    #      True)
    yield m.eval(
        expr(
            S["if"],
            expr(S["file-exists"], val("./examples/integration/c_space/cstore.so")),
            expr(
                S["test"],
                expr(S["check-space-provider"], S["&cstore"]),
                expr(
                    val("enumerate: declared, seam:foreign_atoms/2 has clauses"),
                    val("add: declared, seam:foreign_add/2 has clauses"),
                    val("remove: declared, seam:foreign_remove/3 has clauses"),
                    val("clear: declared, seam:foreign_clear/1 has clauses"),
                    val("match: over-approximation holds over 1 atoms"),
                    val("pushdown: 0 of 1 patterns claimed exact, and are"),
                    val("plan: not declared, so a conjunction takes the engine's split"),
                ),
            ),
            val(value=True),
        )
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (progn (collapse (hyperpose ((add-atom &cstore (row 1))
    #                                   (add-atom &cstore (row 2))
    #                                   (add-atom &cstore (row 3))
    #                                   (add-atom &cstore (row 4)))))
    #             (test (size-atom (collapse (match &cstore (row $n) $n))) 4))
    #      True)
    yield None

    yield from ()
