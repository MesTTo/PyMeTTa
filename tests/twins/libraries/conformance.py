"""examples/libraries/conformance.metta in Python: proving a Prolog provider.

`petta.testing.check_space_provider` takes a Python OBJECT, so the seam's
faster tier had no way to prove itself: a Prolog provider is a set of multifile
clauses and there is nothing to pass. `check-space-provider` asks the same
three checks of a space NAME, and this file is that function's own example, so
the twin names it.

The second claim needs nothing MeTTa-side at all: the provider answers through
the seam, so its space has a handle like any other and the query is a
subscript. `sort-atom` around it is `sorted`.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 60375 to 57296, -3079 (-5.10%), by the idiomatic
#: rewrite: the two `test` wrappers left the engine for `assert`, and the
#: `collapse` and `sort-atom` around the seam query left for `sorted` over
#: the space handle's own subscript; the conformance check itself and one
#: query through the provider are what still run there. Measured min-of-three
#: with the MORK backend linked into this worktree, which the earlier figure
#: may not have been. Prior: 60375 was the last figure for the generator twin
#: that yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 57296

#: The provider under test, complete in eight lines. It declares an EXTENSION
#: and exports nothing, which is the shape of a provider-only file:
#: metta_export is for functions and a provider has none.
PROVIDER = val("./examples/libraries/_fixtures/demo_provider.pl")


def twin(m):
    """Run the seam's own conformance checks, then query through the seam."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_conformance)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes
    m.eval(S.import_prolog_functions_from_file(PROVIDER, ()))

    # The checks that ran, in order: one per declared capability, then the
    # over-approximation contract, then the pushdown claim.
    checked = m.fn("check-space-provider")(S["&demo_provider"])  # rung: the checked space is this function's ARGUMENT, and it is named rather than handed over because a space handle does not encode as an atom
    assert list(checked) == [
        val("match: declared, seam:foreign_match/3 has clauses"),
        val("enumerate: declared, seam:foreign_atoms/2 has clauses"),
        val("match: over-approximation holds over 2 atoms"),
        val("pushdown: 0 of 2 patterns claimed exact, and are"),
        val("plan: not declared, so a conjunction takes the engine's split"),
    ]

    # And it answers through the seam, which is the point of proving it.
    demo = m.space("&demo_provider")
    assert sorted(demo.query(S.edge(S.a, V.y))["y"], key=str) == [S.b]
