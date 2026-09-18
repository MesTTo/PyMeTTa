"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/02-soft.metta in Python: weak unification and attention.

`lib_soft` scores two terms against each other: structure crisp, symbols soft,
minimum aggregation, and a variable binding at degree one. `lib_measure` then
turns the scored candidates into a distribution. Every claim is a call on one
of the two libraries.

The zoo is an ordinary space, and the Python variable IS its binding, so it
needs no name: the handle crosses a term position as itself, which is what
`soft-match` receives where the example writes `&zoo`.

The claim that reads a binding is `solve`, the relational `let`: unify the
score against 1.0 and the subject's own `$who` comes back bound to `cat`,
which is exactly what the example's `(let $probe ... ($probe $who))` says.
"""

import metta
from metta import Expression, S, V, equation, lib


def twin(m):
    """Load soft matching, state two similarities, then check all seventeen claims."""
    # !(import! &self (library lib_measure))
    # !(import! &self (library lib_soft))
    m += lib.measure
    m += lib.soft

    # (similar cat feline 0.8) (similar dog wolf 0.7)
    m += S.similar(S.cat, S.feline, 0.8)
    m += S.similar(S.dog, S.wolf, 0.7)

    sym_sim = m.fn.sym_sim
    soft_score = m.fn.soft_score

    # Symbol closeness: identity is 1.0, declared similarity reads both ways,
    # anything else is 0.0.
    # !(test (sym-sim cat cat) 1.0), and three more
    assert sym_sim(S.cat, S.cat) == [1.0]
    assert sym_sim(S.cat, S.feline) == [0.8]
    assert sym_sim(S.feline, S.cat) == [0.8]
    assert sym_sim(S.cat, S.dog) == [0.0]

    # Weak unification: structure crisp, symbols soft, minimum aggregation.
    # !(test (soft-score (likes cat fish) (likes cat fish)) 1.0), and six more
    assert soft_score(S.likes(S.cat, S.fish), S.likes(S.cat, S.fish)) == [1.0]
    assert soft_score(S.likes(S.feline, S.fish), S.likes(S.cat, S.fish)) == [0.8]
    assert soft_score(S.likes(S.feline, S.wolf), S.likes(S.cat, S.dog)) == [0.7]
    assert soft_score(S.likes(S.cat), S.likes(S.cat, S.fish)) == [0.0]
    assert soft_score(S.likes(S.cat, S.fish), S.hates(S.cat, S.fish)) == [0.0]
    assert soft_score(3, 3) == [1.0]
    assert soft_score(3, 4) == [0.0]

    # A scorer does not RUN the program it is scoring: both operands are
    # Atom, so an equation is compared as written and an evaluable argument
    # stays the term it is. Undeclared, the first call below refused with
    # "* ran backwards with more than one unknown", correct arithmetic met in
    # the wrong place, and the atoms in a space that most deserve scoring are
    # its equations.
    # !(test (soft-score (= (likes cat $f) $body) (= (likes feline fish) tasty)) 0.8)
    assert soft_score(
        equation(S.likes(S.cat, V.f)).to(V.body),
        equation(S.likes(S.feline, S.fish)).to(S.tasty),
    ) == [0.8]
    # !(test (soft-score (likes cat (+ 1 2)) (likes feline (+ 1 2))) 0.8)
    total = S["+"](1, 2)  # rung: the operand is the unevaluated TERM, which is the claim
    assert soft_score(S.likes(S.cat, total), S.likes(S.feline, total)) == [0.8]

    # A variable binds at degree one, and the binding is real.
    # !(test (soft-score $x anything) 1.0)
    assert soft_score(V.x, S.anything) == [1.0]
    # !(test (let $probe (soft-score (likes $who fish) (likes cat fish))
    #             ($probe $who))
    #        (1.0 cat))
    scored = S.soft_score(S.likes(V.who, S.fish), S.likes(S.cat, S.fish))
    assert m.solve(1.0, scored).who == S.cat

    # Soft matching over a space, feeding the measure algebra.
    # !(add-atom &zoo (likes cat fish)), and two more
    zoo = metta.space()
    zoo += S.likes(S.cat, S.fish)
    zoo += S.likes(S.dog, S.bones)
    zoo += S.likes(S.bird, S.seeds)

    soft_match = m.fn.soft_match
    # !(test (collapse (soft-match &zoo (likes feline fish) 0.5))
    #        ((0.8 (likes cat fish))))
    closest = soft_match(zoo, S.likes(S.feline, S.fish), 0.5).one()
    assert tuple(closest) == (0.8, S.likes(S.cat, S.fish))
    # !(test (soft-best &zoo (likes feline fish)) (likes cat fish))
    assert m.fn.soft_best(zoo, S.likes(S.feline, S.fish)) == [S.likes(S.cat, S.fish)]

    # Attention over terms: every candidate scored, softmaxed into a
    # distribution, which sums to one whatever the temperature.
    # `Expression(answers)` is the collapse door: the scored candidates become
    # ONE ordered atom, which is what the measure algebra takes.
    # !(test (size-atom (collapse (soft-match &zoo (likes $x $y) 0.0))) 3)
    assert len(soft_match(zoo, S.likes(V.x, V.y), 0.0)) == 3
    # !(test (< (abs-math (- (ws-total (ws-softmax (collapse (soft-match ...)) 1.0))
    #                        1.0))
    #           1.0e-9)
    #        true)
    candidates = Expression(soft_match(zoo, S.likes(S.feline, V.f), 0.0))
    distribution = m.fn.ws_softmax(candidates, 1.0).one()
    assert abs(m.fn.ws_total(distribution).one() - 1.0) < 1.0e-9

    # How the per-symbol degrees COMBINE is a second choice, separate from
    # what they are. The default is min, the pessimistic reading: one symbol
    # at zero takes the whole term to zero.
    # !(test (soft-score (likes cat fish) (likes dog fish)) 0.0)
    cat_fish, dog_fish = S.likes(S.cat, S.fish), S.likes(S.dog, S.fish)
    assert soft_score(cat_fish, dog_fish) == [0.0]
    # `soft-score-by` asks with one named aggregation without changing the
    # space's own choice: mean over (1.0 0.0 1.0) is two thirds.
    # !(test (< (abs-math (- (soft-score-by mean ...) 0.6666666666666666))
    #           1.0e-9) true), and one more
    by_mean = m.fn.soft_score_by(S.mean, cat_fish, dog_fish).one()
    assert abs(by_mean - 0.6666666666666666) < 1.0e-9
    assert m.fn.soft_score_by(S.mean, cat_fish, cat_fish) == [1.0]

    # The choice is a DECLARATION in the space, Bousi~Prolog's own shape for
    # the same decision, so every scorer in a program reads one atom. This
    # goes last because it changes what soft-score means for everything
    # after it.
    # !(test (soft-aggregation) min), then (soft-aggregate mean)
    assert m.fn.soft_aggregation() == [S.min]
    m += S.soft_aggregate(S.mean)
    # !(test (soft-aggregation) mean)
    assert m.fn.soft_aggregation() == [S.mean]
    # !(test (< (abs-math (- (soft-score (likes cat fish) (likes dog fish))
    #                        0.6666666666666666)) 1.0e-9) true)
    assert abs(soft_score(cat_fish, dog_fish).one() - 0.6666666666666666) < 1.0e-9


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 186644, maximum 186685 over
#: 28 observations under `full-lane/218/workers=32`, so the re-pin owes it an
#: envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 283598 to 283978, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 283978 to 283725, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 283725 to 283765, on the release tree:
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
#: RE-PINNED 2026-08-25, 283765 to 284215, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 284215 to 303059 (+18844): its ~12 rules pay
#: 5c731b03's per-translated-equation specializer bookkeeping, plus
#: 6917bef7's +1,411 measured at that pair
#: (ai-brief-p14-specializer-translation-tax,
#: ai-brief-p14-relational-ops-fastpath) [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 303059 to 302867 (-192), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 302867 to 302803 (-64), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 302803 to 301104 (-1699), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-08-26, 302803 to 302740 (-63): the same count-route change
#: the matespace family carries, worth little here because this twin's one
#: `len(...)` sees three answers. What it still pays is the repeatability
#: walk itself, which is per-length rather than per-answer and is what
#: chooses between the O(1)-memory count for an effect-safe goal and the
#: holding evaluation for an effect-bearing one
#: [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-relational-fastpath off 694c12f7 with engine/reader.so and the MORK artefact; commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2].
#: RE-PINNED 2026-08-26, at the relational-counting merge: 302279.
#: Both parents re-pinned this budget and neither number survives the
#: merge, so it is re-measured here rather than resolved to a side.
#: The two mechanisms above COMPOSE, and the world-admission merge's
#: admission guard lands on top of them: this lineage read 301104,
#: the counting branch read 302740 against its own base, and the
#: merged tree reads 302279
#: [measured: min-of-3 serial fresh processes on the resolved merge
#: tree; command=python extensions/python/tools/twin_coverage.py
#: --measure --rounds 3 ../../examples/<this example>;
#: fixture=engine/reader.so and the MORK artefact present;
#: commit=58d0332489da668251edcd52ccc5cb42ba2e57bb].
#: RE-PINNED 2026-09-01, 302279 to 161088 (-141191), one corpus pricing pass on
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
#: RE-PINNED 2026-09-01, 161088 to 160944 (-144), the subtract-atom primitive
#: and Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 160944 to 161038 (+94), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 161038 to 161377 (+339), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 161377 to 161577 (+200), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 161577 to 161677 (+100), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 161677 to 269347 (+107670), the one pricing pass at
#: the 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 269347 to 294927 (+25580), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-07, 294927 to 304126 (+9199), the twin gained the claims
#: of its example it had been silently short of: this file's own count moves
#: with the asks it now makes [measured 2026-09-07: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 304126 to 304133 (+7), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 304133 to 304035 (-98), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 304035 to 302263 (-1772), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 302263 to 304773 (+2510), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 304773 to 305161 (+388), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 305161 to 305669 (+508), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 305161 to 307629 (+2468), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 307629 to 306833 (-796), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 306833 to 307341 (+508), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 305161 to 305189 (+28), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 305189 to 305278 (+89), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 305278 to 307458 (+2180), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, +117 against the trunk's own pin of 307341 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +2063 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 307458 to 292375 (-15083), a library's Prolog half
#: compiles beside itself on its first import and loads from the artifact after
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
#: RE-PINNED 2026-09-10, 292375 to 292091 (-284), the binding resolves Janus
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
#: RE-PINNED 2026-09-10, 292091 to 292078 (-13), automatic memo reconciliation
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
#: RE-PINNED 2026-09-18, 292078 to 305063 (+12985), the branch's landings since
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
BUDGET = 305063
