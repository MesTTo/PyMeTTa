"""examples/libraries/library.metta in Python: lib_roman's flat map.

One claim, and both halves of it are MeTTa's own: `map-flat` is the library
function under test and `(+ 1)` is a partial application, which Python spells
with `functools.partial` over host callables and not over an engine function.
So the twin names both and states the answer as an ordinary comparison.

The partial takes the operator's WORD, `S.add(1)`: a fixed table maps every
operator symbol to `operator`'s own name for it, so `S.add` IS `+` and the
bracket stays the exact door for a head literally named `add`.

The import hands its target over as the HANDLE it is. `import!` takes that
space as an ARGUMENT, and a space crosses a term position as a grounded
operand, so no space is named as a symbol here. The library's own name keeps
the bracket: `lib_roman` really has an underscore, and the attribute door maps
every underscore to a hyphen.
"""

from metta import Expression, S, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 24493 to 24531, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 24531 to 24468, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 24468 to 24472, on the release tree:
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
BUDGET = 24472


def twin(m):
    """Import lib_roman, then map (+ 1) over three numbers."""
    m += lib.roman

    # (map-flat (+ 1) (1 2 3))
    assert m.fn.map_flat(S.add(1), (1, 2, 3)) == [Expression((2, 3, 4))]
