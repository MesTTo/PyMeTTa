"""examples/integration/import_relative_nested.metta in Python: one import, two files deep.

`root.metta` imports a sibling and a file in a subdirectory, and both of those
imports resolve against the FILE that wrote them rather than against the
process. Importing `root` alone therefore has to bring in all three, which is
what the two claims check.

The path is written from the repository root because a Python program has no
importing file to resolve against, which is the friction this file carries. The
space is the handle itself, which crosses into the built term as a grounded
operand.
"""

from metta import S, lib

#: The fixture the import reads, from the repository root: the lane runs there.
#: A module name is a NAME, so it is minted at the naming factory, and slashes
#: are what rung 5's bracket is for.
ROOT = S["examples/integration/_fixtures/imports/relative/root"]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 7208 to 7265, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 7265 to 7266, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 7266 to 7272, on the release tree:
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
BUDGET = 7272


def twin(m):
    """Import the root, then ask the two files it reached."""
    # (import! &self examples/integration/_fixtures/imports/relative/root)
    m += lib(ROOT)

    assert m.fn.from_sibling() == [42]   # [42]
    assert m.fn.from_second() == [7]   # [7]
