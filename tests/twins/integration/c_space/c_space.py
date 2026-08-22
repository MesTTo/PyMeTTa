"""The Python twin of examples/integration/c_space/c_space.metta: a C-backed space.

`&cstore` is a space whose store is a C hash table reached through the provider
seam, so `add-atom` and `match` are the ordinary space operations and the C is
invisible above them. Every runnable half is guarded by `file-exists`, exactly
as the example guards them, because a C compiler is not one of the engine's
requirements.

Everything stays at the term door: the definitions name `add-atom` and match
against a NAMED space, and a compiled body names a function by exactly its MeTTa
spelling while a compiled `match()` takes its space as a literal. Both are
residue entries against P14.4.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 141295 across the rewrite: `equation(...).to(...)` and the
#: `(b c)` answer tuple build the same atoms the hand-nested `expr` calls built,
#: which the atom-level differential confirms byte-for-byte. `cstore.so` is
#: TRACKED, unlike its two c_extension siblings, so this twin's C path runs in an
#: isolated worktree without a build step. Prior: ADDED 2026-08-22 at 141295 by
#: the wave-3 twin baseline.
BUDGET = 141295


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_import))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_import)))

    # !(import! &self (library lib_file))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_file)))

    # !(import! &self (library lib_conformance))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_conformance)))

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (let "./examples/integration/c_space/cstore.pl" (consult_global) provider)
    #      (println! "SKIPPED c_space: cstore.so is not built, see the README beside this file"))
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_space/cstore.so")),
            S.let(val("./examples/integration/c_space/cstore.pl"),
                S.consult_global(),
                S.provider),
            S["println!"](
                val("SKIPPED c_space: cstore.so is not built, see the README beside this file")
            ))
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (progn (add-atom &cstore (edge a b))
    #             (add-atom &cstore (edge a c))
    #             (add-atom &cstore (edge b c))
    #             (test (collapse (match &cstore (edge a $x) $x)) (b c)))
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_space/cstore.so")),
            S.progn(S["add-atom"](S["&cstore"], S.edge(S.a, S.b)),
                S["add-atom"](S["&cstore"], S.edge(S.a, S.c)),
                S["add-atom"](S["&cstore"], S.edge(S.b, S.c)),
                S.test(S.collapse(S.match(S["&cstore"], S.edge(S.a, V.x), V.x)),
                    (S.b, S.c))),
            TRUE)
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (progn (remove-atom &cstore (edge a $any))
    #             (test (size-atom (collapse (match &cstore (edge $x $y) ($x $y)))) 2)
    #             (remove-atom &cstore (edge a $other))
    #             (test (collapse (match &cstore (edge $x $y) ($x $y))) ((b c))))
    #      True)
    yield m.eval(
        S["if"](S["file-exists"](val("./examples/integration/c_space/cstore.so")),
            S.progn(S["remove-atom"](S["&cstore"], S.edge(S.a, V.any)),
                S.test(S["size-atom"](S.collapse(S.match(S["&cstore"],
                                S.edge(V.x, V.y),
                                (V.x, V.y)))),
                    2),
                S["remove-atom"](S["&cstore"], S.edge(S.a, V.other)),
                S.test(S.collapse(S.match(S["&cstore"],
                            S.edge(V.x, V.y),
                            (V.x, V.y))),
                    (S.b(S.c),))),
            TRUE)
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
        S["if"](S["file-exists"](val("./examples/integration/c_space/cstore.so")),
            S.progn(S["add-atom"](S["&cstore"], S.dup(1)),
                S["add-atom"](S["&cstore"], S.dup(1)),
                S["add-atom"](S["&cstore"], S.dup(1)),
                S["remove-atom"](S["&cstore"], S.dup(1)),
                S.test(S["size-atom"](S.collapse(S.match(S["&cstore"], S.dup(V.n), V.n))),
                    2),
                S["remove-atom"](S["&cstore"], S.dup(1)),
                S["remove-atom"](S["&cstore"], S.dup(1)),
                S.test(S["size-atom"](S.collapse(S.match(S["&cstore"], S.dup(V.n), V.n))),
                    0)),
            TRUE)
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
        S["if"](S["file-exists"](val("./examples/integration/c_space/cstore.so")),
            S.test(S["check-space-provider"](S["&cstore"]),
                (val("enumerate: declared, seam:foreign_atoms/2 has clauses"),
                    val("add: declared, seam:foreign_add/2 has clauses"),
                    val("remove: declared, seam:foreign_remove/3 has clauses"),
                    val("clear: declared, seam:foreign_clear/1 has clauses"),
                    val("match: over-approximation holds over 1 atoms"),
                    val("pushdown: 0 of 1 patterns claimed exact, and are"),
                    val("plan: not declared, so a conjunction takes the engine's split"))),
            TRUE)
    )

    # !(if (file-exists "./examples/integration/c_space/cstore.so")
    #      (progn (collapse (hyperpose ((add-atom &cstore (row 1))
    #                                   (add-atom &cstore (row 2))
    #                                   (add-atom &cstore (row 3))
    #                                   (add-atom &cstore (row 4)))))
    #             (test (size-atom (collapse (match &cstore (row $n) $n))) 4))
    #      True)
    yield None
