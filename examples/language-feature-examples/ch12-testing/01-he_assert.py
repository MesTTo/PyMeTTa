"""Purpose: examples/ch12-testing/01-he_assert.metta in Python: the assert family itself.

Python's `assert` is what MeTTa's assert family dissolves into, which is why
this one file cannot dissolve it: the twelve functions here ARE the subject, so
each claim is a Python assert ABOUT one of them. That is what the `RUNG`
declaration below records.

Three distinctions the file draws, and they are the reason it exists.
`assertEqual` compares evaluated results, so both sides are built as terms
rather than computed in Python, and each takes the operator's WORD, `S.add` for
`+` and `S.sub` for `-`. The `ToResult` forms take the expected results as a
TUPLE and do not evaluate it, so a single result is written `(3)` and not `3`.
The `Alpha` forms compare modulo variable renaming, and the `Msg` variants add
a failure message and otherwise behave as their bases.

`adder` is an ordinary compiled definition. Its body is a one-element
expression holding a variable the head does not bind, which a body says with
Python's own one-tuple; the engine freshens the name, which is why the claim
about it is an ALPHA one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, V, lib


def twin(m):
    """Ask each member of the assert family whether it holds."""
    m += lib.he

    assert m.fn.assertEqual(S.add(1, 2), S.sub(6, 3)) == [True]

    # Comparing modulo variable renaming carries variables by definition, and
    # the call answers the True this family reports all the same.
    alpha_equal = m.fn.assertAlphaEqual
    assert alpha_equal(S.h(V.x, V.y), S.h(V.a, V.b)) == [True]
    assert alpha_equal(S.quote(V.x + V.y), S.quote(V.a + V.b)) == [True]

    # The ToResult forms take the expected results as a tuple, not a bare
    # value, and do not evaluate it. A single result is therefore (3), not 3.
    to_result = m.fn.assertEqualToResult
    assert to_result(S.add(1, 2), (3,)) == [True]
    assert to_result(S.superpose((1, 2)), (1, 2)) == [True]

    @m.define
    def adder():
        # (= (adder) ($x))
        return (V.x,)

    assert m.fn.assertAlphaEqualToResult(
        S.adder(), (Expression((V.y,)),)
    ) == [True]

    # Every expected result must appear among those produced.
    includes = m.fn.assertIncludes
    assert includes(S.superpose((1, 2, 3)), (2,)) == [True]
    assert includes(S.superpose((1, 2, 3)), (2, 3)) == [True]

    # The Msg variants take a failure message and otherwise behave as their bases.
    assert m.fn.assertEqualMsg(S.add(1, 2), S.sub(6, 3), G("sums differ")) == [True]
    assert m.fn.assertAlphaEqualMsg(
        S.h(V.x, V.y), S.h(V.a, V.b), G("not alpha equal")
    ) == [True]
    assert m.fn.assertEqualToResultMsg(
        S.add(1, 2), (3,), G("not the expected result")
    ) == [True]
    assert m.fn.assertAlphaEqualToResultMsg(
        S.adder(), (Expression((V.y,)),), G("not alpha equal")
    ) == [True]


#: Why this twin sits below the top rung: every claim here is about a member of
#: the assert family, so naming them is the file's subject rather than MeTTa
#: written in Python punctuation.
RUNG = "the assert family is this file's subject, so each claim names one of its twelve members"

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 20919 to 20974, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 20974 to 20985, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 20985 to 20919, on the release tree:
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
#: RE-PINNED 2026-08-25, 20919 to 20929, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 20929 to 19924 (-1005), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 19924 to 19944 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 19944 to 19628 (-316), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 19628 to 19565 (-63), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 19565 to 19653 (+88), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 19653 to 19889 (+236), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 19889 to 19934 (+45), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 19934 to 19951 (+17), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 19951 to 17883 (-2068), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 17883 to 17489 (-394), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 17489 to 17527 (+38), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 17527 to 17513 (-14), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 17513 to 17475 (-38), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 17475 to 17492 (+17), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 17492 to 17529 (+37), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 17529

#: OVERRUN 2026-09-08, 9: the twin names each of the twelve assert-family
#: members through `m.fn` and compares every answer in Python, where the
#: example writes twelve runnables the engine evaluates for itself. Measured
#: 17492 against a ceiling of 17484; a MINIMAL twin of this example -- its own
#: forms stored and asked through the structured door, nothing else -- costs
#: 15175, inside that ceiling, so the distance is this twin's own program and
#: not the band being tighter than the library's floor. What tipped it over is
#: the branch's own boot-content move, +17 on this twin and none on the
#: example, against a ceiling it sat 9 under [measured 2026-09-08: one fresh
#: process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: OVERRUN 2026-09-08, 48: publishing typed host door declarations changes
#: catalog lookup indexes on both sides. The example costs 13424, the twin
#: 17529, and the band's ceiling is 17481.4. The difference rounds up to 48;
#: stored contents remain unchanged [measured: two fresh-process measurements
#: per side agreed; command=python ai-tmp/ai-door-band-cost.py;
#: fixture=run_example and run_twin with the full corpus band;
#: commit=WORKTREE].
OVERRUN = 48
