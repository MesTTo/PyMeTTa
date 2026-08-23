"""Purpose: examples/types/typing_rules.metta in Python: a user rule in the checker.

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
writes it. The refusal itself is read through `collapse`, because a flat call
of a compiled function at the Python door takes a fast path that never runs the
argument check, so it answers `(seen unknown-demo)` where the engine's own form
answers the Error. That divergence is friction against P14.9; every other
spelling of the same call, nested, let-bound or collapsed, agrees with the
engine.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

from metta import Atom, Expression, S, fn

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1

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
    refused = m.eval(fn.collapse(demo))  # rung: collapse is list(), but a FLAT call at the Python door skips the argument check this claim is about
    assert refused == [Expression((S.Error(demo, refusal),))]

    # !(remove-typing-rule! deny-unknown-demo)
    # !(test (typing-rule-demo unknown-demo) (seen unknown-demo))
    m.fn.remove_typing_rule(rule)
    assert typing_rule_demo(payload) == [S.seen(payload)]
