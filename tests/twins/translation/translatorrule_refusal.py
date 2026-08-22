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

from petta import REFLECTION_SPACE, S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4725 to 3693, -1032 (-21.8%), by the twin contract
#: change: three `(test ...)` terms became three Python `assert`s, so the
#: `test` wrapper left the engine three times and the last form's `match`
#: became the subscript door, while both rewrites and the refusal that drives
#: them stayed. Against the example's 12896 the ratio is 0.2864.
#: Prior: 4725, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 3693

#: The words the rule declines with, which are its own.
TOO_STRONG = val("a dose above 1000 is not a milligram strength")


def twin(m):
    """Register a rule that declines above a threshold, then cross it."""
    m += S[":"](S.strength, S["->"](S.Atom, S.Atom, S["%Undefined%"]))

    # (= (strength (dose $n) (unit mg))
    #    (if (> $n 1000) (refuse "...") (noeval (mg $n))))
    m += equation(S.strength(S.dose(V.n), S.unit(S.mg))).to(
        S["if"](S[">"](V.n, 1000), S.refuse(TOO_STRONG), S.noeval(S.mg(V.n)))  # rung: the stored body of an equation whose head selects on structure
    )
    # A refusal is a decline, so a rule with another equation tries that one.
    m += equation(S.strength(S.dose(V.n), S.unit(S.mg))).to(
        S.noeval(S.grams(V.n / 1000))
    )
    m.fn("add-translator-rule!")(S.strength)

    # A match the rule can honour rewrites.
    assert m.one(S.strength(S.dose(250), S.unit(S.mg))) == S.mg(250)
    # A match it declines falls through to the second equation.
    assert m.one(S.strength(S.dose(5000), S.unit(S.mg))) == S.grams(5)

    # And the words are the rule's own, published where a program can ask.
    reflection = m.space(REFLECTION_SPACE)
    assert [
        row.why for row in reflection[S["translator-rule-refusal"](S.strength, V.why)]
    ] == [TOO_STRONG]
