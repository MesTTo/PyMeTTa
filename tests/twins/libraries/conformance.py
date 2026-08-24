"""examples/libraries/conformance.metta in Python: proving a Prolog provider.

`metta.testing.check_space_provider` takes a Python OBJECT, so the seam's
faster tier had no way to prove itself: a Prolog provider is a set of multifile
clauses and there is nothing to pass. `check-space-provider` asks the same
three checks of a space, and this file is that function's own example, so the
twin names it. The space it checks is handed over as the HANDLE it is, reached
by ATOM rather than by text, because a space name is a symbol.

The second claim needs nothing MeTTa-side at all: the provider answers through
the seam, so its space has a handle like any other and the query is the
handle's own. `sort-atom` around it is `sorted`.

Three names keep the bracket because their MeTTa spelling really has
underscores: `lib_conformance`, `import_prolog_functions_from_file` and the
provider's own `demo_provider`. The attribute door maps every underscore to a
hyphen, so `S.lib_conformance` is the library `lib-conformance`, which does not
exist.
"""

import metta
from metta import G, S, V

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1

#: The provider under test, complete in eight lines. It declares an EXTENSION
#: and exports nothing, which is the shape of a provider-only file:
#: metta_export is for functions and a provider has none.
PROVIDER = G("./examples/libraries/_fixtures/demo_provider.pl")


def twin(m):
    """Run the seam's own conformance checks, then query through the seam."""
    m.fn["import!"](m, S.library(S["lib_conformance"]))
    m.eval(S["import_prolog_functions_from_file"](PROVIDER, ()))

    demo = metta.space(S["demo_provider"])

    # The checks that ran, in order: one per declared capability, then the
    # over-approximation contract, then the pushdown claim.
    [checked] = m.fn.check_space_provider(demo)
    assert list(checked) == [
        G("match: declared, seam:foreign_match/3 has clauses"),
        G("enumerate: declared, seam:foreign_atoms/2 has clauses"),
        G("match: over-approximation holds over 2 atoms"),
        G("pushdown: 0 of 2 patterns claimed exact, and are"),
        G("plan: not declared, so a conjunction takes the engine's split"),
    ]

    # And it answers through the seam, which is the point of proving it.
    assert sorted(row.y for row in demo.match(S.edge(S.a, V.y))) == [S.b]
