"""examples/translation/translatorrule_refusal.metta in Python: a rule with reasons.

A rule head says WHICH shape it rewrites. A guard inside the rule says whether
the match it got is one the rewrite can honour, which is a different question
and needs a different answer: `(refuse Reason)`. A refusal is a decline rather
than an error, so the call carries on down the dispatch chain and the next
equation gets its turn, and the words the rule gave are published where a
program can read them.

Both equations select on STRUCTURE, `(dose $n)` and `(unit mg)`, and both must
coexist in the order the rule tries them, which is the pair `@m.rules` exists
for. A bundle body EXECUTES, so its comparison is built by the word door,
`S.gt(n, 1000)`, where a lowered body would write `n > 1000`; the arithmetic
builds either way, so `n / 1000` there is the term `(/ $n 1000)`.

Which is why the last claim is an ordinary query: the reason lands in the
reflection space as a fact, so asking why a rewrite did not happen is
`reflection[pattern]` like any other question.
"""

from typing import Any

import metta
from metta import Atom, S, V, arrow, equation, ground, if_, typed

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
BUDGET = 1

#: The words the rule declines with, which are its own.
TOO_STRONG = ground("a dose above 1000 is not a milligram strength")


def twin(m):
    """Register a rule that declines above a threshold, then cross it."""
    m += typed(S.strength, arrow(Atom, Atom, Any))   # (: strength (-> Atom Atom %Undefined%))

    @m.rules
    def dosing(n):
        # (= (strength (dose $n) (unit mg))
        #    (if (> $n 1000) (refuse "...") (noeval (mg $n))))
        yield equation(S.strength(S.dose(n), S.unit(S.mg))).to(
            if_(S.gt(n, 1000), S.refuse(TOO_STRONG), S.noeval(S.mg(n))))
        # A refusal is a decline, so a rule with another equation tries that one.
        yield equation(S.strength(S.dose(n), S.unit(S.mg))).to(
            S.noeval(S.grams(n / 1000)))       # (= ... (noeval (grams (/ $n 1000))))

    # The directive's MeTTa name ends in `!`, so calling it is the whole of
    # performing it and the statement needs no forcing read.
    m.fn.add_translator_rule(S.strength)

    # A match the rule can honour rewrites.
    assert m.fn.strength(S.dose(250), S.unit(S.mg)).one() == S.mg(250)
    # A match it declines falls through to the second equation.
    assert m.fn.strength(S.dose(5000), S.unit(S.mg)).one() == S.grams(5)

    # And the words are the rule's own, published where a program can ask.
    assert [row.why for row in
            metta.reflection[S["translator-rule-refusal"](S.strength, V.why)]] == [TOO_STRONG]
