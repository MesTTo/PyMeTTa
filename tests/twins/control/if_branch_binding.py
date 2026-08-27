"""Purpose: examples/control/if_branch_binding.metta in Python: arms bind alone.

A conditional arm whose value collapses to a clause parameter must not capture
the clause's output at translate time; the other arm still runs its own
unification. The original found this by differential fuzzing of compiled
programs, and every equation in it is exactly what a Python `if` statement
with an assignment in one arm compiles to:

    if a < a:          -->  (if (< $a $a)
        _c = a         -->      (let* (($c $a)) $a)
        return a
    return b           -->      $b)

so three of the four are written that way and read the same in both languages.
The binding is named `_c` rather than `c` because Python calls a bound name
nothing reads a dead store, and it is not one here: it is the `let*` pair the
defect lives in. `case-else` is the same shape through `case`, which is
Python's `match` statement, and it compiles to the case tower with both arms'
bindings intact.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""


def twin(m):
    """Take each arm of four conditionals whose arms bind."""
    @m.define
    def pick_else(a, b):
        # (= (pick-else $a $b) (if (< $a $a) (let* (($c $a)) $a) $b))
        if a < a:  # noqa: PLR0124 -- comparing the parameter with itself is the fixture: the then arm must never run, and the else arm must still unify its own output
            _c = a
            return a
        return b

    # !(test (pick-else 1 2) 2)
    assert pick_else(1, 2) == [2]

    @m.define
    def pick_then(a, b):
        # (= (pick-then $a $b) (if (> $a 0) (let* (($c $a)) $a) $b))
        if a > 0:
            _c = a
            return a
        return b

    # !(test (pick-then 1 2) 1)
    assert pick_then(1, 2) == [1]

    @m.define
    def case_else(a, b):
        # (= (case-else $a $b) (case (< $a $a) ((True (let* (($c $a)) $a)) (False $b))))
        match a < a:  # noqa: PLR0124 -- the same fixture, asked through `case` rather than through `if`
            case True:
                _c = a
                return a
            case False:
                return b

    # !(test (case-else 3 4) 4)
    assert case_else(3, 4) == [4]

    @m.define
    def both(a, b):
        # (= (both $a $b) (if (> $a $b) (let* (($c 1)) $a) (let* (($d 1)) $b)))
        if a > b:
            _c = 1
            return a
        _d = 1
        return b

    # !(test (both 5 2) 5)
    assert both(5, 2) == [5]
    # !(test (both 2 5) 5)
    assert both(2, 5) == [5]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 22007 to 22102, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 22102 to 22113, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 22113 to 22053, on the release tree:
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
#: RE-PINNED 2026-08-25, 22053 to 22063, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 22063 to 22107 (+44), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 22107 to 22129 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 22129
