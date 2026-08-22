"""The Python twin of examples/spaces/restricted_spaces.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 44917


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(new-space &locked (restricted))
    yield m.eval(expr(S["new-space"], S["&locked"], expr(S["restricted"])))

    # !(add-atom &locked (= (double $x) (* $x 2)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&locked"],
            expr(S["="], expr(S["double"], V["x"]), expr(S["*"], V["x"], 2)),
        )
    )

    # !(test (evalc (double 21) &locked) 42)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["double"], 21), S["&locked"]), 42))

    # !(test
    #    (if-error
    #       (catch
    #          (evalc
    #             (exists_file "examples/spaces/restricted_spaces.metta")
    #             &locked))
    #       refused
    #       answered)
    #    refused)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(
                    S["catch"],
                    expr(
                        S["evalc"],
                        expr(S["exists_file"], val("examples/spaces/restricted_spaces.metta")),
                        S["&locked"],
                    ),
                ),
                S["refused"],
                S["answered"],
            ),
            S["refused"],
        )
    )

    # !(new-space &reader (restricted (grants file)))
    yield m.eval(
        expr(S["new-space"], S["&reader"], expr(S["restricted"], expr(S["grants"], S["file"])))
    )

    # !(test
    #    (evalc
    #       (exists_file "examples/spaces/restricted_spaces.metta")
    #       &reader)
    #    true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["evalc"],
                expr(S["exists_file"], val("examples/spaces/restricted_spaces.metta")),
                S["&reader"],
            ),
            val(value=True),
        )
    )

    yield from ()
