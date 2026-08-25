"""Purpose: examples/control/if3.metta in Python: an unbound variable IS one.

The companion of if2: there the argument was a symbol and `is-var` answered
False, here it is `$A` and the then arm runs, which is itself an `if`.

Both `if`s are Python conditional expressions and the condition is
`fn.is_var(x)`, so the file compiles whole. `lol` is `S.lol`, the lowercase
symbol reached through the factory, which a compiled body reads as the atom it
builds rather than as a function to call.

`chosen(V.A)` passes a variable as DATA, which is what the example does, and
the answer is 42. A twin runs inside a `stats()` scope and the call answers the
same either way, so nothing here depends on the scope; an earlier note in this
file said the two doors diverged and they no longer do
[re-measured 2026-08-24: `chosen(V.A)` answers `[42]` both inside and outside
`m.stats()`; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 7038 to 7059, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 7059 to 7067, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 7067 to 7034, on the release tree:
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
BUDGET = 7034


def twin(m):
    """Ask whether a variable is a variable, and take the arm that answers."""
    @m.define
    def chosen(x):
        # (if (is-var $x) (if True 42 lol) (+ 2 2))
        return (42 if True else S.lol) if fn.is_var(x) else 2 + 2

    # !(test (if (is-var $A) (if True 42 lol) (+ 2 2)) 42)
    assert chosen(V.A) == [42]
