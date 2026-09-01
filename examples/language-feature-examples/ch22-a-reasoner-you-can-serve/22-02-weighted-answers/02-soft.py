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
from metta import Expression, S, V, lib


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
#: commit=WORKTREE].
#: RE-PINNED 2026-09-02, 161377 to 161577 (+200), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-02, 161577 to 161677 (+100), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 161677
