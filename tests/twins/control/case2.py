"""Purpose: examples/control/case2.metta in Python: a branch may fork.

One branch, whose pattern is the key itself so everything reaches it, and
whose VALUE is a superposition: a `case` answers whatever its branch answers,
which is two things here. The `case` therefore decides nothing, and what is
left is the fork.

The fork is `superpose(...)`, the expression-position door, and not two
yields. They are different knowledge: two yields store TWO equations where the
example stores ONE whose body superposes, and `match` sees one atom rather than
two. Both tags are lowercase symbols reached through the `S` factory, which a
compiled body reads as the atom it builds rather than as a function to call.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 3201 to 3220, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3220 to 3231, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3231 to 3165, on the release tree:
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
BUDGET = 3165


def twin(m):
    """One head, one branch, two answers."""
    # The def's own name IS the head, so `name=` is for heads Python cannot
    # spell, and `compile` is one of them HERE: the identifier shadows a
    # builtin, which this repository's gate refuses by budget rather than by
    # taste (the A family's burn-down maximum is 8 and is full), so writing
    # `def compile` would cost a suppression the gate does not have
    # [measured 2026-08-24: `GATE_ONLY=1 sh check.sh` failed with
    # "P0.13 suppression burn-down increased (observed, maximum): {'A': (9, 8)}";
    # commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
    @m.define(name="compile")
    def compiled(_stmt):
        # (= (compile $stmt) (case $stmt (($stmt (superpose (what what2))))))
        return superpose(S.what, S.what2)

    # !(test (collapse (compile wat)) (what what2))
    assert compiled(S.wat) == [S.what, S.what2]
