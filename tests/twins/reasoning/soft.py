"""Purpose: examples/reasoning/soft.metta in Python: weak unification and attention.

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
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
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
#: ai-brief-p14-relational-ops-fastpath) [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 303059 to 302867 (-192), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=WORKTREE].
#: RE-PINNED 2026-08-26, 302867 to 302803 (-64), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=WORKTREE].
BUDGET = 302803
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
