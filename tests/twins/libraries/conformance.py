"""The Python twin of examples/libraries/conformance.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 60375


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_conformance))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_conformance"])))

    # !(import_prolog_functions_from_file "./examples/libraries/_fixtures/demo_provider.pl" ())
    yield m.eval(
        expr(
            S["import_prolog_functions_from_file"],
            val("./examples/libraries/_fixtures/demo_provider.pl"),
            expr(),
        )
    )

    # !(test (check-space-provider &demo_provider)
    #        ("match: declared, seam:foreign_match/3 has clauses"
    #         "enumerate: declared, seam:foreign_atoms/2 has clauses"
    #         "match: over-approximation holds over 2 atoms"
    #         "pushdown: 0 of 2 patterns claimed exact, and are"
    #         "plan: not declared, so a conjunction takes the engine's split"))
    yield m.eval(
        expr(
            S["test"],
            expr(S["check-space-provider"], S["&demo_provider"]),
            expr(
                val("match: declared, seam:foreign_match/3 has clauses"),
                val("enumerate: declared, seam:foreign_atoms/2 has clauses"),
                val("match: over-approximation holds over 2 atoms"),
                val("pushdown: 0 of 2 patterns claimed exact, and are"),
                val("plan: not declared, so a conjunction takes the engine's split"),
            ),
        )
    )

    # !(test (sort-atom (collapse (match &demo_provider (edge a $y) $y))) (b))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["sort-atom"],
                expr(
                    S["collapse"],
                    expr(S["match"], S["&demo_provider"], expr(S["edge"], S["a"], V["y"]), V["y"]),
                ),
            ),
            expr(S["b"]),
        )
    )

    yield from ()
