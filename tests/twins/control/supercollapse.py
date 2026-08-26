"""Purpose: examples/control/supercollapse.metta in Python: appending through answer sets.

`TupleConcat` takes two expressions apart into answers and gathers the answers
back into one expression, which is how a program written entirely in answer
sets appends. `range` then builds 1..9 out of nothing but that.

Both operations are named where the subset reads them as MeTTa, and the
equation stored is the original's own. Two rungs are visible on the line.
`collapse` is written rather than `list()`, because the dissolution table says
`list()` is `collapse` and a compiled body refuses `list` outright; and taking
a BOUND expression apart is `fn.superpose(x)`, because the ruled
expression-position spelling `superpose(*x)` refuses with "Starred has no
MeTTa equivalent in the compiled subset" and `superpose(x)` is the other
operation, one alternative that happens to be `$x` [both measured 2026-08-24;
commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. Both are filed against P14.4.

Both heads are named rather than spelled, and each for a measured reason. A
def's own name IS its head, so `name=` is for heads Python cannot spell:
`range` is a BUILTIN a compiled body lowers to `py-range` before it looks for
the definition's own name, so `def range` compiles its own recursion to the
builtin and answers `[1, (2 3 4)]`; and `TupleConcat` is a CapWords FUNCTION
head, which `def TupleConcat` can spell only at the cost of an N-family
suppression this repository's gate has no budget for
[both measured 2026-08-24; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. `()` is the empty tuple, which is
the empty expression, so the base case needs no spelling of its own.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, fn, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 18028 to 18047, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 18047 to 18053, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 18053 to 18020, on the release tree:
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
#: RE-PINNED 2026-08-25, 18020 to 18025, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 18025 to 18156 (+131), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 18156 to 18176 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=WORKTREE].
BUDGET = 18176
def twin(m):
    """Append two expressions, then count to nine with nothing else."""
    @m.define(name="TupleConcat")
    def concat(first, second):
        # (= (TupleConcat $Ev1 $Ev2) (collapse (superpose ((superpose $Ev1) (superpose $Ev2)))))
        return collapse(superpose(fn.superpose(first), fn.superpose(second)))  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)

    @m.define(name="range")
    def count_from(k, n):
        # (= (range $K $N) (if (< $K $N) (TupleConcat ($K) (range (+ $K 1) $N)) ()))
        return concat((k,), count_from(k + 1, n)) if k < n else ()

    # !(test (range 1 10) (1 2 3 4 5 6 7 8 9))
    assert count_from(1, 10) == [Expression((1, 2, 3, 4, 5, 6, 7, 8, 9))]
