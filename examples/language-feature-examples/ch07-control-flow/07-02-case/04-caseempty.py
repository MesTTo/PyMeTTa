"""Purpose: examples/ch07-control-flow/07-02-case/04-caseempty.metta in Python: the `Empty` branch.

`Empty` is the branch a key with NO ANSWERS takes. In `wu` the key is
`(empty)`, so the default fires and the answer is 42; in `wu2` the key answers
42, so the ordinary branch fires and `Empty` is never reached. The pair is the
whole file: `Empty` is about the absence of an answer, not about the value
`()`.

`wu2` is Python's `match` statement, which is what a `case` is, and the
equation it stores is the case tower with the `Empty` arm intact. `wu` cannot
be, and the reason is measurable rather than a missing lowering: the statement
lowers its SUBJECT into a `let*` binding first, and a `let*` over a key with no
answers prunes the whole form, so the compiled `wu` answers nothing where the
example answers 42 [measured 2026-08-24: `match empty(): case 1: ...;
case S.Empty: return 42` stores
`(let* (($k (empty))) (case $k ((1 2) ($_ (case $k ((Empty 42) ...))))))` and
answers `[]`; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. So `wu` is stated as the term it is, and the
gap is filed against P14.4.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, equation


def twin(m):
    """Take the `Empty` branch, then take an ordinary one instead."""
    # The top rung is the `match` statement `wu2` writes below. It answers
    # nothing here, because the lowering binds the subject with a `let*` and a
    # `let*` over a key with no answers prunes the form, which is the one
    # thing `Empty` exists to catch. Residue: P14.4.
    # (= (wu) (case (empty) ((1 2) (Empty 42))))
    m += equation(S.wu()).to(S.case(S.empty(), ((1, 2), (S.Empty, 42))))  # rung: the compiled `match` binds its subject first, and a binding over a key with no answers prunes the whole form

    @m.define
    def f():
        # (= (f) 42)
        return 42

    @m.define
    def wu2():
        # (= (wu2) (case (f) ((42 ok) (Empty nok))))
        match f():
            case 42:
                return S.ok
            case S.Empty:
                return S.nok

    # !(test (wu) 42)
    assert m.eval(S.wu()) == [42]
    # !(test (wu2) ok)
    assert wu2() == [S.ok]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 8263 to 8301, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 8301 to 8314, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 8314 to 8248, on the release tree:
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
#: RE-PINNED 2026-08-25, 8248 to 8258, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 8258 to 8315 (+57), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 8315 to 8335 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 8335 to 5644 (-2691), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 5644 to 5631 (-13), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 5631
