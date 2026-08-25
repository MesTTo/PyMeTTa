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

One name keeps the bracket because its MeTTa spelling really has
underscores: the provider's own `demo_provider`. The attribute door maps
every underscore to a hyphen, so `S.demo_provider` would be the symbol
`demo-provider`, which nothing declares.
"""

from pathlib import Path

import metta
from metta import G, S, V, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 42555 to 43174, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 43174 to 43185, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
BUDGET = 43185

#: The provider under test, complete in eight lines. It declares an EXTENSION
#: and exports nothing, which is the shape of a provider-only file:
#: metta_export is for functions and a provider has none.
PROVIDER = Path("./examples/libraries/_fixtures/demo_provider.pl")


def twin(m):
    """Run the seam's own conformance checks, then query through the seam."""
    m += lib.conformance
    m.register_prolog(path=PROVIDER)

    demo = metta.space(S["demo_provider"])

    # The checks that ran, in order: one per declared capability, then the
    # match family (each position opened, repeated variables folded), the
    # source discipline, the round trip (not asked here: no add/remove),
    # the pushdown claim, and the plan split.
    [checked] = m.fn.check_space_provider(demo)
    assert list(checked) == [
        G("match: declared, seam:foreign_match/3 has clauses"),
        G("enumerate: declared, seam:foreign_atoms/2 has clauses"),
        G("match: over-approximation holds over 2 atoms and their pattern families"),
        G("source: repeated, two enumerations agree"),
        G(
            "round trip: not asked, the provider does not declare add, "
            "remove and enumerate together"
        ),
        G("pushdown: 0 of 2 patterns claimed exact, and are"),
        G("plan: not declared, so a conjunction takes the engine's split"),
    ]

    # And it answers through the seam, which is the point of proving it.
    assert sorted(row.y for row in demo.match(S.edge(S.a, V.y))) == [S.b]
