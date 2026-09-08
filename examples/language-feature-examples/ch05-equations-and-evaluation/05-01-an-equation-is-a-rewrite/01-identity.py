"""Purpose: translate examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta into Python.

The example defines `(= (f $x) (* $x $x))` and asserts `(f 1)` is 1. Here the
definition is an ordinary Python function the engine compiles, and the claim
is Python's own `assert`.

Guarantees:
  - the translated definition and assertion agree with the source example
    inside the current inference budget [tested:
    test_a_shipped_twin_agrees_with_its_example_end_to_end; commit=df1367c75148ca6c7262134a8736b237e1150383]
"""


def twin(m):
    """Define the square, then check it."""

    @m.define
    def f(x: int) -> int:
        return x * x

    assert f(1) == [1]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: RE-PINNED 2026-08-23, 2230 to 2240, at the p14-kernel merge. The move is
#: LAYOUT inside the band the entry below already measured: on the kernel
#: branch, deleting the new metta_host_function_generation/1 service row,
#: deleting its shim wrapper, or moving the service left the reading at 2240
#: unchanged, and on the merged tree three runs read 2240 identically
#: [measured 2026-08-23, min-of-3 through tools/twin_coverage.run_twin].
#: RE-PINNED 2026-08-23, 2208 to 2230, by the indexed equation lookup in
#: engine/filereader.pl. The move is LAYOUT, not work: with
#: translated_equation_of/3 present in that file but never called this twin
#: already costs 2230, and switching one, two or all three of its call sites
#: onto it costs nothing further, all three readings 2230. A single inert
#: fact inserted at the same point moves it the same +20. Inserting n inert
#: facts there measures 2210 at n=0, 2230 at 1 and 2, 2240 at 3 and 5, 2220
#: at 4, 2250 at 6 and 8, and 2210 again at 16, 32 and 400, so this twin's
#: own floor is a 2210..2250 band with no trend in clause count, five times
#: the 4-inference deterministic allowance a point budget carries [measured
#: 2026-08-23, min-of-3 per variant through tools/twin_coverage.run_twin,
#: every variant's three runs identical].
#: Prior: INTERIM PIN 2026-08-23, min-of-3 on the wave-merged tree (2208 against the example's 2626): this file gates the pytest lane, so it is priced ahead of the corpus-wide pass that follows the library fixes, the guide update, and the marked-site sweep, and it is re-priced there with everything else.
#: RE-PINNED 2026-08-23, 2230 to 2221, by the call-side precondition on
#: specialization_plan/5, which stops this twin's call sites reading the callee's
#: equations to find nothing. Inside the 2210..2250 band recorded above, and DOWN,
#: which the point budget refuses in both directions.
#: RE-PINNED 2026-08-23, 2221 to 2258, by keying each support edge on a hash of
#: its endpoints. Eight above the band's top, and the reason is that the keys are
#: inferences the counter SEES while what they buy, a scan of every edge sharing
#: a node functor, is a C-level clause walk it cannot see: this example's graph
#: is far too small to collect any of that, where loading 8,000 definitions fell
#: from 3.25 seconds to 0.73.
#: RE-PINNED 2026-08-24 at the integration merge, both parents' chains kept:
#: this side had read 2240 on the kernel+dispatch+library tree, the branch
#: 2258 with its two entries above; the merged tree's own min-of-3 reading
#: is what the budget below pins [measured 2026-08-24 through
#: tools/twin_coverage.run_twin on the merged tree].
#: RE-PINNED 2026-08-24, 2258 to 2228, by dropping the second walk over an
#: already-translated data head, which is 30 inferences this example no longer
#: spends ON THAT BRANCH's pre-refactor layout.
#: CORRECTED at the integration merge: on the post-refactor merged tree the
#: reading stays 2258 (min-of-3, three identical), so this example's compile
#: path here never paid the removed walk; the walk removal itself is proved
#: by translator.plt's own depth-linearity unit, which passes on this tree.
#: The pin is the merged tree's reading.
#: RE-PINNED 2026-08-24, 2258 to 2208, at the segments merge: DOWN, and layout
#: rather than work. Adding INERT kind/2 declaration rows to engine/ext_points.pl
#: moves this same reading 2208/2218/2218/2240 for 0/1/2/4 rows, reproducing the
#: 2210..2250 band recorded above; the branch's file-by-file bisect shows the new
#: unit alone +20 and two declaration facts -10, and a declaration cannot do work.
#: [measured 2026-08-24, min-of-3 identical on the merged tree; the inert-row
#: evidence is ai-report-p14-segments.md section 3].
#: RE-PINNED 2026-08-24, 2208 to 2221, at the metatype-conformance merge:
#: inside the 2210..2250 band above. The measured decomposition on that
#: branch: an ordinary added equation compiles for +3 (the mask read), an
#: equation whose body compiles to NO goals costs +144 more for its result
#: continuation, and the first m.define in a process pays +42 one-time in two
#: metta_py_add calls of the three-element contract atoms, where the same
#: adds measured directly in Prolog are 15 cheaper on that tree; a single
#: inert clause in any compiled engine file moves the reading +-10
#: [measured 2026-08-24, min-of-3 through tools/twin_coverage.py --measure
#: on the merged tree at 5a2d96f4; decomposition ai-report-p14-metatype.md
#: section 9].
#: RE-PINNED 2026-08-25, 2221 to 2824, at conformance increment 2: the
#: NotReducible application boundary prices every compiled equation call in
#: this twin's define-and-run workload, the same per-call classification the
#: benchmark lanes attribute (op-raw about +1 per operation). The example
#: itself reads 3246 on the same tree, so the twin stays cheaper at ratio
#: 0.87, and the growth class of the workload is unchanged
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta on the conformance-2 tree].
#: RE-PINNED 2026-08-25, 2824 to 2774, at the C reader port: the twin's own
#: source reads go through engine/reader.c now, 50 inferences of shipped-mode
#: parsing off this workload (the example itself moves 3246 to 2590). The
#: budget is a two-sided band, so the drop repins rather than passes
#: [measured 2026-08-25 through tools/twin_coverage.py --measure with
#: engine/reader.so present].
#: RE-PINNED 2026-08-25, 2774 to 2784, at the masked-escape boundary: a
#: non-masking call's compound result tests the b_getval escape flag and
#: answers directly where it ran the reducibility walk, one guard per such
#: boundary in this define-and-run workload. The walk elision that guard
#: buys is the asymptotic half: tilepuzzle's per-iteration whole-queue walk
#: is gone and the example corpus stays 224/224
#: [measured 2026-08-25, the twin reading 2784 stable across the suite run
#: and a direct re-run on the fixed tree].
#: RE-PINNED 2026-08-25, 2784 to 2814, by the computed-head value dispatch:
#: metta_dynamic_head_masks/1 and metta_dynamic_value_call/4 join
#: seam:engine_emitted/1 at the documented three inferences per name per
#: execution-module build, and this workload builds several spaces. The
#: dispatch removes per-activation tail retranslation at computed-head
#: sites (matespacefast 39.3s to 9.4s)
#: [measured 2026-08-25, 2814 stable across the suite run and a direct
#: re-run].
#: RE-PINNED 2026-08-25, 2814 to 2845, at the store wave: deferred
#: translation prices this workload's define-and-first-call shape about
#: +15 per equation at its first reach, the same shape the wave's own
#: branch measured as +20 per equation. Stable across the suite run and a
#: direct re-run.
#: RE-PINNED 2026-08-25, 2845 to 2867, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 2867 to 2878, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 2878 to 2812, on the release tree:
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
#: RE-PINNED 2026-08-25, 2812 to 2822, for the identity-wire numeric
#: ownership seams and concrete Number admission. The native arithmetic
#: clauses remain first and spend the same 246015 inferences in the
#: 2000-addition A/B; this small movement is the compiled QLF layout after
#: adding the seam declarations, provider clauses, and failure-boundary type
#: check [measured 2026-08-25 through tools/twin_coverage.py
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; provisional on the merged tree, the
#: final release measure re-prices].
#: RE-PINNED 2026-08-26, 2822 to 2850, on the memory-and-scale merge. The
#: twin's definition and assertion are unchanged; the fixed 28-inference move
#: is the compiled program-layout cost after adding the named-lifecycle and
#: wide-query bridge clauses. Removing only the hashtable import and then only
#: the hot metta_py_query/4 wide clause left the same 2850 count, ruling out
#: both an import charge and per-query traversal. The pin is the minimum of
#: three fresh processes on the merged tree with engine/reader.so present
#: [measured: 2850 inferences; command=tools/twin_coverage.py --measure
#: --rounds 3 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=merged tree with
#: engine/reader.so; commit=d843bb6d17a525c36afd21cab077d63b34447535].
#: RE-PINNED 2026-08-26, 2822 to 2840: an Answers count now asks the
#: engine-published metta_host_goal_repeatable/2 classifier before choosing
#: whether it may issue a second query. That guard is what keeps effectful
#: relational generators single-pass, and this pure define-and-call twin pays
#: the classification once during its answer comparison [measured: 2840
#: inferences; command=python extensions/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=minimum of three serial
#: runs; commit=6917bef7ca902671999eafcae3a7a86db8f69723].
#: RE-PINNED 2026-08-26, on the integration merge of both parents above:
#: the merged tree measures 2830, BELOW both single-parent pins (2850 and
#: 2840), because the two mechanisms' layout costs compose non-monotonically
#: through clause-indexing shape - the boot-content lesson qlf_boot.pl's
#: header records. Both parent entries stay as the mechanism record; the
#: number is the merged tree's own [measured: 2830 inferences;
#: command=tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=merged tree with
#: engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2822 to 2846, after the algebra carrier host
#: services and catalog rows changed the compiled QLF layout. The ordinary
#: identity workload does no carrier work and its one claim still agrees
#: [measured: 2846 inferences; command=python
#: extensions/python/tools/twin_coverage.py examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: fixture=one full-lane identity twin; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
#: RE-PINNED 2026-08-26, on the under-algebra integration merge: the merged
#: tree measures 2861 (the parents above read 2830 and 2846 alone), the
#: example itself 2801; layout composes non-monotonically through
#: clause-indexing shape and the carrier host services sit in the compiled
#: image even though this workload does no carrier work [measured: 2861
#: inferences; command=tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=merged tree with
#: engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2822 to 2835, for mandatory operation-effect
#: reflection. The first compiled definition publishes its canonical
#: `(effect f pureStructural)` row beside `(defined ...)`; three direct
#: measurements were identical at 2835 while the MeTTa example cost 2817
#: [measured 2026-08-26 through tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta].
#: RE-PINNED 2026-08-26, on the effect-lattice integration merge: 2801,
#: which is also what the example itself costs, so the twin and its source
#: agree exactly on this tree. The four merged mechanisms' layout costs
#: compose non-monotonically through clause-indexing shape, which is why
#: the parents above read 2830, 2846 and 2861 on their own
#: [measured: 2801 inferences; command=tools/twin_coverage.py --measure
#: --rounds 3 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=merged tree with
#: engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2822 to 2880, on the post-commit observation,
#: immutable-world, and State-fence tree. The reading prices the combined
#: engine source and compiled QLF layout; three fresh serial processes each
#: read metta=2817 and twin=2880.
#: [measured: 2880; command=python extensions/python/tools/twin_coverage.py --measure --rounds 1 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=three fresh serial processes under the required MeTTa venv with worktree.sh artifacts; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
#: RE-PINNED 2026-08-26, on the worlds integration merge: 2826 against the
#: example's own 2801. Five landings now compose in this boot image and
#: their layout costs do not add: the single-parent pins above read 2830,
#: 2846, 2861, 2880 and 2801, and the merged tree sits inside that spread
#: rather than at its sum [measured: 2826 inferences;
#: command=tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=merged tree with
#: engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2826 to 2891, after materializing the callable
#: visibility catalog. The identity definition and assertion are unchanged,
#: and the MeTTa example remains 2801; the fixed movement is the engine image
#: and &metta catalog layout, the same non-monotonic layout effect recorded by
#: the preceding merge receipts [measured: 2891 inferences;
#: command=tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=merged exact-spellings tree with
#: engine/reader.so; commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6].
#: RE-PINNED 2026-08-26, 2891 to 2885, after the lexical declaration selector
#: added the governing/reporting split to the compiled engine image. This twin
#: has no inherited declaration and its answer remains 1, so the fixed
#: six-inference drop is layout rather than a change in its work or result
#: [measured: 2885 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=isolated p14-typed-shadowing
#: worktree with engine/reader.so; commit=7b238053d2907cd514e3fd9a29927d43a53c5a3c].
#: RE-PINNED 2026-08-26, 2891 to 2866 on the writable-specialization tree.
#: The source example remains 2801, and the twin stores only f/1 with no
#: specialization equation. The move is compiled engine-image layout from the
#: new specializer clauses, the same non-monotonic QLF layout effect recorded
#: above, rather than work in this identity program [measured: base
#: metta=2801 twin=2891 and candidate metta=2801 twin=2866;
#: command=tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta in each worktree; fixture=separate fresh
#: processes with worktree.sh-linked engine/reader.so on detached base
#: 20e9fc70bb171a2380ef378322817d3b95ed7618 and candidate; commit=5d93a44cf4820717163bbf8dfaf667ae14e5e4ee].
#: RE-PINNED 2026-08-26 on the MERGED tree: the two re-pins above each
#: measured from their OWN parent (2885 lexical selector, 2866 writable
#: minter), and the merged image reads 2875, three stable rounds, the same
#: non-monotonic layout composition both comments describe [measured:
#: metta=2801 twin=2875; command=tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=merged tree with
#: engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2875 to 2825 (-50), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: The parallel async-scheduler branch's own history of this pin,
#: kept for the record; the merged value follows below:
#: engine/reader.so; commit=c52da430787404cdcc8631bec9e913b19de899a4].
#: RE-PINNED 2026-08-26, 2826 to 2801. The identity implementation is
#: unchanged and its twin again costs exactly what the source example costs.
#: The base worktree reads twin=2826 while this tree reads twin=2801, each
#: stable across three fresh processes
#: [measured: 2801 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=6aa5a678 base worktree against
#: p14-audit-async with engine/reader.so; commit=39092863ae34184a9f955f185ff57c1ff177ec40].
#: RE-PINNED 2026-08-26, 2801 to 2806, on the completed async-scheduler
#: tree. The identity implementation and the example remain unchanged, and
#: the example still reads 2801; the five-inference twin move is compiled
#: program layout after the final lifecycle and exact-memo clauses landed.
#: Three fresh serial processes agreed at 2806
#: [measured: 2806 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=p14-audit-async with
#: engine/reader.so; commit=39092863ae34184a9f955f185ff57c1ff177ec40].
#: RE-PINNED 2026-08-26, 2825 to 2845 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 2845 to 2821 (-24), by the arithmetic
#: goal-expansion guard: engine/metta.pl replaces library(arithmetic)'s
#: unguarded system:goal_expansion clause with a catch-wrapped
#: replacement, and the wrapper plus the replaced clause's image move
#: per-goal expansion cost by small deterministic amounts in both
#: directions. NOT clause order: asserta and assertz of the
#: replacement measure identically on this twin and on source-load,
#: which reads +15 over 1,000 forms while this define-and-run workload
#: reads -24; the paired baseline comment is
#: p14_arithmetic_guard_comment on source-load
#: [measured: the twin lane reading 2821 stable across the full suite
#: run and a direct re-run; command=python -m pytest
#: "tests/test_twin_coverage.py::test_a_shipped_twin_agrees_with_its_example_end_to_end[ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta]";
#: fixture=guarded-hook tree with engine/reader.so; commit=87cc9f6c96a11bc06e307d3b2bec861cf0c1430e].
#: RE-PINNED 2026-08-26, 2821 to 2841 (+20), at the world-admission merge:
#: the cache-admission seam now asks the declared effect and refuses names
#: the reviewed native profile fixes stronger, one extra semidet guard per
#: admitted memo call in this define-and-run workload, the same +20 the
#: async-admission entry above documents for its arm. The branch's own tree
#: read the same class against its own base (2888 vs its 2891 pin)
#: [measured: 2841 on the resolved merge tree with engine/reader.so;
#: command=python -m pytest
#: "tests/test_twin_coverage.py::test_a_shipped_twin_agrees_with_its_example_end_to_end[ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta]";
#: commit=16ffc0beff1dff8e6d42cb6c50ff010a22cfa0c0].
#: RE-PINNED 2026-08-27, 2841 to 2846 (+5), at the cursor inference budget.
#: Attributed to ONE LINE and it is a declaration: adding
#: kind(metta_host_inference_budget/3, host_service) to engine/ext_points.pl
#: is the whole move, and applying the branch's other three files on top of it
#: (the service itself in engine/metta/control.pl, the two message clauses in
#: engine/metta/registration.pl, and the five shim call sites) adds nothing
#: further, all four readings 2846. A declaration cannot do work, and the
#: control says so: INERT kind/2 rows for predicates that do not exist move the
#: same reading 2841/2846/2841/2816/2816/2836 for 0/1/2/3/4/8 rows, so one row
#: lands on 2846 exactly as this change does and the band here is 2816..2846,
#: seven times the four-inference allowance a point budget carries. Inert rows
#: in engine/metta/control.pl, where the service actually lives, move it not at
#: all (2841 at 1, 2, 4, 8 and 16). The twin's definition, its assertion and the
#: example's own 2801 are unchanged
#: [measured: base 2841 and candidate 2846, three fresh processes each,
#: all identical; command=python extensions/python/tools/twin_coverage.py
#: --measure --rounds 3 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=this worktree
#: with engine/reader.so, the C extension objects and the MORK backend loaded;
#: commit=6da1b0dacc500fc7691a66722ba58f52ab2df081].
#: RE-PINNED 2026-08-27, 2846 to 2826, on the binding-fixes integration merge
#: of four branches (engine diagnostics, platform capabilities, the cursor
#: inference budget, the codec species tag). The twin's own work is unchanged
#: and its answer is still 1; the movement is the compiled engine image again,
#: and it is DOWNWARD, which is why the two-sided band caught it rather than
#: letting it pass. The cursor-budget parent measured 2846 alone and recorded
#: a control showing this reading tracks the NUMBER of kind/2 declaration rows
#: non-monotonically (2841/2846/2841/2816/2816/2836 for 0/1/2/3/4/8 inert
#: rows); the merged tree adds several such rows and lands on 2826, a value
#: this twin has read on a merged tree before. Three fresh serial processes
#: each read twin=2826 and metta=2800 [measured: 2826 inferences;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta; fixture=the p14-binding-fixes merged tree
#: with engine/reader.so and the MORK backend loaded; commit=0c7b0516438e8b823e429747d66ad1d86754c9ff].
#: RE-PINNED 2026-08-27, 2826 to 2831, by ONE new kind/2 declaration row,
#: kind(metta_host_stack_charge/3, host_service) in engine/ext_points.pl. Same
#: cause as the entry above and the control it cites: this reading tracks the
#: NUMBER of those rows, and boot scans them. It is not the twin's own work.
#: Removing that single row and nothing else puts the reading back on 2826
#: exactly, which is the control [measured 2026-08-27: 2831 with the row,
#: 2826 with the row deleted and the tree otherwise identical, and 2831 again
#: with three inert facts planted beside the new predicate in
#: engine/metta/control.pl, so a clause that is not a scanned row costs
#: nothing; command=python extensions/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: fixture=this worktree with engine/reader.so, the C extension objects and
#: the MORK backend loaded;
#: commit=6c1a6a9ff5420791bd6e7004283949b005ea5c8e]. metta=2800, unchanged.
#: RE-PINNED 2026-08-28, 2831 back to 2826, by the REMOVAL of one kind/2 row.
#: seam:host_builtin/1 and seam:backend_builtin/2 merged into one
#: seam:extension_builtin/2, so engine/ext_points.pl went from 187 declaration
#: rows to 186. Same cause as the two entries above, in the other direction,
#: and the same control confirms it in both: planting ONE inert kind/2 row
#: beside kind(extension_builtin/2, declaration) and changing nothing else puts
#: the reading back on 2831 exactly, and removing it returns 2826. So the
#: measured cost of a scanned declaration row is 5 inferences at boot, read
#: now from both sides. It is not the twin's own work
#: [measured 2026-08-28: 2826 with 186 rows, 2831 with an inert 187th planted;
#: command=python -m pytest "tests/repository/test_twin_coverage.py::test_a_shipped_twin_agrees_with_its_example_end_to_end[ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta]";
#: fixture=this checkout with engine/reader.so and the MORK backend loaded;
#: commit=bdd7de39a6604f9712254fa406d9da798137e452]. metta=2800, unchanged.
#: RE-PINNED 2026-08-28, 2826 to 2836, by THREE names added to
#: engine/spaces.pl's module export list: metta_claim_space/2,
#: metta_disclaim_space/2 and metta_space_claim/2, the space-ownership claim
#: door. Attributed by bisect and by a sweep, both on a tree that already
#: carries the door's ~120 clauses: with the clauses present and NONE of the
#: three exported the reading is 2826, and exporting 1, 2 and 3 of them reads
#: 2831, 2841 and 2836. So the move is the export list, it is about 5
#: inferences a row, and it is NON-MONOTONIC in the row count, which is the
#: same class every entry above records for a scanned declaration row. It is
#: not the twin's work and not the door's clauses: 40 inert facts planted in
#: engine/spaces/foreign.pl on the unmodified base move the reading not at
#: all, this twin never calls the door, and the example itself reads 2800 in
#: every variant. The door's own cost to a space OPERATION is zero, measured
#: separately: 2,000 MORK adds plus a flush, 2,000 MORK matches and a
#: 2,000-atom native write-and-match read 256,979, 531,796 and 78,028
#: inferences identically before and after, five runs each
#: [measured: 2836 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: fixture=this worktree with engine/reader.so and the MORK backend loaded,
#: against a pristine archive of the parent commit with the same artifacts;
#: commit=402d8126d3ce32e9035ce0709822297b012721df]. metta=2800, unchanged.
#: RE-PINNED 2026-08-28, 2836 to 2841, at the extension-doors merge, both
#: parents' chains kept: the doors branch measured 2836 on its own tree (the
#: three engine/spaces.pl exports, its entry above), and the integration side
#: sat within the allowance of 2826 carrying two further kind/2 rows
#: (seam:host_transport_failure/1 and seam:host_error_reason/2, engine-declared
#: at the seam-module fix). The merged tree reads 2841, and the same one-inert-
#: kind-row control that priced every earlier move confirms the mechanism HERE:
#: planting one row beside the new declarations reads 2846, +5 exactly. Row
#: effects compose non-monotonically across the two parents, which is why the
#: merged value is measured rather than summed
#: [measured 2026-08-28: 2841 on the merged tree, 2846 with one inert row
#: planted; command=python -m pytest "tests/repository/test_twin_coverage.py::test_a_shipped_twin_agrees_with_its_example_end_to_end[ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta]";
#: fixture=the p14-integration checkout with engine/reader.so and the MORK
#: backend loaded; commit=1d3c85464994d4c9e5d45cf7e3d6e755a4e456cd]. metta=2800, unchanged.
#: RE-PINNED 2026-08-28, 2826 to 2841, by the platform census extension
#: (regex, compressed-sources, fast-cache). NOT this change's work, and two
#: direct probes say so rather than an argument: a trace on entry to
#: metta_require_platform/2 counts 0 calls over the whole twin process, and
#: the same trace on metta_platform/4 counts 0 census reads, so no line the
#: three new rows added executes anywhere here. What moved is the compiled
#: image, the class every entry above records: planting 1, 2, 4, 8, 16 or 40
#: inert facts in engine/metta.pl moves the BASE from 2826 to 2831 and this
#: tree from 2841 to 2846, flat in count both times; applying the changed
#: files one at a time to the base tree puts the whole move in
#: engine/metta.pl (interop.pl and source_lifecycle.pl each read 2826
#: unchanged); and MOVING the one pcre re-export directive down the base's
#: own file, changing nothing else, reads metta=2788 twin=2808, so the
#: reading tracks where the image puts things rather than what this program
#: does. 2841 is inside the 2816..2846 band the cursor-budget control above
#: measured. The example itself is 2800 on both trees, unchanged
#: [measured 2026-08-28: base twin=2826, candidate twin=2841, both min-of-3
#: fresh serial processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: fixture=this worktree and a clone of 6269f241 beside it, each with
#: engine/reader.so and the MORK backend linked in;
#: commit=6269f2418cd844c45f97f0b21df2f5ab81cdba8b]. metta=2800, unchanged.
#: RE-PINNED 2026-08-28, 2841 to 2821, at the platform-census merge, both
#: parents' chains kept above: each parent independently measured 2841 on its
#: own tree, and the merged tree reads 2821, three identical runs, QLF warmed
#: through run.sh first (a plt-path boot reads a stale set after engine edits;
#: engine/main.pl entries purge). DOWN 20, and layout rather than work: on
#: THIS tree the one-inert-kind-row control moves the reading not at all
#: (2821 with a planted row), where the doors merge measured +5 per row --
#: the banding is non-monotonic in the compiled image, as the 2826..2846
#: entries above already record. metta=2800, unchanged
#: [measured 2026-08-28: 2821 x3; command=python -m pytest "tests/repository/test_twin_coverage.py::test_a_shipped_twin_agrees_with_its_example_end_to_end[ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta]";
#: fixture=the p14-integration checkout with engine/reader.so and the MORK
#: backend loaded; commit=d8463dc901cc14fe134c85da85636f9964f4d160].
#: RE-PINNED 2026-08-28, 2826 to 2831 (+5), at the C writer. LAYOUT, not
#: work: this example neither prints nor writes text, so no swrite/2,
#: sdisplay/2 or metta_unwritable_symbol/2 call runs in it at all, and the
#: whole change to a file it does consult, engine/parser.pl, is +178/-14
#: lines. The control is the tree's own and the one the entry above uses in
#: the other direction: planting inert facts in engine/parser.pl and changing
#: nothing else reads 2826 at 0, 2831 at 1, 2836 at 3, 2821 at 10, 2836 at 30
#: and 2841 at 100, so ONE inert clause reproduces this exact reading and the
#: curve is non-monotonic, which work is not. The reading is also identical
#: with METTA_C_WRITER=off, where the C path answers nothing
#: [measured 2026-08-28: 2826 pristine, 2831 with the change, 2831 with the
#: change and METTA_C_WRITER=off, 2831 pristine with one inert fact planted;
#: command=python -m pytest "tests/repository/test_twin_coverage.py::test_a_shipped_twin_agrees_with_its_example_end_to_end[ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta]";
#: fixture=this worktree with engine/reader.so, engine/writer.so and the MORK
#: backend loaded; commit=a9663314a626d6227ef948658b5de769992c0afa]. metta=2800, unchanged.
#: RE-PINNED 2026-08-29, 2821 to 2831 (+10), a reaction row now installs the
#: engine's write hook itself, from metta_check_catalog_semantics/3 where the
#: head is dispatched on an atom, so the cost is two inferences per (on ...)
#: DECLARATION and nothing per ordinary write. It was the one declaration whose
#: side effect stayed on the host: every binding had to call
#: metta_install_bridges/0 after writing the row, the Python seat does it
#: inside a goal string, and a binding whose Prolog is statically checked could
#: not do it at all. The complexity class is unchanged and now proportional to
#: reactions declared rather than to writes, and 2821 to 2831 is the harness's
#: own five reaction declarations paying it [measured 2026-08-29: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-30, 2831 to 2793 (-38), the engine image, the class every
#: entry above records, moving DOWN for once: the PeTTa-alignment pass removed
#: and added scanned rows and export names across engine/ext_points.pl,
#: engine/translator.pl, engine/translator_rules.pl and engine/filereader.pl,
#: and cut the boot's builtin-source snapshot from a nth_clause scan to a
#: first-clause read. It is not the twin's own work, and the same one-inert-
#: kind-row control that priced every earlier move prices this one: planting
#: kind(ai_probe_inert_row/1, service) beside kind(recompile_function_impl/1,
#: service) and changing nothing else reads twin=2798 metta=2791 against
#: twin=2793 metta=2787, +5 and +4 exactly. The example moved with the twin
#: rather than against it, 2800 to 2787, which is what a boot-image move looks
#: like and what the twin's own work never does [measured 2026-08-30: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-30, 2793 to 2656 (-137), the petta-alignment eliminations
#: reached the twin's own evaluation path: the fuel charge is compiled only
#: under a configured budget, the total-boolean scaffolding is not emitted, and
#: the rule-gate doors hold fast bodies while no cost-ordered translator rule
#: is registered, so the identity calls stopped paying the per-crossing probe
#: of an empty table [measured 2026-08-30: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-30, 2656 to 2662 (+6), boot-image movement from the same
#: day's later engine edits (the qualified boundary emission, the reverted
#: assert guard and the census generalization changed the compiled image), the
#: documented process-predicate-set sensitivity this file's header prices at a
#: few inferences either way [measured 2026-08-30: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-31, 2662 to 2421 (-241, -9.1%), the petta matcher
#: adoption: the match door's entry scan, C classifier and per-candidate
#: acyclic_term left with the earlier occurs law, and let binds raw, the
#: shared constants every counter lane shed that evening [measured
#: 2026-08-31: min-of-3 serial fresh processes; command=pytest
#: test_twin_coverage.py -k 01-identity; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-31, 2421 to 4929 (+2508), the context home's execution
#: module is created by its FIRST write, and this twin's single define is that
#: write. Measured 2026-08-31: one equation costs 385 inferences into &self,
#: 2877 as the first into a minted context home, and 364 as the second or third
#: there, the difference being the import/1 x75, export/1 x63 and
#: import_module/2 x232 that build the home's own execution module once.
#: MeTTa() minting its own home rather than sharing &self is what moved it; the
#: twin pays the whole one-off because it defines exactly once [measured
#: 2026-08-31: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-31, 4929 to 2416 (-2513): the +2508 measured above was
#: real but its cause was a defect, not the design. The abandonment backstop
#: then watched the CONTEXT object, so a chained `MeTTa().self` released the
#: home while its handle was still in use and the next write rebuilt the
#: execution module the note above prices (import/1 x75, export/1 x63,
#: import_module/2 x232). The backstop now watches the home HANDLE, so the
#: module is built once and the twin pays one build, not two
#: [measured 2026-08-31: min-of-3 serial fresh processes; command=pytest
#: test_twin_coverage.py -k 01-identity; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-31, 2416 to 2402 (-14): the occurs-demotion pass is
#: gone, so compiling this twin's one equation no longer rebuilds its body
#: to demote a check nothing emits [measured 2026-08-31: min-of-3 serial
#: fresh processes; command=pytest test_twin_coverage.py -k 01-identity;
#: commit=57f21ba9edf94bcf28cde11f938bce2c241a3709].
#: RE-PINNED 2026-08-31, 2402 to 2411 (+9): the entry above priced this twin
#: at 57f21ba9 and three commits landed after it, one of which (c530ccb8) is
#: the only one to touch engine Prolog. It rewrote engine/translator/runtime.pl
#: to take the mbr artifact path from metta_engine_src_dir/1 rather than
#: prolog_load_context/2, and the translator is what compiling this twin's one
#: equation goes through, so that is the candidate. It is NAMED AS A CANDIDATE
#: rather than a cause: no control was run that removes only that change, and
#: this twin is the whole corpus's smallest, so it is the one whose fixed
#: overhead clears the +-4 allowance while larger twins absorb the same move
#: [measured 2026-08-31: 2411 on six consecutive runs, 0.0000% spread;
#: command=pytest test_twin_coverage.py -k 01-identity; commit=891d413a32b3e6f132998e3613618ff029dfda0d]
#: [assumed 2026-08-31: the attribution to c530ccb8's translator change;
#: commit=891d413a32b3e6f132998e3613618ff029dfda0d].
#: RE-PINNED 2026-08-31, 2411 to 2429 (+18), by the Python shim's fast path
#: going through the engine's own translator:resolve_dispatch instead of a
#: second copy of its else-branch. That is the seam a compiled call site
#: consults, seam:dispatch_call/4, and skipping it meant a memoized function
#: evaluated from Python recomputed where the same call written as a directive
#: hit the memo. +18 is the consultation, paid per direct-goal call, and it
#: buys the seam being reachable from this door at all; every other twin in
#: the corpus absorbed the same move inside its allowance
#: [measured 2026-08-31: 2429 on three consecutive runs, 0.0000% spread;
#: command=pytest test_twin_coverage.py -k 01-identity; commit=4a5325f86c83a301673099e0f6281cae0ec6595c].
#: RE-PINNED 2026-09-01, 2429 to 2435 (+6), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 2435 to 2428 (-7), the subtract-atom primitive and the
#: Counter grain for -=: a new engine head shifts every twin's load structure,
#: and the removal doors changed meaning where a twin spells one [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 2428 to 2466 (+38), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 2466 to 3392 (+926), exact numeric annotations retain
#: pure engine heads and publish MeTTa type declarations [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 3392 to 3561 (+169), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 3561 to 3555 (-6), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 3555 to 3565 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-03, 3565 to 3575 (+10), after translator_rule/3 made the
#: owning execution module part of each global rule row and release retirement
#: added its module-keyed predicates to the loaded engine image. The MeTTa
#: example itself still measures 2800 and both twins answer identically.
#: [measured: 3575 inferences; command=PYTHONPATH=extensions/python
#: $CHECK_PY -m pytest -q
#: tests/repository/test_twin_coverage.py -k 'identity.metta'; fixture=warm
#: main-checkout engine artifacts; commit=d1318d20b5d89d33079c49d0e94aa29e12685664]
#: RE-PINNED 2026-09-03, 3575 to 3564 (-11), by the fast cache reusing a
#: matching live rule in its owning module instead of registering a second one.
#: That gives back most of the +10 the row above paid when translator_rule/3
#: took on the owning execution module. Attributed by A/B in one worktree, same
#: configuration both sides so the delta is the commit rather than the
#: environment: at 76690d84^ the twin passes its 3575 pin, at 76690d84 it reads
#: 3564. Deterministic, three identical samples
#: [measured: 3564 inferences; command=PYTHONPATH=extensions/python
#: $CHECK_PY -m pytest -q
#: tests/repository/test_twin_coverage.py -k 'identity.metta'; fixture=warm
#: worktree engine artifacts provisioned by worktree.sh;
#: commit=76690d84e47dcd890748646015830e4fa38075e0]
#: RE-PINNED 2026-09-04, 3564 back to 3575, because the row above measured a
#: DIFFERENT CONFIGURATION from the one the gate runs in. Its own fixture line
#: says so -- "warm worktree engine artifacts provisioned by worktree.sh" --
#: while the row before it says "warm main-checkout engine artifacts", and the
#: gate runs in the main checkout. The four-cell reading at ONE commit, HEAD,
#: is main checkout 3575 and worktree 3796: the two configurations differ by
#: 221 inferences, and neither is 3564, so the worktree number was not a saving
#: that later regressed but a measurement of something else. A worktree omits
#: gitignored build artifacts, and a feature gated on their presence measures
#: differently there; that is why worktree.sh exists and why a number carried
#: back out of one has to be re-measured in the checkout that will be judged
#: against it
#: [measured: 3575 inferences in the main checkout and 3796 in a worktree of
#: the same commit; command=PYTHONPATH=extensions/python $CHECK_PY -m pytest -q
#: tests/repository/test_twin_coverage.py -k 'identity.metta';
#: fixture=warm main-checkout engine artifacts, and a worktree.sh-provisioned
#: worktree of the same commit; commit=c8900bc70f1bf02ca7cde2fab184aeaa954db9be]
#: RE-PINNED 2026-09-05, 3575 to 3565 (-10), by declaring
#: metta_host_time_budget/3 as a host_service in engine/ext_points.pl. An
#: IMPROVEMENT, which this lane refuses to leave unpinned for the same reason
#: it refuses a regression: an unpinned number stops being a meter.
#: Attributed by A/B in the main checkout, the configuration the gate judges
#: in, with the QLF cleared on both sides so neither read a stale image: with
#: the kind/2 clause the twin reads 3565, and with only that clause removed it
#: passes its 3575 pin. One added fact to a predicate the boot consults is
#: enough to move a first-argument index, which is the shape of a ten-inference
#: move rather than a change in what the example computes; the MeTTa example
#: itself is untouched and both twins still answer identically. Deterministic:
#: three identical samples at loadavg 29.4, 0.0000% spread, which is why an
#: inference pin does not need the measurement lock that a wall-clock one does
#: [measured: 3565 inferences, three identical samples; command=PYTHONPATH=
#: extensions/python $CHECK_PY -m pytest -q
#: tests/repository/test_twin_coverage.py -k 'identity.metta'; fixture=warm
#: main-checkout engine artifacts; commit=6cff6f972723b1b466d35b21b972f901408c471d]
#: RE-PINNED 2026-09-05, 3565 to 3553 (-12), another IMPROVEMENT the lane
#: refuses to leave unpinned. Four of the twelve are attributed by A/B in the
#: main checkout with the QLF cleared on both sides: with
#: engine/metta/control.pl reverted to 7e071e5f^ the twin reads 3557, and with
#: the residual-check reader restored it reads 3553. That commit adds clauses
#: to a boot-consulted file without changing what the example computes, the
#: same first-argument-index shape as the kind/2 move above.
#: The other eight are NOT attributed to a code change, and saying so is the
#: point. Only two commits since the 3565 pin touched engine/ at all
#: (7e071e5f and 4d94a1ac's single line), and removing lib/lib_pln2 entirely
#: leaves the reading at 3553. What DID move is the configuration: the
#: gitignored extensions/mork/mork_ffi/target/release/libmork_ffi.so was
#: rebuilt at 08:09, after the 06:01 pin, and a backend whose artefact is
#: present loads while one whose artefact is absent does not. That is the
#: mechanism this file already documents in the other direction, where the
#: same commit read 3575 in the checkout and 3796 in a worktree.
#: The confirming control -- move the .so aside, re-read, restore -- was NOT
#: run. It changes the engine configuration for every process that boots
#: during the window, and the box was carrying other agents' work at loadavg
#: 11. An unattributed eight recorded as unattributed is honest; a control run
#: under concurrent owners would not be.
#: Deterministic: three identical samples, 0.0000% spread
#: [measured: 3553 inferences, three identical samples, and 3557 with
#: engine/metta/control.pl at 7e071e5f^; command=cd extensions/python &&
#: PYTHONPATH=. $CHECK_PY -m pytest -q tests/repository/test_twin_coverage.py
#: -k 'identity.metta'; fixture=warm main-checkout engine artifacts with
#: libmork_ffi.so present; commit=fc095384e1c6ed4c50d19d0f8aa559344a286e29]
#: RE-PINNED 2026-09-05, 3553 to 3558 (+5), and this one is attributed in
#: full, which the -12 above was not. Routing the arrow reader's CARDINALITY
#: slot through the catalog's (vocabulary determinism ...) row, the way its
#: effect-class slot already went, adds metta_determinism_canonical/2 and three
#: metta_long_determinism/2 facts to engine/spaces/catalog.pl, a file the boot
#: consults. A/B in the main checkout with the QLF cleared on both sides: at
#: HEAD the twin reads 3553 and the lane passes, and with the four changed
#: files restored it reads 3558. Same first-argument-index shape as the two
#: moves above, and the example itself is untouched.
#: Deterministic: three identical samples
#: [measured: 3558 inferences with the change and 3553 at HEAD, three
#: identical samples each; command=cd extensions/python && PYTHONPATH=.
#: $CHECK_PY -m pytest -q tests/repository/test_twin_coverage.py
#: -k 'identity.metta'; fixture=warm main-checkout engine artifacts with
#: libmork_ffi.so present; commit=8fdcfd754d0916544667751e0c959a2f113f96f0]
#: RE-PINNED 2026-09-05, 3558 to 3583 (+25), attributed in full by A/B on the
#: merged tree with the QLF cleared and warmed on both sides: with
#: engine/spaces/catalog.pl at bf39bfd1 the twin reads 3558 and the lane
#: passes, and with the semiring slice restored it reads 3583. Four facts added
#: to a file the boot consults, widening the semiring vocabulary to the ten
#: algebras the catalog defines and publishing budget's ordering claim. The
#: same first-argument-index shape the three moves above record, and the MeTTa
#: example is untouched.
#: Deterministic: three identical samples
#: [measured 2026-09-05: 3583 with the slice and 3558 without, three identical
#: samples each; command=cd extensions/python && PYTHONPATH=. $CHECK_PY -m
#: pytest -q tests/repository/test_twin_coverage.py -k 'identity.metta';
#: fixture=main checkout, libmork_ffi.so present, QLF cleared and warmed;
#: commit=dbd76f0366f5695031b60aff22e3bc6b0b4b1aac]
#: RE-PINNED 2026-09-05, 3558 to 3578 (+20), the callable-type read boundary
#: now projects annotated arrows. Equally provisioned worktrees measure
#: 7eb873e0c758f90f2ff192b7c02df172f16892b2 at 3558 and this change at 3578
#: in the unchanged define-and-call workload.
#: [measured: 3578 inferences, three identical fresh-process samples;
#: command=$PY
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: fixture=warm worktrees with the shipping C artifacts and both MORK shared
#: objects; commit=cba149fe709e7e11b343d7c722ea81b81275a1a5].
#: MERGE RESOLUTION 2026-09-05, 3592. Both parents re-pinned this row from
#: different bases and git could not choose: the semiring slice measured 3583
#: and the annotated-arrow slice 3578, and both narratives are kept above
#: because both are true of the tree they were measured in. Neither is true of
#: the merge. 3592 is measured HERE, three identical samples on the merged
#: tree, which is the rule this repository has for a value derived from two
#: sides: a clean merge of two correct edits can still leave a derived number
#: that neither parent holds
#: [measured 2026-09-05: 3592, three identical samples; command=cd
#: extensions/python && PYTHONPATH=. $CHECK_PY -m pytest -q
#: tests/repository/test_twin_coverage.py -k 'identity.metta'; fixture=merged
#: main checkout, libmork_ffi.so present, QLF cleared and warmed;
#: commit=464ffffb05a0ef09d4e69043d03cfba625966aef]
#: RE-PINNED 2026-09-05, 3583 to 3378 (-205), fixed-width
#: metta_catalog_clause/2 reads now select their storage predicate directly,
#: while open-tail reads retain enumeration with one list check. Source-only
#: A/B against 2458294ae03b8dc1c982a5bc7d31601cc6332dd3 measures 3583 before
#: and 3378 after, three identical fresh processes each with cleared and warmed
#: QLF and matching C/MORK artifacts in the isolated worktree. See
#: docs/journal/2026-09-05-catalog-arity-enumeration.md [measured 2026-09-05:
#: min-of-3 serial fresh processes; command=$CHECK_PY ai-tmp/ai-twin-audit.py;
#: commit=8bd37f3042555ee016a7b917234ce44c75a97c3e].
#: MERGE RESOLUTION 2026-09-05, the second one this row has needed, 3399.
#: Three parents' worth of narrative now sits above and none of their numbers
#: is true of this tree: the earlier merge resolved to 3592, and the catalog
#: arity branch measured 3583 to 3378 against a base that predates it. Measured
#: HERE on the merged tree, three identical samples, metta=2292 twin=3399
#: ratio=1.4830. The rule is the one the note above states and this row keeps
#: proving: a clean merge of two correct edits leaves a derived number that
#: neither parent holds
#: [measured 2026-09-05: 3399, three identical samples; command=$PY
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: fixture=merged main checkout, libmork_ffi.so present, QLF cleared and
#: warmed; commit=e7cc36d2e5d8e38927fa821f8cb3130f55047bfa].
#: RE-PINNED 2026-09-05, 3399 to 3383 (-16). The alias integration changes the
#: remaining open-tail catalog enumeration order. A fixed-order control on both
#: rebased arms measures twin=3450 before and 3449 after; the one-inference
#: saving is the skipped empty declaration prepass. The unmodified source-order
#: arms measure 3399 and 3383, so the other fifteen inferences are catalog
#: layout, not alias expansion. Alias-free readers retain their original work.
#: Both arms use 8f853f992a4c732eca39de34ff0a3dfe161508dd with matching C/MORK
#: artifacts and cleared, warmed QLF; see docs/journal/2026-09-05-structural-
#: type-aliases.md [measured 2026-09-05: min-of-3 serial fresh processes;
#: command=$PY extensions/python/tools/twin_coverage.py --repin --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: commit=acad923476d21110870f235192757281a737ee71].
#: warmed; commit=e7cc36d2e5d8e38927fa821f8cb3130f55047bfa].
#: RE-PINNED 2026-09-05, 3399 to 3394 (-5), the source-observation engine
#: overlay reduces this unchanged define-and-call workload by five inferences.
#: Same-path isolated A/B against 8f853f99 measured twin 3351 before and 3346
#: after, with metta 2280 on both sides; this fully provisioned worktree
#: measures twin 3394 and metta 2292. Compiled successful function clauses and
#: native execution counts are unchanged; the absolute counters depend on the
#: boot artifacts and image layout [measured 2026-09-05: min-of-3 serial fresh
#: processes; command=$VENV/bin/python
#: extensions/python/tools/twin_coverage.py --repin;
#: commit=df1367c75148ca6c7262134a8736b237e1150383].
#: MERGE RESOLUTION 2026-09-05, the third this row has needed, 3398. The alias
#: slice measured 3383 and the observation slice 3394, from different bases, and
#: the merge is neither: measured HERE, three identical samples, metta=2291
#: twin=3398 ratio=1.4832
#: [measured 2026-09-05; command=$PY extensions/python/tools/twin_coverage.py
#: --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: fixture=merged main checkout, libmork_ffi.so present, QLF warmed;
#: commit=9f0bae4845e871dee2b14b3b73a7dc5850c1418e].
#: RE-PINNED 2026-09-05, 3398 to 3412 (+14), The annotated arrow product audits
#: declared cardinality at ordinary call dispatch: compiling and first-calling
#: a function costs a constant +7 beside K installed products for K in 0..50
#: (measured on the branch, zero slope), and this twin defines two functions,
#: so its first evaluation pays +14. The identity twin's fifth merge
#: resolution; the four earlier ones sit above [measured 2026-09-05: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-05, 3412 to 3417 (+5), Union membership's decision
#: predicates live in engine/metta/type_unions.pl and reach the typing registry
#: through its public surface, because this row counts engine code SHAPE: five
#: inert predicates in type_rules.pl move it +5 and ten move it +15, while a
#: new unit resident with no caller leaves it unmoved (measured on the union
#: branch, five arms). The identity twin's sixth merge resolution [measured
#: 2026-09-05: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-05, 3417 to 3382 (-35), the debugger's three seam
#: declarations change kind/2's clause layout: engine/ext_points.pl gains
#: kind(metta_debug_begin/1, host_service), kind(metta_debug_run/3,
#: host_service) and kind(metta_debug_end/0, host_service), which the
#: registration path reads. Same-worktree A/B with QLF cleared and warmed on
#: both arms and three identical samples each: twin 3417 with petta's
#: ext_points.pl, which is that row's own pin exactly, and 3382 with these
#: three rows, metta 2289 on BOTH arms. The MeTTa side not moving is the
#: control that says the WORK is unchanged and only the layout is; no
#: reduction, no clause and no answer differs. The size of this class is base-
#: dependent and non-monotonic: the same three rows moved this row by -5
#: against one base and by -35 against this one [measured 2026-09-05: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=39dd4c9014bf8c38d78df8c8fdc9c114b372dc1f].
#: RE-PINNED 2026-09-05, 3382 to 3387 (+5), The C seat's compiled boot moved
#: qlf_load_engine/0 into engine/qlf_boot.pl and main.pl calls it, which shifts
#: engine clause layout by +5 on this row after the debugger's three kind/2
#: rows moved it -35; metta side unchanged. This row counts code shape and
#: moves with every engine unit change; the seventh resolution tonight
#: [measured 2026-09-05: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-05, 3387 to 3422 (+35), materialization, the Generic Join
#: planner and the folding pass add engine units, and this row counts code
#: shape. The trunk it rebases onto already measures 3404 against this pin in a
#: fully provisioned checkout, so 17 of the move is trunk's and 18 is this
#: branch's. Unlike the two moves above it this one is not layout alone: the
#: MeTTa side moves with it, 2291 to 2357, and a sweep of the branch's own
#: commits accounts for every inference of that +66. +7 is the constant-folding
#: admission probe, +12 the metadata projection index, and +47 what is left of
#: materialization after its three gates, which is +454 where it is introduced,
#: then -241 for preparing once per completed load, -72 for the pragma and -94
#: for charging the source doors only when a program has asked [measured
#: 2026-09-06: min-of-3 serial fresh processes per commit, each in a fully
#: provisioned base worktree with its .qlf set rebuilt first; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch05-
#: equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: commit=3c64e2e24787362a5a5081513bc24b880711a1d7].
#: RE-PINNED 2026-09-06, 3422 to 3432 (+10), the specialization coverage report
#: adds one dynamic marker and five predicates to engine/specializer.pl, and
#: this row counts engine code SHAPE. A positive control settles it: an
#: UNREACHABLE set of the same shape, one dynamic and five static predicates
#: that nothing calls, placed in the same file over trunk's own specializer.pl,
#: reads the identical 3432, while the same set in engine/tracer.pl leaves the
#: row at 3422 and the dynamic marker alone reads 3417. The MeTTa side is 2357
#: on every arm, which is the control saying the work is unchanged; no
#: reduction, clause or answer differs [measured 2026-09-06: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=694dff934a11dbc2ee99267b60f39564053baf87].
#: RE-PINNED 2026-09-06, 3432 to 3437 (+5), five memo cache-admission refusals
#: and the seam:function_clauses_changed/1 handler clause one of them installed
#: leave lib_memo.pl. The MeTTa side is 2357 on every arm, which is the control
#: saying the work is unchanged; no reduction, clause or answer differs. This
#: row counts engine code SHAPE and, as the 2026-09-05 entry above says, that
#: class is base-dependent and NON-MONOTONIC: the identical removal read -5
#: against two earlier tips and +5 against this one, so the sign is a property
#: of the surrounding image and not of the change.
#:
#:   fcfac73f   parent 3432, with the change 3427
#:   754df32f   parent 3432, with the change 3427
#:   84bb5aa9   parent 3437, with the change 3432
#:   db307494   parent 3432, with the change 3437
#:
#: The WARM-UP is part of the protocol and not an incidental. With the .qlf set
#: cleared and rebuilt by a bare
#: `swipl -g "consult('engine/qlf_boot.pl'), consult('engine/metta.pl')"` this
#: row read 3401 on a tree that reads 3427 when the tool's own subprocess
#: rebuilds it, twice over, so an arm warmed one way cannot be compared with an
#: arm warmed the other. `--repin` prices `run_twin` alone while the gate reads
#: the full lane, which is how that spread reached a written pin
#: [measured 2026-09-06: min-of-3 serial fresh processes on each arm, three
#: readings per arm and all nine prices identical, .qlf cleared and rebuilt by a
#: discarded tool round first; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch05-
#: equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: commit=ccad9f6d588270ec2f0810fc56c30e9e59207e7c].
#: RE-PINNED 2026-09-06, 3437 to 3402 (-35), engine SHAPE again, in the two
#: steps a bisect across petta at 9b944a94 and every landed commit finds: the
#: algebra-owner commit reads 3432 and this one 3402. The entry above already
#: records that this row's moves are base-dependent and non-monotonic, and this
#: thread saw the same: the identical pair of commits read 0 and +5 against
#: 754df32f, -5 and -30 against 84bb5aa9 and db307494, and -5 and -30 here. On
#: 754df32f, removing the single kind(metta_current_algebra/3, host_service)
#: row restored the earlier number while removing the predicate it names, the
#: root door or the algebra door each did not, and replacing engine/ with
#: trunk's at the branch tip restored it where replacing
#: extensions/python/metta/ changed nothing. The MeTTa half reads 2357 on every
#: one of those arms, which is the control saying the work is unchanged: no
#: reduction, clause or answer differs [measured 2026-09-06: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=2e627a593413191cda3170f2eb716835f7f62543].
#: RE-PINNED AGAIN 2026-09-06 on the base this branch finally sits on, petta at
#: 7d9b66a1: 3402 to 3407. The row moved with the base and not with the branch,
#: which is the fifth base to show it. Read arm against arm on that base, trunk
#: measures 3402 where it pins 3437, and this branch measures 3407, so what the
#: row prices here is the same engine-shape difference the paragraph above
#: attributes and not new work: the MeTTa half is 2357 on both arms again
#: [measured 2026-09-06: min-of-3 serial fresh processes, both arms on petta at
#: 7d9b66a1; command=python extensions/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch05-equations-and-evaluation/
#: 05-01-an-equation-is-a-rewrite/01-identity.metta; commit=2e627a593413191cda3170f2eb716835f7f62543].
#: RE-PINNED 2026-09-06, 3407 to 3422 (+15), the catalog-owned algebra-law
#: vocabulary. engine/spaces/catalog.pl gains metta_algebra_law_alias/2,
#: metta_algebra_law_expansion/2 and metta_algebra_law_vocabulary/1, and turns
#: two metta_catalog_preset/1 facts into rules; engine/metta/effects.pl gains
#: metta_algebra_declares_law/2, its own metta_algebra_law_expansion/2 and the
#: metta_algebra_accepted_laws//0 message tail. This row counts engine clause
#: layout, which every added engine predicate moves, in either direction. Same-
#: worktree A/B with the .qlf set cleared and rebuilt on both arms and min-of-3
#: serial fresh processes: twin 3407 with petta's two engine files, which is
#: this row's own pin exactly, and 3422 with these two. The MeTTa side reads
#: 2357 on petta's and 2356 on these, inside the 4-inference deterministic
#: allowance, and that control is what says the WORK is unchanged and only the
#: layout moved: no reduction, clause or answer differs. The same two files
#: read +10, +15, -30 and +15 against four earlier bases, so the sign and the
#: size of this class are both base-dependent, as the entries above already
#: record [measured 2026-09-06: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e].
#: RE-PINNED 2026-09-07, 3422 to 3462 (+40), two merges of the same day, each
#: measured on its own merge commit in a worktree provisioned with every .so
#: and its .qlf set rebuilt, the MeTTa side beside it: acd04732 (the assertion
#: bag diff) 3424/2320, 2f4422c9 (the per-space function catalogue) 3422/2320,
#: ab02d526 (the test-hygiene suite) 3422/2320, 80af155d (the refinement
#: vocabulary) 3442/2320, 5621c456 (the cache policies) 3462/2322. So +20 is
#: the refinement guards at the typing sites, which the branch itself measured
#: at 3442 against 3422 + 20 and which sit on this twin's path, and +20 is the
#: cache-policy rows and the reconcile handler lib_tabling installs, which also
#: move the MeTTa side by +2 [measured 2026-09-07: one fresh process per arm,
#: inferences deterministic; command=python extensions/python/tools/twin_coverage.py
#: --measure --rounds 1 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta;
#: commit=a376df6dff8099d6145ace55132c7e30922ea1de].
#: RE-PINNED 2026-09-07, 3462 to 3422 (-40), the engine's clause layout again:
#: this branch adds the refusal taxonomy to engine/metta/registration.pl, one
#: classifier to engine/spaces/lifecycle.pl and five kind rows to
#: engine/ext_points.pl, and the MeTTa side of the same run reads 2320 on both
#: arms, which is the control that says the WORK did not move. The pristine
#: base a0a34ea5, provisioned with every .so and its .qlf set rebuilt, reads
#: twin=3457 metta=2320 against this tree's twin=3422 metta=2320 [measured
#: 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=52e95b50cc5acdc0e41f97b444ab244ad1301433].
#: RE-PINNED 2026-09-07, 3422 to 3498 (+76), the engine's prelude vocabulary
#: became Prolog bodies (perf/prelude-in-prolog, merged e67e2db9), which moves
#: the clause layout every twin's cost prices; the MeTTa side of this same
#: example moved 2320 to 2368 in the same run, so the work did not change, its
#: layout did [measured 2026-09-07: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7dfc9ae929c0f67e9ab3bc3573d6509bfedb2f92].
#: RE-PINNED 2026-09-07, 3498 to 3528 (+30), the refusal-kinds package
#: (feat/refusal-kinds-as-rows, merged 8824b5f1) presets thirteen (refusal ...)
#: rows and four vocabularies into &metta at boot, which its own control priced
#: at +38 inferences on source-load; the MeTTa side of this example is
#: unchanged at 2368, so the twin's extra reads are the rows the catalog now
#: holds, not this example's work [measured 2026-09-07: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=73d95f1aebe460580b123d20f82092ef60f41765].
#: RE-PINNED 2026-09-07, 3528 to 3483 (-45), the AE merge (5a85f560) made the
#: engine's observation dispatch skip an EMPTY committed segment
#: (engine/ext_points.pl, Current == [] -> true), so every write this twin
#: makes while nothing observes it stops paying the reverse and the empty
#: dispatch, 45 inferences over the twin [measured 2026-09-07: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=e84a8263d8181e9dee95b6924a11c10d5c6198b0].
#: RE-PINNED 2026-09-08, 3483 to 3522 (+39), the catalog-types merge (1a3579fa)
#: checks a definition's (arguments name delivery) row against the argument-
#: delivery vocabulary at the write, the one-of kind row that refuses a
#: misspelt delivery word; measured on a fresh space, @m.define of one
#: annotated function costs 2714 inferences on ad762ee7 and 2753 on the merged
#: tree, +39, with the first evaluation, the call and a MeTTa declaration
#: unchanged, which is this twin's one definition [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f31028aa45171c1e8c62767eb31235b84e2399c5].
#: RE-PINNED 2026-09-07, 3483 to 3511 (+28), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 3511 to 3550 (+39), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 3550 to 3529 (-21), metta_substitute_self/3 probes the
#: term for the text &self before walking it, one C write and one C substring
#: probe, where the twins-lane merge's one-equation door (08f6f4df) walked
#: every natively added equation in a named space unconditionally, so every
#: twin that adds or defines an equation in a named space drops by about that
#: equation's size in inferences; the same probe now guards the reader's per-
#: form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 3529 to 3580 (+51), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 3580 to 3542 (-38), the door table landed (feat/space-
#: as-a-projection-of-door-rows merged at 6471faa37, its reconciliation fixes
#: at 58bf75947): every Space door is a generated alias over its body, the
#: catalog publishes the door contracts at boot as typed atoms, and the seam's
#: listeners publish on every registration, so boot content and clause layout
#: moved, which shifts a twin count by tens; measured on the merged tree
#: [measured 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 3542 to 3570 (+28), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
BUDGET = 3570
#: BANDED 2026-09-06 rather than re-pinned an eighteenth time. Seventeen of
#: the eighty-three re-pins above were written on 2026-09-05 and 2026-09-06
#: alone, and every control taken with them left the MeTTa side of the same
#: run unchanged, which is what says the work never moved. What moves is a
#: compile-time term this twin's `@m.define` path carries that tracks the
#: ENGINE's clause layout: appending ONE inert fact to engine/specializer.pl
#: takes the reading from 3422 to 3432, and 2, 4, 8, 16 or 32 more take it no
#: further; the same fact in engine/filereader.pl or
#: engine/translator/analysis.pl costs the same 10 and in
#: engine/metta/effects.pl, engine/spaces/catalog.pl or engine/metta/types.pl
#: costs nothing; the MeTTa side reads 2356 in all twelve arms. Over the
#: sixteen first-parent trunk points from a94f804c to this tip the row read
#: 3397 to 3437 while the MeTTa side moved once, at 26f479ba, from 2291 to
#: 2357, and over the eleven points since then it read 3422 to 3437, a spread
#: of 15, or one and a half of those steps. 20 covers that spread with a step
#: to spare and is 0.58 percent of the pin, so a merge that only relays the
#: engine's predicate set no longer moves this number while an order of
#: magnitude, or the loss of the work, still does. An empirical envelope
#: cannot serve here: it licenses exactly one protocol, and this twin is
#: priced under the serial protocol by tests/repository/test_twin_coverage.py
#: and under the full-lane protocol by the twins lane, so either spelling
#: would be a finding in the other. [measured 2026-09-06: inert facts
#: 0/1/2/4/8/16/32 in engine/specializer.pl read
#: 3422/3432/3432/3432/3432/3432/3432, one fact in each of five other engine
#: files read 3422/3422/3432/3422/3432, metta=2356 in every arm, and the
#: trunk series read
#: 3398/3397/3412/3404/3404/3422/3422/3422/3437/3437/3437/3422/3422/3422/3422/3422;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds
#: 3 examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-
#: rewrite/01-identity.metta; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
ALLOWANCE = 20

#: DIVERGED 2026-09-07, the example holds 0 atoms the twin does not (none) and
#: the twin holds 1 atom the example does not (1 :): a Python annotation IS a (:
#: name (-> ...)) row and a docstring on a compiled function IS an (@doc name
#: ...) row, so the twin's space carries the declarations and the documentation
#: its own file states where the example leaves both unsaid [measured
#: 2026-09-07: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "635ee9220ad2f53fbc5c4c7cd0fc64e01dfb572dbac14df6574fc6a1653cd7e6"
