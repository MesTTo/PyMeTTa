"""Purpose: translate examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta into Python.

The example defines `(= (f $x) (* $x $x))` and asserts `(f 1)` is 1. Here the
definition is an ordinary Python function the engine compiles, and the claim
is Python's own `assert`.

Guarantees:
  - the translated definition and assertion agree with the source example
    inside the current inference budget [tested:
    test_a_shipped_twin_agrees_with_its_example_end_to_end; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
"""


def twin(m):
    """Define the square, then check it."""
    @m.define
    def f(x):
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
#: acyclic_term left with the LeaTTa occurs law, and let binds raw, the
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
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 2428
