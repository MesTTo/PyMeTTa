"""Purpose: examples/ch06-many-answers/07-tests.metta in Python: four programs, one answer set.

`program4` collapses a three-element expression whose middle element answers
three times, so the whole thing answers three times and the collapse gathers
all three. The other three programs are the ways a `let` and a superposition
can be stacked, and each has a Python statement that means it: `let` is
assignment, `superpose` over written-out alternatives is the form itself, and
`superpose` over a BOUND expression is `fn.superpose`, one rung down because
the ruled `superpose(*xs)` refuses inside a body ["Starred has no MeTTa
equivalent in the compiled subset", measured 2026-08-24; commit=028b41a056cfd706e516cd0b945cbf69ac066da7] and
`superpose(xs)` is the other operation.

`collapse` is the one name here Python's own linter cannot see: `superpose`
and `match` are package exports now, `collapse` and `empty` are not, so a
compiled body that gathers carries the suppression the residue entry against
P14.4 would delete. `list()`, the dissolution table's spelling for `collapse`,
does not lower inside a compiled body either, which supercollapse records
against the same row.

The digest difference is deliberate and spans three equations. Assignment
stores one-binding `let*` forms in `program1` and nested `let*` forms in
`program2`. `program3` now stores the source's `==` through `fn.eq`; only its
two identity lets disappear from the twin.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, fn, superpose


def twin(m):
    """Stack lets and superpositions four ways, then collapse the lot."""

    @m.define
    def program1(y):
        # Source: (= (program1 $Y) (let $X $Y (collapse (superpose (12 (+ $X 4))))))
        # Twin:   (= (program1 $Y) (let* (($X $Y)) (collapse (superpose (12 (+ $X 4))))))
        x = y
        return collapse(superpose(12, fn.add(x, 4)))  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa, which the package exports nowhere yet (residue, P14.4)

    @m.define
    def program2(_y):
        # Source: (= (program2 $Y) (let $list (let $L (1 2 3) (collapse (superpose $L))) (superpose $list)))
        # Twin: nested one-binding let* forms for $L and the collapsed list.
        values = (1, 2, 3)
        answers = collapse(fn.superpose(values))  # noqa: F821  -- the same name
        return fn.superpose(answers)

    @m.define
    def program3(x):
        # Source: (= (program3 $x)
        #    (if (== $x 2)
        #        (let $z (superpose ((if (< $x 10) (superpose ((42 43))) 43))) $z)
        #        (let $z 4 $z)))
        # Twin: the same if shape and comparisons; both identity lets are elided.
        if fn.eq(x, 2):
            return superpose(superpose((42, 43)) if fn.lt(x, 10) else 43)
        return 4

    @m.define
    def program4():
        # (= (program4) (collapse ((program1 42) (program2 42) (program3 2))))
        return collapse((program1(42), program2(42), program3(2)))  # noqa: F821  -- the same name

    first = Expression((12, 46))
    last = Expression((42, 43))

    # !(test (program4)
    #        (((12 46) 1 (42 43)) ((12 46) 2 (42 43)) ((12 46) 3 (42 43))))
    rows = tuple(Expression((first, n, last)) for n in (1, 2, 3))
    assert program4() == [Expression(rows)]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 21633 to 21652, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 21652 to 21663, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 21663 to 21595, on the release tree:
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
#: RE-PINNED 2026-08-25, 21595 to 21605, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 21605 to 21903 (+298), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 21903 to 21925 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 21925 to 10279 (-11646), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 10279 to 10260 (-19), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 10260 to 11734 (+1474), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 11734
