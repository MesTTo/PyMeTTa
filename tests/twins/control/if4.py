"""Purpose: examples/control/if4.metta in Python: an `if` inside a condition.

A condition is an ordinary expression, so an `if` sits there as happily as a
comparison does, and this file's whole subject is that nesting. All three `if`s
are Python conditional expressions and the file compiles whole.

Two lowerings the equation makes visible. Python's `==` is the prelude's
`py-eq`, which is Python's equality rather than MeTTa's `==`; and a test
position that is not already boolean by its syntax wraps in `py-truthy`, so an
`if` used as a condition is asked for its truth the way Python asks. The stored
equation is
`(if (py-truthy (if (py-eq 42 42) True False)) (if True 42 lol) (+ 2 2))`.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 6816 to 7222, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 7222 to 7235, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 7235 to 7167, on the release tree:
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
BUDGET = 7167


def twin(m):
    """Decide a condition with an `if`, then take an arm with another."""
    @m.define
    def nested():
        # (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2))
        return (42 if True else S.lol) if (True if 42 == 42 else False) else 2 + 2  # noqa: PLR0133  -- comparing two constants is the example's own program, which the engine reduces

    # !(test (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2)) 42)
    assert nested() == [42]
