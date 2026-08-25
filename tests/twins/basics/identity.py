"""examples/basics/identity.metta in Python: square a number, check the answer.

The example defines `(= (f $x) (* $x $x))` and asserts `(f 1)` is 1. Here the
definition is an ordinary Python function the engine compiles, and the claim
is Python's own `assert`.
"""

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
#: petta_py_add calls of the three-element contract atoms, where the same
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
#: examples/basics/identity.metta on the conformance-2 tree].
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
#: petta_dynamic_head_masks/1 and petta_dynamic_value_call/4 join
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
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
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
#: examples/basics/identity.metta; provisional on the merged tree, the
#: final release measure re-prices].
BUDGET = 2822


def twin(m):
    """Define the square, then check it."""
    @m.define
    def f(x):
        return x * x

    assert f(1) == [1]
