"""examples/ch07-control-flow/07-05-recursion/04-fibsmartimport.metta in Python: importing another file.

`m += lib(PATH)` performs the import: the call door on the lib namespace is
the exact-module-form escape a path import crosses as, the receiver is the
target space, and the imported file's own claim runs as part of the import,
so no `&self` symbol appears here. The path is the ATOM the example writes,
spelled through the same S[...] bracket every unspeakable name takes: the
engine resolves it against its own rules (the importing file, the repo root
for a host program), never against the host's working directory, so a host
path type would promise semantics the door does not apply.

One thing it will not take. A bare module name resolves relative to the
IMPORTING FILE and a Python-authored program has no file, so the path is named
in full; the residue table records that against P14.13.

What the import brings in is then an ordinary callable: `m.fn.fib` is the
imported function, named through the space that now holds it.
"""

from metta import S, lib

#: The imported module, named by the atom the example itself writes.
PATH = S["examples/ch07-control-flow/07-05-recursion/03-fibsmart"]


def twin(m):
    """Import the accumulator fib, then run it."""
    # (import! &self 03-fibsmart): the module is named by its path atom, and
    # the lib door carries the exact form to the engine's own resolution.
    m += lib(PATH)

    # COST, the library's rather than this twin's: naming `fib` through the
    # space resolves a handle against the engine (~1,200 inferences) and the
    # first answer view sets up a held evaluation (~4,700), which is the whole
    # of this twin's 16,564 against the example's 12,672. The spelling is the
    # right one [measured 2026-08-23 on this worktree; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    assert m.fn.fib(100) == [354224848179261915075]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 14526 to 14564, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 14564 to 14565, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 14565 to 14569, on the release tree:
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
#: RE-PINNED 2026-08-26, 14569 to 14538 (-31), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 14538 to 7105 (-7433), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
BUDGET = 7105
