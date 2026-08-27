"""Purpose: examples/reasoning/logicprog.metta in Python: a recursive relation over facts.

Six successor facts and a transitive closure over them, asked backwards: which
letters come before `d`. The two dispatch policies go into the reflection space
through the ordinary write door, `space += atom`, because that is what
`add-atom` is; `metta.reflection` IS that space, so the `&metta` symbol is
never written.

Both relations are `@m.rules` bundles, the door for equations that COEXIST.
That matters twice here. `later-in-alphabet`'s two clauses are ALTERNATIVES,
and stacked `@m.define` clauses would read as first-match, which makes the
recursive one unreachable; and the second clause's `$Z` appears in neither
head, where a bundle mints a fresh variable for every parameter it declares.
`&` is the conjunction, rung 3 of the descent ladder, because Python's own
`and` cannot be overloaded and a rules body EXECUTES rather than lowering.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

import metta
from metta import TRUE, Expression, S, V, equation
from metta.vocabularies import NoMatchEnum

#: Six letters, each with the one before it.
SUCCESSORS = ((S.b, S.a), (S.c, S.b), (S.d, S.c), (S.e, S.d), (S.f, S.e), (S.g, S.f))


def twin(m):
    """State six facts, close them transitively, and search backwards."""
    # Reaching either relation's unmatched boundary must FAIL the search rather
    # than answering the P3 residual-call dispatch value.
    # !(add-atom &metta (dispatch-policy successor NoMatchEnum NoMatchFail))
    # !(add-atom &metta (dispatch-policy later-in-alphabet NoMatchEnum NoMatchFail))
    reflection = metta.reflection
    reflection += S.dispatch_policy(
        S.successor, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail]
    )
    reflection += S.dispatch_policy(
        S.later_in_alphabet, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail]
    )

    @m.rules
    def alphabet():
        """(= (successor b a) True), and five more of the same shape."""
        for after, before in SUCCESSORS:
            yield equation(S.successor(after, before)).to(TRUE)

    @m.rules
    def closure(after, before, middle):
        """The transitive closure, as the two coexisting clauses it is."""
        # (= (later-in-alphabet $X $Y) (successor $X $Y))
        yield equation(S.later_in_alphabet(after, before)).to(
            S.successor(after, before)
        )
        # (= (later-in-alphabet $X $Y)
        #    (and (successor $X $Z) (later-in-alphabet $Z $Y)))
        yield equation(S.later_in_alphabet(after, before)).to(
            S.successor(after, middle) & S.later_in_alphabet(middle, before)
        )

    # Asking with the second argument open enumerates every letter before d,
    # nearest first, each paired with the True its clause answered.
    # !(test (collapse ((later-in-alphabet d $1) $1)) ((True c) (True b) (True a)))
    assert m.eval((S.later_in_alphabet(S.d, V.earlier), V.earlier)) == [
        Expression((TRUE, S.c)), Expression((TRUE, S.b)), Expression((TRUE, S.a)),
    ]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 17594 to 17545, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 17545 to 17517, on the release tree:
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
#: RE-PINNED 2026-08-25, 17517 to 17513, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 17513 to 17474 (-39), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 17474 to 17457 (-17), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 17457 to 17446 (-11), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
BUDGET = 17446
