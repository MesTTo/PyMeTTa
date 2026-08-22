"""The Python twin of examples/integration/c_extension/handle.metta: a C handle.

A vector lives in C and crosses as an opaque handle, so `vector-bump` mutates
the same object every call sees. `bump-thrice` stays at the container door
because its body names `vector-new` and `vector-bump`, and a compiled body names
a function by exactly its MeTTa spelling, which neither is a Python identifier
for; the residue records that against P14.4.

Every runnable half is guarded by `file-exists`, exactly as the example guards
them, because a C compiler is not one of the engine's requirements.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 105529 across the rewrite, and the baseline finding against
#: it was the WORKTREE, not the twin: `handle.so` is a gitignored build artefact,
#: so an isolated checkout takes the example's own skip branch and costs less.
#: Built here with the README's `swipl-ld` line, the C path runs and the figure
#: is the pinned one. Prior: ADDED 2026-08-22 at 105529 by the wave-3 twin
#: baseline.
BUDGET = 105529


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_import))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_import)))

    # !(import! &self (library lib_file))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_file)))

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (import_prolog_functions_from_file
    #         "./examples/integration/c_extension/handle_loader.pl"
    #         (vector-new vector-nth vector-bump vector-length))
    #      (println! "SKIPPED handle: handle.so is not built, see the README beside this file"))
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/handle.so")),
            S.import_prolog_functions_from_file(
                val("./examples/integration/c_extension/handle_loader.pl"),
                S["vector-new"](S["vector-nth"], S["vector-bump"], S["vector-length"])),
            S["println!"](
                val("SKIPPED handle: handle.so is not built, see the README beside this file")
            ))
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (vector-length (vector-new 1000))) 1000)
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/handle.so")),
            S.test(S.eval(S["vector-length"](S["vector-new"](1000))),
                1000),
            TRUE)
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (vector-nth (vector-new 1000) 700)) 700)
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/handle.so")),
            S.test(S.eval(S["vector-nth"](S["vector-new"](1000), 700)),
                700),
            TRUE)
    )

    # (= (bump-thrice)
    #    (let $v (vector-new 4)
    #         (progn (vector-bump $v 0) (vector-bump $v 0) (vector-bump $v 0))))
    m += equation(S["bump-thrice"]()).to(S.let(V.v,
            S["vector-new"](4),
            S.progn(S["vector-bump"](V.v, 0),
                S["vector-bump"](V.v, 0),
                S["vector-bump"](V.v, 0))))

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (bump-thrice)) 3)
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/handle.so")),
            S.test(S.eval(S["bump-thrice"]()), 3),
            TRUE)
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (let $vector (vector-new 1) (get-metatype $vector)) Grounded)
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/handle.so")),
            S.test(S.let(V.vector,
                    S["vector-new"](1),
                    S["get-metatype"](V.vector)),
                S.Grounded),
            TRUE)
    )

    # !(if (file-exists "./examples/integration/c_extension/handle.so")
    #      (test (eval (let $v (vector-new 1) (== $v $v))) True)
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_extension/handle.so")),
            S.test(S.eval(S.let(V.v, S["vector-new"](1), V.v.eq(V.v))),
                TRUE),
            TRUE)
    )
