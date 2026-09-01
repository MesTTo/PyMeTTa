"""examples/ch08-data/08-03-the-shipped-libraries/09-conformance.metta in Python: proving a Prolog provider.

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

#: The provider under test, complete in eight lines. It declares an EXTENSION
#: and exports nothing, which is the shape of a provider-only file:
#: metta_export is for functions and a provider has none.
PROVIDER = Path("./examples/ch08-data/08-03-the-shipped-libraries/_fixtures/demo_provider.pl")


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
    assert sorted(row.y for row in demo[S.edge(S.a, V.y)]) == [S.b]


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
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
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
#: RE-PINNED 2026-08-25, 43185 to 54337, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 54337 to 56881 (+2544), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 56881 to 56628 (-253), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 56628 to 56620 (-8), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 56620 to 56634 (+14), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 56634
