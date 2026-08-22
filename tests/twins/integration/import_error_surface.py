"""The Python twin of examples/integration/import_error_surface.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 9499


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # !(test (if-error (catch (import! &self _fixtures/imports/import_error_broken))
    #                  Error
    #                  NoError)
    #        Error)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(
                    S["catch"],
                    expr(S["import!"], S["&self"], S["_fixtures/imports/import_error_broken"]),
                ),
                S["Error"],
                S["NoError"],
            ),
            S["Error"],
        )
    )

    # !(test (if-error (catch (import! &self _fixtures/imports/definitely_missing_import))
    #                  Error
    #                  NoError)
    #        Error)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["if-error"],
                expr(
                    S["catch"],
                    expr(
                        S["import!"], S["&self"], S["_fixtures/imports/definitely_missing_import"]
                    ),
                ),
                S["Error"],
                S["NoError"],
            ),
            S["Error"],
        )
    )

    yield from ()
