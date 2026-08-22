"""The Python twin of examples/translation/translatorrule_refusal.metta.

A rule head says WHICH shape it rewrites; a guard inside the rule says whether
the match it got is one the rewrite can honour, and answers `(refuse Reason)`
when it is not. A refusal is a decline rather than an error, so the call
carries on to the next equation, and the words the rule gave are published
into `&petta` where a program can read them.

Both clauses stay at the container door because their head arguments are
PATTERNS, `(dose $n)` and `(unit mg)`. A compiled definition spells a head
pattern as a literal default, `def fib(n=0)`, which reaches a constant in a
position and not a structure around one, so the residue table records the
missing spelling against P14.4.

Inside the stored bodies the operators still build: `V.n > 1000` is
`(> $n 1000)` and `V.n / 1000` is `(/ $n 1000)`, because a Python operator on
a symbolic operand builds the term rather than computing.
"""

from petta import S, V, equation, val

#: The rule's own words, quoted twice: once as the reason it refuses with and
#: once as the answer a program reads back out of &petta.
TOO_STRONG = val("a dose above 1000 is not a milligram strength")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4725 to 4725, +0, by the wave-4 idiom rewrite: every
#: form is the same term built at the same door, so the rewrite is a SPELLING
#: change and the counter says so.
BUDGET = 4725


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    the `add-translator-rule!` form answers the rule it registered.
    """
    # (: strength (-> Atom Atom %Undefined%))
    m += S[":"](S.strength, S["->"](S.Atom, S.Atom, S["%Undefined%"]))

    # (= (strength (dose $n) (unit mg))
    #    (if (> $n 1000)
    #        (refuse "a dose above 1000 is not a milligram strength")
    #        (noeval (mg $n))))
    m += equation(S.strength(S.dose(V.n), S.unit(S.mg))).to(
        S["if"](V.n > 1000, S.refuse(TOO_STRONG), S.noeval(S.mg(V.n)))
    )

    # A refusal is a decline, so a rule with another equation tries that one.
    # (= (strength (dose $n) (unit mg)) (noeval (grams (/ $n 1000))))
    m += equation(S.strength(S.dose(V.n), S.unit(S.mg))).to(
        S.noeval(S.grams(V.n / 1000))
    )

    # !(add-translator-rule! strength)
    yield m.eval(S["add-translator-rule!"](S.strength))

    # A match the rule can honour rewrites.
    # !(test (strength (dose 250) (unit mg)) (mg 250))
    yield m.eval(
        S.test(S.strength(S.dose(250), S.unit(S.mg)), S.mg(250))
    )
    # A match it declines falls through to the second equation.
    # !(test (strength (dose 5000) (unit mg)) (grams 5))
    yield m.eval(
        S.test(S.strength(S.dose(5000), S.unit(S.mg)), S.grams(5))
    )

    # And the words are the rule's own, published into &petta.
    # !(test (match &petta (translator-rule-refusal strength $why) $why)
    #        "a dose above 1000 is not a milligram strength")
    yield m.eval(
        S.test(
            S.match(
                S["&petta"],
                S["translator-rule-refusal"](S.strength, V.why),
                V.why,
            ),
            TOO_STRONG,
        )
    )
