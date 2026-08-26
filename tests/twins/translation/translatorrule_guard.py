"""examples/translation/translatorrule_guard.metta in Python: rules that decline.

A translator rule's head is a PATTERN, so a rule can carry a guard: it names
the shape it rewrites, and a call of another shape is left to ordinary
dispatch rather than bringing the translation down. The example walks that from
both sides, then adds the half a head shape cannot say, which is that a rule's
BODY is its condition too: a clause whose body has no answer declines, and the
next clause is tried.

Five of the six definitions are LAWS with structured heads, and that is what
`@m.rules` is for: a bundle whose parameters ARE the equations' variables,
whose clauses coexist rather than being made exclusive, and which derives no
guard of its own. So `(add-pairs (pair $a $b) (pair $c $d))` is written as the
head it is, and `hold-pairs` and `pick` each carry their two clauses in one
bundle, in the order the rule tries them.

A bundle body EXECUTES rather than lowering, so its arithmetic on the rule
variables BUILDS: `a + c` there is the term `(+ $a $c)`. Its type declaration
is data for the same reason, `typed(head, arrow(...))` rather than an
annotation, because a bundle has no signature to annotate.

The sixth is not a law. `both-ways` has one head and two answers, which is
Python's `yield`, and its point is that the same two equations answer twice
where a rule would take only the first.

What is ordinary throughout is the asking. A rule that declines has no answer,
and that is what an empty answer set looks like from Python: the empty list,
not an error.
"""

from typing import Any

import metta
from metta import Atom, S, arrow, equation, fn, typed
from metta.vocabularies import NoMatchEnum

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 21974 to 0, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, at the P14.32 gate closing the fast path: the
#: rule-path claim moved to the bare written call (the prelude's own
#: double-noeval hand-back idiom; the pre-gate fast path had pinned the
#: equation-path answer), and the corpus reprice had recorded this twin's
#: failed run as 0 [measured 2026-08-25, tools/twin_coverage.py, min-of-2
#: identical at 22742 on the final tree].
#: RE-PINNED 2026-08-25, 22742 to 22682, on the release tree:
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
#: RE-PINNED 2026-08-25, 22682 to 22702, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 22702 to 22933 (+231), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 22933 to 22968 (+35), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 22968 to 22973 (+5), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
BUDGET = 22973
def twin(m):
    """Register five guarded rules, and ask each of them a hit and a miss."""
    metta.reflection += (
        S.dispatch_policy,
        S.add_pairs,
        S.NoMatchEnum,
        S[NoMatchEnum.NoMatchFail],
    )

    # This rule rewrites a pair addition only when both arguments are pairs,
    # which is the shape the rewrite knows how to add.
    m += typed(S.add_pairs, arrow(Atom, Atom, Any))

    @m.rules
    def summing(a, b, c, d):             # (= (add-pairs (pair $a $b) (pair $c $d))
        yield equation(S.add_pairs(S.pair(a, b), S.pair(c, d))).to(
            S.noeval(S.pair(a + c, b + d)))      # (noeval (pair (+ $a $c) (+ $b $d))))

    m.fn.add_translator_rule(S.add_pairs)

    assert m.fn.add_pairs(S.pair(1, 2), S.pair(10, 20)) == [S.pair(11, 22)]

    # A call the rule does not match is not an error: it carries on to ordinary
    # dispatch, so a miss has no answer.
    assert m.fn.add_pairs(1, 2) == []

    # That is what lets a guarded rule live inside a definition at all.
    @m.define
    def holds_a_miss():                  # (= (holds-a-miss) (add-pairs 1 2))
        return fn.add_pairs(1, 2)

    assert holds_a_miss() == []

    # To hand a miss back as DATA instead, write the identity as a second
    # equation. The rule tries them in order, so the guarded one still wins
    # where it fits, and `noeval` stops the expansion going round again.
    m += typed(S.hold_pairs, arrow(Atom, Atom, Any))

    @m.rules
    def holding(a, b, c, d):             # (= (hold-pairs (pair $a $b) (pair $c $d))
        yield equation(S.hold_pairs(S.pair(a, b), S.pair(c, d))).to(
            S.noeval(S.pair(a + c, b + d)))      # (noeval (pair (+ $a $c) (+ $b $d))))
        yield equation(S.hold_pairs(a, b)).to(       # (= (hold-pairs $a $b)
            S.noeval(S.noeval(S.hold_pairs(a, b))))  # (noeval (noeval (hold-pairs $a $b))))

    m.fn.add_translator_rule(S.hold_pairs)

    assert m.fn.hold_pairs(S.pair(1, 2), S.pair(10, 20)) == [S.pair(11, 22)]
    # The original writes this claim as `(test (hold-pairs 1 2) (hold-pairs 1 2))`,
    # and the answer really is the bare written call: a rule's expansion is a
    # FORM, so the double noeval is the prelude's own hand-it-back idiom (the
    # engine's `(noeval (noeval (union $a $b)))`), one layer consumed by the
    # rule's guard and one by the compiled noeval form. The equation WITHOUT
    # the rule keeps one wrapper (the arbiter's Atom-return law); this twin
    # once pinned that equation answer here because the pre-P14.32 fast path
    # skipped the rule's translated route entirely.
    assert m.fn.hold_pairs(1, 2) == [S.hold_pairs(1, 2)]

    # The engine's own stream operations are written that way: `union` rewrites
    # two superpositions and hands anything else back as it was written.
    assert m.fn.union(S.superpose((1, 2)), S.superpose((2, 3))) == [1, 2, 2, 3]
    assert m.fn.union(S.foo, S.bar) == [S.union(S.foo, S.bar)]

    # A RULE'S BODY IS ITS CONDITION: a body with no answer declines, and the
    # next clause is tried, so `(pick a)` is rewritten by the SECOND equation.
    m += typed(S.pick, arrow(Atom, Any))

    @m.rules
    def picking(x):
        yield equation(S.pick(S.a)).to(S.empty())          # (= (pick a) (empty))
        yield equation(S.pick(x)).to(S.noeval(S.picked(x)))  # (= (pick $x) (noeval (picked $x)))

    m.fn.add_translator_rule(S.pick)

    assert m.fn.pick(S.a) == [S.picked(S.a)]
    assert m.fn.pick(S.b) == [S.picked(S.b)]

    # When NO clause applies, the whole rule declines and the call carries on
    # to ordinary dispatch, which here has no answer either.
    m += typed(S.only_a, arrow(Atom, Any))

    @m.rules
    def only_a():
        yield equation(S.only_a(S.a)).to(S.empty())     # (= (only-a a) (empty))

    m.fn.add_translator_rule(S.only_a)

    assert m.fn.only_a(S.a) == []

    # A rule is DETERMINISTIC in a way the function of the same equations is
    # not: written as a plain function, the same two equations answer twice.
    @m.define
    def both_ways(_):                    # (= (both-ways $x) bw-one)
        yield S.bw_one                    # (= (both-ways $x) bw-two)
        yield S.bw_two

    assert both_ways(S.q) == [S.bw_one, S.bw_two]
