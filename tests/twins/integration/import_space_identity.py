"""The Python twin of examples/integration/import_space_identity.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 9672


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(bind! &import-space-a (new-space))
    yield m.eval(expr(S["bind!"], S["&import-space-a"], expr(S["new-space"])))

    # !(bind! &import-space-b (new-space))
    yield m.eval(expr(S["bind!"], S["&import-space-b"], expr(S["new-space"])))

    # !(import! &import-space-a _fixtures/imports/overhaul/space_payload)
    yield m.eval(
        expr(
            S["import!"],
            S["&import-space-a"],
            S["examples/integration/_fixtures/imports/overhaul/space_payload"],
        )
    )

    # !(import! &import-space-b _fixtures/imports/overhaul/space_payload)
    yield m.eval(
        expr(
            S["import!"],
            S["&import-space-b"],
            S["examples/integration/_fixtures/imports/overhaul/space_payload"],
        )
    )

    # !(test (collapse (match &import-space-a (import-space-marker) present)) (present))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"], S["&import-space-a"], expr(S["import-space-marker"]), S["present"]
                ),
            ),
            expr(S["present"]),
        )
    )

    # !(test (collapse (match &import-space-b (import-space-marker) present)) (present))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"], S["&import-space-b"], expr(S["import-space-marker"]), S["present"]
                ),
            ),
            expr(S["present"]),
        )
    )

    # !(test (collapse (metta (import-space-function) %Undefined% &import-space-a)) (one-result))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["metta"],
                    expr(S["import-space-function"]),
                    S["%Undefined%"],
                    S["&import-space-a"],
                ),
            ),
            expr(S["one-result"]),
        )
    )

    # !(test (collapse (metta (import-space-function) %Undefined% &import-space-b)) (one-result))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["metta"],
                    expr(S["import-space-function"]),
                    S["%Undefined%"],
                    S["&import-space-b"],
                ),
            ),
            expr(S["one-result"]),
        )
    )

    # !(test (collapse (import-space-function)) ((import-space-function)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["import-space-function"])),
            expr(expr(S["import-space-function"])),
        )
    )

    yield from ()
