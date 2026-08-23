"""Purpose: examples/types/typing_rules.metta in Python: a user rule in the checker.

`add-typing-rule!` installs a refusal into the same checker every typed call
already consults, so `typing-rule-demo` stops accepting an undeclared argument
and answers the error the rule dictates, naming the rule and its words.
Removing the rule restores exactly the answer from before, which is the claim
worth making twice.

The definition is written as an equation because its body answers `(seen $x)`,
a lowercase head a compiled body would read as a function to call, and the two
rule directives are terms because there is no Python door for them.

The refusal itself is read through `collapse`, because a flat call of a
compiled function at the Python door takes a fast path that never runs the
argument check, so it answers `(seen unknown-demo)` where the engine's own
form answers the Error. That divergence is filed as friction with its
reproduction; every other spelling of the same call, nested, let-bound or
collapsed, agrees with the engine.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Atom, Expression, S, V, arrow, equation, fn, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1

#: The unconstrained type, as the rule's own argument spells it. `Any` is
#: its image where a declaration is being BUILT; here it is being named.
UNDEFINED = S["%Undefined%"]


def twin(m):
    """Accept, then refuse under a user rule, then accept again."""
    demo, payload = S["typing-rule-demo"], S["unknown-demo"]
    rule, words = S["deny-unknown-demo"], S["unknown-demo-is-not-a-payload"]

    m += typed(demo, arrow(S.DemoPayload, Atom))
    m += equation(demo(V.value)).to(S.seen(V.value))
    assert m.fn.typing_rule_demo(payload) == [S.seen(payload)]

    m.eval(fn.add_typing_rule(
        rule, S.ordinary, UNDEFINED, S.DemoPayload, S.refuse(words)
    ))
    refusal = S.BadArgType(1, S.DemoPayload, UNDEFINED,
                           S.TypingRuleRefusal(rule, words))
    refused = m.eval(fn.collapse(demo(payload)))  # rung: collapse is list(), but a FLAT call at the Python door skips the argument check this claim is about
    assert refused == [Expression((S.Error(demo(payload), refusal),))]

    m.eval(fn.remove_typing_rule(rule))
    assert m.fn.typing_rule_demo(payload) == [S.seen(payload)]
