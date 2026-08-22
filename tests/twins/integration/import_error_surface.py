"""The Python twin of examples/integration/import_error_surface.metta.

Two failing imports, one broken and one missing, both surfacing as `Error`
through `catch` and `if-error`. The paths stay RELATIVE here, unlike the
sibling import twins: these forms are asserting that the import FAILS, and a
path that resolves against nothing fails the same way the example's does.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 9499


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    # !(test (if-error (catch (import! &self _fixtures/imports/import_error_broken))
    #                  Error
    #                  NoError)
    #        Error)
    yield m.eval(
        S.test(S["if-error"](
                S.catch(
                    S["import!"](S["&self"], S["_fixtures/imports/import_error_broken"])
                ),
                S.Error,
                S.NoError),
            S.Error)
    )

    # !(test (if-error (catch (import! &self _fixtures/imports/definitely_missing_import))
    #                  Error
    #                  NoError)
    #        Error)
    yield m.eval(
        S.test(S["if-error"](
                S.catch(
                    S["import!"](S["&self"], S["_fixtures/imports/definitely_missing_import"])
                ),
                S.Error,
                S.NoError),
            S.Error)
    )
