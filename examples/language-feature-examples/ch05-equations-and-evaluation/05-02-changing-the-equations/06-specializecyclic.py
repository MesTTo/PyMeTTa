"""Purpose: spell the cyclic higher-order specialization example in Python.

Two mutually recursive pairs, each carrying the function it was called with.
The pairs are the reason both take the `@m.rules` shape of the definitional
decorator rather than `@m.define`: `f1`'s body calls `f2` and `f2`'s body
calls `f1`, and a compiled body resolves a free name against what the engine
knows AT DECORATION TIME, so whichever is written first cannot name the other.
At the rule door both are ordinary built terms and the cycle closes when the
bundle lands.

Assumes:
  - the four equations and two runnable claims mirror
    examples/ch05-equations-and-evaluation/05-02-changing-the-equations/06-specializecyclic.metta in source order
    [source: examples/ch05-equations-and-evaluation/05-02-changing-the-equations/06-specializecyclic.metta lines 1-15; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Guarantees:
  - twin installs every equation and proves both runnable claims
    [tested: test_a_shipped_twin_agrees_with_its_example_end_to_end; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, equation, if_


def twin(m):
    """Install both cycles and ask each one through the same function value."""

    @m.rules
    def cyclic(f, a, n):
        """The mutually recursive equations, admitted as one rule bundle."""
        # (= (f1 $f $a) (if (< $a 0) ($f nevercalled 42)
        #                   (if (== $a 0) (f2 $f (- $a 1)) finish)))
        #
        yield equation(S.f1(f, a)).to(
            if_(
                S.lt(a, 0),
                Expression((f, S.nevercalled, 42)),
                if_(S.eq(a, 0), S.f2(f, a - 1), S.finish),
            )
        )
        # (= (f2 $f $a) (if (< $a 0) ($f nevercalled 42) (f1 $f $a)))
        yield equation(S.f2(f, a)).to(
            if_(S.lt(a, 0), Expression((f, S.nevercalled, 42)), S.f1(f, a))
        )
        # (= (f3 $f $n) (if (== $n 0) finish (f4 $f $n)))
        yield equation(S.f3(f, n)).to(if_(S.eq(n, 0), S.finish, S.f4(f, n)))
        # (= (f4 $f $n) (f3 $f (- $n 1)))
        yield equation(S.f4(f, n)).to(S.f3(f, n - 1))

    assert m.eval(S.f1(S.add, 2)) == [S.finish]
    assert m.eval(S.f3(S.add, 1)) == [S.finish]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships.
#: Before the wave this file carried an EMPIRICAL envelope rather than a point,
#: minimum 26325, maximum 26409 over 28 observations under
#: `full-lane/218/workers=32`, because its cost moves with the scheduler; the
#: re-pin pass has to give it an envelope again rather than a point
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 81920 to 81962, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 81962 to 81979, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 81979 to 81971, on the release tree:
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
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-PINNED 2026-09-01 on the operator-protocol tree. Ten fresh full-lane
#: observations had no spread, and the serial min-of-three confirmed the point
#: [measured: twin minimum 24966 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-02-changing-the-equations/06-specializecyclic.metta;
#: fixture=operator-protocol tree after python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10; commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 24966 to 25385 (+419), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 25385 to 25417 (+32), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 25417 to 25433 (+16), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 25433 to 26398 (+965), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 26398 to 26882 (+484), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 26882 to 26673 (-209), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 26673 to 24982 (-1691), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 24982 to 25182 (+200), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 25182 to 25857 (+675), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 25182 to 25191 (+9), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 25191 to 25369 (+178), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 25369 to 26043 (+674), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +186 against the trunk's own pin of 25857 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +488 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 26043 to 26037 (-6), the binding resolves Janus
#: maplist/2 at boot, removing its first-failure autoload; one compiled option
#: policy removes repeated evaluation frames, and keyed dispatch removes
#: repeated transport/context selection. Indexed source-macro hooks preserve
#: unrelated compilation costs. Same-cut controls and all before/after rows are
#: in docs/journal/2026-09-09-the-binding-collapse.md. These three fresh serial
#: processes set file_search_cache_time=9223372036854775807 before boot,
#: matching the validated full-lane/277/workers=32/file-cache-
#: time=9223372036854775807 environment. Workloads, point tolerances and
#: empirical envelopes are unchanged [measured 2026-09-10: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
#: RE-PINNED 2026-09-10, 26037 to 26031 (-6), automatic memo reconciliation
#: uses a trailed marker so an inference-limit signal cannot leak its guard.
#: The ordinary dirty drain saves two inferences; the first unset-marker read
#: in each engine invokes SWI's undefined-global hook. Removing the old thread-
#: local predicate also changes catalog-arity enumeration order: five
#: inferences per visited arity in metta_catalog_clause/2 or the partial-list
#: get_native_atom/3 lookup. Same-worktree old/current/restore measurements,
#: native call-site coverage and actual missing-global events separate those
#: costs. See docs/journal/2026-09-09-the-binding-collapse.md. These are three
#: fresh sequential samples per row with 32 concurrent row runners, warmed
#: library artifacts, and file_search_cache_time=9223372036854775807 before
#: boot. Every workload, point allowance and empirical envelope is unchanged
#: [measured 2026-09-10: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
#: RE-PINNED 2026-09-11, 26031 to 26046 (+15), end-of-wave re-pin on the merged
#: tree after FROM's reference rows and four engine units, the closed-set
#: derivations and two host services, BINDING's one native evaluation entry and
#: boot import, W-OBSERVE's observer guard, PERF's receipts batching and cursor
#: retirement, and the three REDS repairs (derived runtime resources and the
#: shared loader, the tool-lane repairs, the corpus example); serial minimum of
#: three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 26031 to 27317 (+1286), the branch's landings since
#: the 09-10 pins, re-taken on the tip f06186a96: the compiled call law
#: (e59104ace: an Atom argument enters as written, a Python object crosses as a
#: value, a positional call of a bound callee is the plain application and a
#: compiled lambda is bare where it is applied), the one codec at the grounded
#: call (fd0af38f7, whose read of a call site's written keyword tail costs
#: about six inferences per translated site, read once since 7cc8fb863), the
#: runnable cache's dependency index written by the producer (a9e2c06d3, which
#: takes back the walk of the generated code 5416e741d charged at every miss),
#: the host patches of 09-17 and the class units of 09-13 to 09-16 the ladder
#: in docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 27317 to 26614 (-703), the trunk merged (f97c4b0a3,
#: petta's 61 commits since c75181adc) with the definition batch's load pushed
#: as the running load (2da1155e3): every example moved with the engine, 279 of
#: 294 cheaper (median -0.78%), through the compiled runnable envelope
#: executing each runnable form's fixed answer, name and fuel envelope from
#: compiled clauses, the trunk's trailed scopes and compiled context readers (a
#: b_getval/2 read per recorded assertion in place of the branch's thread-local
#: rows), the host listener door and the receipts loop probing the owner once
#: per set; serial minimum of three fresh processes through the lane's run_twin
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=55d451b670949c2dc9d2ab7bc678f33f21094bd2].
BUDGET = 26614

#: OVERRUN 2026-09-07, 2400: the mutually recursive pair takes the `@m.rules`
#: door, which stages two equations where the example writes two. Measured
#: 26882 against a ceiling of 24519; a MINIMAL twin of this example -- its own
#: forms stored and asked through the structured door, nothing else -- costs
#: 26857 against the ceiling's 24519, so no twin of it fits the band at all
#: [measured 2026-09-07: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-09, 2400 to 2806 (+406): the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): a Python decode with one named variable
#: builds no index and one with more builds it at the second distinct name,
#: which moves a twin's engine-side cost while its example, which decodes
#: nothing, holds; boot content and clause layout moved the rest; against the
#: trunk's own run at da0e5755d the twin moved +186 and the example +8, and
#: the twin sat 228 over its ceiling there already. Measured 26043 against a
#: ceiling of 25638; a minimal twin costs 26018 against the band's 23238,
#: above that ceiling, so no twin of it fits the band at all, as before
#: [measured 2026-09-09: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PRICED 2026-09-11, 2806 to 3916 (+1110): the band stopped granting the
#: first-definition premium (DEFINITION_WARMUP 1482 to 303, DEFINITION_COST
#: 1364 to 1362, re-derived 2026-09-11 from the authoring probe's one-line
#: fixture, which no longer pays it after the binding's boot import), and this
#: twin still pays 1110 of it: the first use of the lowering paths its 1
#: definition take, which the fixture's `return x + 1` does not exercise.
#: Measured 26046 against a ceiling of 24936 (18605 times 1.1 plus 303 once
#: plus 1 times 1362 plus the declared 2806) [measured 2026-09-11: sh check.sh
#: twins on the merged tree after the twin re-pin; command=python
#: extensions/python/tools/twin_coverage.py; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: OVERRUN 2026-09-18, 2806 to 3373 (+567): the twin costs 27317 against the
#: example's 19180 and a ceiling of 26750 with the earlier declaration; a
#: minimal twin of this example costs 26794, above the 21098 the band alone
#: allows, so the distance is the library's own floor for this shape, debt the
#: tracker carries rather than this twin's program. The landings the point re-
#: pin names moved this twin and its example apart: the compiled call law and
#: the one codec at the grounded call charge the twin's Python-side crossings,
#: which the example never pays, and the runnable cache's dependency index
#: written by the producer took most of that back on the branch tip f06186a96
#: [measured 2026-09-18: one fresh process per side through the lane's
#: run_example and run_twin, the floor from a minimal twin built by the probe;
#: command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
OVERRUN = OVERRUN = 3373
