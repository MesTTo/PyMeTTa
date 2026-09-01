"""Purpose: examples/ch09-types/16-typing_rules.metta in Python: a user rule in the checker.

`add-typing-rule!` installs a refusal into the same checker every typed call
already consults, so `typing-rule-demo` stops accepting an undeclared argument
and answers the error the rule dictates, naming the rule and its words.
Removing the rule restores exactly the answer from before, which is the claim
worth making twice.

The definition is an ordinary annotated function: `DemoPayload` is a Python
class so the parameter can name it, `Atom` is the metatype the answer has, and
the body builds `(seen $value)` from the factory, which inside a compiled body
is data rather than a call.

Both directives are performed rather than built, because their engine names end
in `!` and a banged name on the BOUND namespace performs on the line that
writes it. The refusal is read through the flat call itself: a declared head's
flat call runs the same call-site typed dispatch the engine's own form runs
(metta_py_typed_dispatch_applies/2), which retired this file's P14.9 residue
row on 2026-08-25; the collapse spelling it once needed is gone.
Guarantees:
  - the flat call, the eval door, and the engine's own form agree on the
    refusal [tested: test_a_typing_rule_refuses_a_flat_python_call]
"""

from metta import Atom, S

#: The unconstrained type, as the rule's own argument spells it. `Any` is
#: its image where a declaration is being BUILT; here it is being named.
UNDEFINED = S["%Undefined%"]


class DemoPayload:
    """The MeTTa type `DemoPayload`, so a signature can name it."""


def twin(m):
    """Accept, then refuse under a user rule, then accept again."""
    payload = S.unknown_demo
    rule, words = S.deny_unknown_demo, S.unknown_demo_is_not_a_payload

    @m.define
    def typing_rule_demo(value: DemoPayload) -> Atom:
        """(: typing-rule-demo (-> DemoPayload Atom)), answering (seen $value)."""
        return S.seen(value)

    # !(test (typing-rule-demo unknown-demo) (seen unknown-demo))
    assert typing_rule_demo(payload) == [S.seen(payload)]

    # !(add-typing-rule! deny-unknown-demo ordinary %Undefined% DemoPayload
    #                    (refuse unknown-demo-is-not-a-payload))
    m.fn.add_typing_rule(rule, S.ordinary, UNDEFINED, S.DemoPayload, S.refuse(words))

    # !(test (typing-rule-demo unknown-demo)
    #        (Error (typing-rule-demo unknown-demo)
    #               (BadArgType 1 DemoPayload %Undefined%
    #                (TypingRuleRefusal deny-unknown-demo
    #                                   unknown-demo-is-not-a-payload))))
    refusal = S.BadArgType(1, S.DemoPayload, UNDEFINED,
                           S.TypingRuleRefusal(rule, words))
    demo = S.typing_rule_demo(payload)
    assert typing_rule_demo(payload) == [S.Error(demo, refusal)]

    # !(remove-typing-rule! deny-unknown-demo)
    # !(test (typing-rule-demo unknown-demo) (seen unknown-demo))
    m.fn.remove_typing_rule(rule)
    assert typing_rule_demo(payload) == [S.seen(payload)]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 5158 to 6697, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 6697 to 6687, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 6687 to 6658, on the release tree:
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
#: RE-PINNED 2026-08-25, 6658 to 6663, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 6663 to 6850 (+187), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 6850 to 6858 (+8), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 6858 to 6850 (-8), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 6850 to 7362 (+512), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 7362 to 7339 (-23), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 7339
