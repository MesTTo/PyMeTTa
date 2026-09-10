"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/04-plntestdirect.metta in Python: PLN deduction, driven by search.

The same deduction formula as plntest.metta beside it, but reached differently:
instead of applying a syllogistic rule to two premises, `sentence` is a
relation that either matches a stored premise or DERIVES one, and asking it for
`(Inheritance a c)` makes the search find the middle term itself.

The definitions duplicate the sibling file's because the examples do; each twin
stands alone, since the lane runs it in its own process.

Four relations are compiled functions. Exact numeric annotations let their
Python operators preserve the source arithmetic heads, while `clamp`
explicitly names the source's `min` and `max` relations. Three are `@m.rules`
bundles, the door for equations whose heads are structures or symbols.
`sentence` is the interesting one: its three clauses coexist, its recursive
body is a conjunction of two sentence goals, and `(= $TV ...)` there is a GOAL
rather than a definition. `equation(lhs).to(rhs)` is the same builder either
way, because `(= lhs rhs)` in an evaluated position is an ordinary atom.

The claim is `solve`, the relational `let`: it evaluates the subject, unifies
its answer with the pattern, and hands back the subject's own variables, which
is how `$TV` leaves the search.
"""

from metta import TRUE, S, V, equation, fn

#: The deduction formula's own head, which carries a genuine underscore no
#: attribute door can spell: rung 4's map would make it `truth-deduction`.
DEDUCTION = S["Truth_Deduction"]


def twin(m):
    """Build the deduction formula, then let the search find the middle term."""

    @m.define
    def clamp(value: float, low: float, high: float) -> float:
        """(= (clamp $v $min $max) (min $max (max $v $min)))."""
        return fn.min(high, fn.max(value, low))

    @m.define
    def smallest_intersection_probability(a_size: float, b_size: float) -> float:
        """(: ... (-> Number Number Number)) and (clamp (/ (- (+ $As $Bs) 1) $As) 0 1)."""
        return clamp(
            fn.truediv(a_size + b_size - 1, a_size),  # preserve the source's bare division head
            0,
            1,
        )

    @m.define
    def largest_intersection_probability(a_size: float, b_size: float) -> float:
        """(: ... (-> Number Number Number)) and (clamp (/ $Bs $As) 0 1)."""
        return clamp(
            fn.truediv(b_size, a_size),  # preserve the source's bare division head
            0,
            1,
        )

    @m.define
    def conditional_probability_consistency(a_size: float, b_size: float, both: float) -> bool:
        """A conditional probability sits between the bounds its marginals allow."""
        # (= (conditional-probability-consistency $As $Bs $ABs)
        #    (and (< 0 $As) (and (<= (smallest ...) $ABs) (<= $ABs (largest ...)))))
        return (
            0 < a_size
            and fn.le(  # the helper call's return type is unknown
                smallest_intersection_probability(a_size, b_size), both
            )
            and fn.le(  # the helper call's return type is unknown
                both, largest_intersection_probability(a_size, b_size)
            )
        )

    @m.define(name="Truth_Deduction")
    def truth_deduction(p, q, r, pq, qr):
        """Strength from the two conditionals, confidence as the weakest link."""
        # (= (Truth_Deduction (stv $Ps $Pc) ... ) (if (and ...) (stv ...) (stv 1 0)))
        match (p, q, r, pq, qr):
            case (
                (S.stv, ps, pc),
                (S.stv, qs, qc),
                (S.stv, rs, rc),
                (S.stv, pqs, pqc),
                (S.stv, qrs, qrc),
            ) if conditional_probability_consistency(
                ps, qs, pqs
            ) and conditional_probability_consistency(qs, rs, qrs):
                # Qs tending to 1 would divide by zero, so that branch answers Rs.
                strength = (
                    rs
                    if fn.lt(0.9999, qs)  # qs is match-bound
                    else fn.add(  # the probabilities are match-bound
                        fn.mul(pqs, qrs),
                        fn.truediv(
                            fn.mul(fn.sub(1, pqs), fn.sub(rs, fn.mul(qs, qrs))), fn.sub(1, qs)
                        ),
                    )
                )
                return S.stv(strength, fn.min(pc, fn.min(qc, fn.min(rc, fn.min(pqc, qrc)))))
            case _:
                # Preconditions unmet.
                return S.stv(1, 0)

    @m.rules
    def strengths():
        """(= (STV a) (stv 0.4 0.9)), and two more with a symbol in the head."""
        for name in (S.a, S.b, S.c):
            yield equation(S.STV(name)).to(S.stv(0.4, 0.9))

    @m.rules
    def sentences(left, middle, right, first, second, truth):  # noqa: PLR0917  -- a bundle's parameters ARE its equations' variables, not a call signature
        """Two stored premises, and one rule that derives a third."""
        # (= (sentence (Inheritance a b) (stv 0.9 0.9)) (once True))
        # (= (sentence (Inheritance b c) (stv 0.9 0.9)) (once True))
        for start, end in ((S.a, S.b), (S.b, S.c)):
            yield equation(S.sentence(S.Inheritance(start, end), S.stv(0.9, 0.9))).to(fn.once(TRUE))
        # (= (sentence (Inheritance $A $C) $TV)
        #    (once (and (and (sentence (Inheritance $A $B) $T1)
        #                    (sentence (Inheritance $B $C) $T2))
        #               (= $TV (Truth_Deduction (STV $A) (STV $B) (STV $C) $T1 $T2)))))
        yield equation(S.sentence(S.Inheritance(left, right), truth)).to(
            fn.once(
                S.sentence(S.Inheritance(left, middle), first)
                & S.sentence(S.Inheritance(middle, right), second)
                & equation(truth).to(
                    DEDUCTION(S.STV(left), S.STV(middle), S.STV(right), first, second)
                )
            )
        )

    # !(test (let $derivation (sentence (Inheritance a c) $TV) $TV)
    #        (stv 0.8166666666666668 0.9))
    derived = m.solve(V.derivation, S.sentence(S.Inheritance(S.a, S.c), V.TV))
    assert derived.TV == S.stv(0.8166666666666668, 0.9)


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 102315 to 102317, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 102317 to 102264, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 102264 to 102196, on the release tree:
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
#: RE-PINNED 2026-08-25, 102196 to 102190, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 102190 to 103927 (+1737), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 103927 to 103899 (-28), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 103899 to 103867 (-32), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 103867 to 102335 (-1532), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 102335 to 42138 (-60197), one corpus pricing pass on
#: the merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 42138 to 42101 (-37), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 42101 to 42383 (+282), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 42383 to 43550 (+1167), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 43550 to 45372 (+1822), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 45372 to 45534 (+162), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 45534 to 45544 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 45544 to 43958 (-1586), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 43958 to 45557 (+1599), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 45557 to 45639 (+82), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 45639 to 44643 (-996), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 44643 to 44675 (+32), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 44643 to 44925 (+282), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 44925 to 44937 (+12), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 44937 to 44916 (-21), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 44675 to 44728 (+53), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 44728 to 44954 (+226), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 44954 to 44964 (+10), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 44916 to 45728 (+812), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 45728 to 45668 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 45668 to 45761 (+93), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 44916 to 44908 (-8), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 44908 to 46785 (+1877), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 46785 to 47535 (+750), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +1774 against the trunk's own pin of 45761 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining -1024 is what
#: landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 47535 to 47595 (+60), a library's Prolog half compiles
#: beside itself on its first import and loads from the artifact after
#: (metta_load_source/2, seam:compiled_source/1): a twin whose example imports
#: a library with a Prolog half pays the artifact load where both sides paid
#: the source consult and its compile-time expansion in every process,
#: lib_thread's import 278,309 to 5,925 inferences; every import now resolves
#: its spec and asks the boot's claim, about 180 inferences an import, and the
#: boot's content moved (the door, the seam and the three library imports the
#: tokens, receipts and seed units gained), which shifts clause layout by tens;
#: measured on this tree with the artifacts warm [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-PINNED 2026-09-09, 47595 to 47605 (+10), engine/qlf_boot.pl gained the
#: hermetic child that writes the engine's own artifact set and every library
#: half's (qlf_child/2, qlf_regenerate_aside/1, qlf_child_boot/0,
#: qlf_shell_words/2), so no process's flags, initialisation file or packs
#: shape an artifact the tree shares; the boot file's added predicates move the
#: first definition's warm-up by ten, the load-structure movement its header
#: records for any boot-content change, and the lane's authoring constant moves
#: with it (warmup 1482); a twin importing a half pays the claim's freshness
#: check besides; measured on this tree with the artifacts warm, against the
#: pins of f26de01fb [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=5f8a823d23fbed5c7395912a89ba32760e2df4b1].
#: RE-PINNED 2026-09-09, 47605 to 47565 (-40), Public add-atom calls
#: metta_add_atom/4 directly and the native bulk loop calls add_sexp_in/5
#: directly, removing one forwarding inference per accepted atom while keeping
#: the atomic token clock, hooks and errors. Open native enumeration uses the
#: shared native_storage_functor/2 mapping, including parametric scalar
#: storage. Receipt scopes retain the nearest unnested transaction and post no
#: cleanup when no reservation exists. Full-lane ten-round observations on the
#: repaired tree place this point below the published budget; the provisioned
#: cut is 3e5855a35d7b206c847845f12467551ea4c54a59. See the 2026-09-09 entries in
#: docs/journal/2026-09-07-every-fact-has-a-token.md. Autoload-only excursions
#: are excluded from this point selection and keep their pins [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 47565

#: DIVERGED 2026-09-07, the example holds 2 atoms the twin does not (2 =) and
#: the twin holds 8 the example does not (1 :, 2 =, 5 @doc): the twin is an
#: ordinary Python program and its body lowers to the engine's own forms: a
#: match statement is ONE equation whose body is a case tower where the example
#: writes one clause per arm, a named intermediate is a let* the original does
#: not have, a Python truth test wraps its condition in py-truthy, and the
#: annotations and docstrings that come with it are stored beside them
#: [measured 2026-09-07: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "0b427152bfa61a3e7a4bbf67cc4c2cd7bfc057d1004bfd680b4b24170e203e62"
