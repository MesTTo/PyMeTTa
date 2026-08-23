"""examples/translation/translatorrule_refusal.metta in Python: a rule with reasons.

A rule head says WHICH shape it rewrites. A guard inside the rule says whether
the match it got is one the rewrite can honour, which is a different question
and needs a different answer: `(refuse Reason)`. A refusal is a decline rather
than an error, so the call carries on down the dispatch chain and the next
equation gets its turn, and the words the rule gave are published where a
program can read them.

Which is why the last claim is an ordinary query: the reason lands in the
reflection space as a fact, so asking why a rewrite did not happen is
`reflection[pattern]` like any other question.

Both equations are terms: their heads select on STRUCTURE, `(dose $n)` and
`(unit mg)`, where a compiled head pattern is a literal default (residue,
P14.4).
"""

import petta
from petta import S, V, equation, ground

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1

#: The words the rule declines with, which are its own.
TOO_STRONG = ground("a dose above 1000 is not a milligram strength")


def twin(m):
    """Register a rule that declines above a threshold, then cross it."""
    m += S[":"](S.strength, S["->"](S.Atom, S.Atom, S["%Undefined%"]))

    # (= (strength (dose $n) (unit mg))
    #    (if (> $n 1000) (refuse "...") (noeval (mg $n))))
    m += equation(S.strength(S.dose(V.n), S.unit(S.mg))).to(
        S["if"](V.n > 1000, S.refuse(TOO_STRONG), S.noeval(S.mg(V.n)))  # rung: this `if` is the stored BODY of an equation, so it is data rather than control flow
    )
    # A refusal is a decline, so a rule with another equation tries that one.
    m += equation(S.strength(S.dose(V.n), S.unit(S.mg))).to(
        S.noeval(S.grams(V.n / 1000))
    )
    # Known issue: a call through the function namespace answers a LAZY view,
    # so the perfect statement-level spelling of a directive,
    # `m.fn.add_translator_rule(head)`, REGISTERS NOTHING until something pulls
    # its answers [measured 2026-08-23: the rule fires only after list() of the
    # view]. The term door evaluates eagerly, so a directive is written that
    # way until a side-effecting call runs at statement level.
    m.eval(S["add-translator-rule!"](S.strength))

    # A match the rule can honour rewrites.
    assert m.fn.strength(S.dose(250), S.unit(S.mg)).one() == S.mg(250)
    # A match it declines falls through to the second equation.
    assert m.fn.strength(S.dose(5000), S.unit(S.mg)).one() == S.grams(5)

    # And the words are the rule's own, published where a program can ask.
    reflection = petta.reflection
    assert [
        row.why for row in reflection[S["translator-rule-refusal"](S.strength, V.why)]
    ] == [TOO_STRONG]
