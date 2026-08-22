"""The Python twin of examples/integration/c_extension/c_extension.metta.

A C foreign predicate called from MeTTa with nothing in between. Both runnable
halves are guarded by `file-exists`, exactly as the example guards them, because
a C compiler is not one of the engine's requirements and the example says so
when it skips rather than passing quietly.

The import has to be its own runnable form. A runnable is compiled just before
it runs, so a call written in the SAME form as its import compiles while the
name is still unregistered and stays unreduced; the twin keeps that split, and
that is why the two `m.eval` calls are not merged.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 99523 across the rewrite, and the baseline finding against
#: it was the WORKTREE, not the twin: `cbump.so` is a gitignored build artefact,
#: so an isolated checkout takes the example's own skip branch and costs less.
#: Built here with the README's `swipl-ld` line, the C path runs and the figure
#: is the pinned one. Prior: ADDED 2026-08-22 at 99523 by the wave-3 twin
#: baseline.
BUDGET = 99523


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_import))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_import)))

    # !(import! &self (library lib_file))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_file)))

    # !(if (file-exists "./examples/integration/c_extension/cbump.so")
    #      (import_prolog_functions_from_file
    #         "./examples/integration/c_extension/loader.pl" (c-bump))
    #      (println! "SKIPPED c_extension: cbump.so is not built, see the README beside this file"))
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/cbump.so")),
            S.import_prolog_functions_from_file(val("./examples/integration/c_extension/loader.pl"),
                S["c-bump"]()),
            S["println!"](
                val("SKIPPED c_extension: cbump.so is not built, see the README beside this file")
            ))
    )

    # !(if (file-exists "./examples/integration/c_extension/cbump.so")
    #      (test (eval (c-bump 41)) 42)
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/cbump.so")),
            S.test(S.eval(S["c-bump"](41)), 42),
            TRUE)
    )
