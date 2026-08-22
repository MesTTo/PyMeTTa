"""The Python twin of examples/libraries/conformance.metta.

Proving a Prolog space provider before its users find out.

`petta.testing.check_space_provider` takes a Python OBJECT, so the seam's faster
tier had no way to prove itself; this is the same three checks asked of a space
NAME, so every form here is a term over that name.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 60375 to 60375, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 60375 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 60375


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_conformance))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_conformance)))

    # The provider under test is a complete one in eight lines,
    # _fixtures/demo_provider.pl. It declares an EXTENSION and exports nothing,
    # which is the shape of a provider-only file.
    # !(import_prolog_functions_from_file "./examples/libraries/_fixtures/demo_provider.pl" ())
    yield m.eval(
        S.import_prolog_functions_from_file(
            val("./examples/libraries/_fixtures/demo_provider.pl"), ()
        )
    )

    # The checks that ran, in order: one per declared capability, then the
    # over-approximation contract, then the pushdown claim.
    # !(test (check-space-provider &demo_provider) ("match: ..." ...))
    yield m.eval(
        S.test(
            S["check-space-provider"](S["&demo_provider"]),
            (
                val("match: declared, seam:foreign_match/3 has clauses"),
                val("enumerate: declared, seam:foreign_atoms/2 has clauses"),
                val("match: over-approximation holds over 2 atoms"),
                val("pushdown: 0 of 2 patterns claimed exact, and are"),
                val("plan: not declared, so a conjunction takes the engine's split"),
            ),
        )
    )

    # And it answers through the seam, which is the point of proving it.
    # !(test (sort-atom (collapse (match &demo_provider (edge a $y) $y))) (b))
    yield m.eval(
        S.test(
            S["sort-atom"](
                S.collapse(S.match(S["&demo_provider"], S.edge(S.a, V.y), V.y))
            ),
            (S.b,),
        )
    )
