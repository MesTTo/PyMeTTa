"""examples/types/typing_rules.metta in Python: a user rule in the checker.

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
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5359 to 2794, -2565 (-47.86%), by the twin-shape
#: rewrite: the three `test` wrappers left the engine for `assert`;
#: installing and removing the typing rule and the three calls are what
#: remains. Against the example's 12703 the ratio is 0.2199 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/typing_rules.metta`]. Prior: RE-PINNED at 5359 by P14.8's
#: m.eval fuel-scope alignment.
BUDGET = 2794


def twin(m):
    """Accept, then refuse under a user rule, then accept again."""
    typed, arrow = S[":"], S["->"]
    demo, payload = S["typing-rule-demo"], S["unknown-demo"]
    rule, words = S["deny-unknown-demo"], S["unknown-demo-is-not-a-payload"]

    m += typed(demo, arrow(S.DemoPayload, S.Atom))
    m += equation(demo(V.value)).to(S.seen(V.value))
    assert m.fn("typing-rule-demo")(payload) == S.seen(payload)

    m.eval(S["add-typing-rule!"](
        rule, S.ordinary, S["%Undefined%"], S.DemoPayload, S.refuse(words)
    ))
    refusal = S.BadArgType(1, S.DemoPayload, S["%Undefined%"],
                           S.TypingRuleRefusal(rule, words))
    refused = m.eval(S.collapse(demo(payload)))  # rung: collapse is list(), but a FLAT call at the Python door skips the argument check this claim is about
    assert refused == [expr(S.Error(demo(payload), refusal))]

    m.eval(S["remove-typing-rule!"](rule))
    assert m.fn("typing-rule-demo")(payload) == S.seen(payload)
