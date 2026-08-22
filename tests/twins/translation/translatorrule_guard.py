"""examples/translation/translatorrule_guard.metta in Python: rules that decline.

A translator rule's head is a PATTERN, so a rule can carry a guard: it names
the shape it rewrites, and a call of another shape falls through to ordinary
dispatch rather than bringing the translation down. The example walks that from
both sides, then adds the half a head shape cannot say, which is that a rule's
BODY is its condition too: a clause whose body has no answer declines, and the
next clause is tried.

Every definition here is a term, and the compiled subset's own rules say why.
`add-pairs`, `hold-pairs`, `pick` and `only-a` select on head PATTERNS,
`(pair $a $b)` and the symbol `a`, where a compiled head pattern is a literal
default and reaches neither a structure nor a symbol. `holds-a-miss` names the
hyphenated `add-pairs`, which a body resolves exactly as written. And `pick`
and `both-ways` answer LOWERCASE symbols as data (residue, P14.4).

What is ordinary is the asking. A rule that declines has no answer, and
`m.fn(name).all(...)` is what an answer set with nothing in it looks like from
Python: the empty list, not an error.
"""

from petta import REFLECTION_SPACE, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17296 to 11052, -6244 (-36.1%), by the twin contract
#: change: eleven `(test ...)` terms became eleven Python `assert`s, so `test`
#: left the engine eleven times and five `collapse`s went with it, replaced by
#: `.all()`. The four rules, their registrations and every call over them
#: stayed. Against the example's 36588 the ratio is 0.3021.
#: Prior: 17296, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 11052


def pair_sum(head):
    """The guarded clause both `add-pairs` and `hold-pairs` are written from.

    `(= (head (pair $a $b) (pair $c $d)) (noeval (pair (+ $a $c) (+ $b $d))))`.
    """
    return equation(head(S.pair(V.a, V.b), S.pair(V.c, V.d))).to(
        S.noeval(S.pair(V.a + V.c, V.b + V.d))
    )


def twin(m):
    """Register four guarded rules, and ask each of them a hit and a miss."""
    reflection = m.space(REFLECTION_SPACE)
    reflection += (S["dispatch-policy"], S["add-pairs"], S.NoMatchEnum, S.NoMatchFail)
    add_rule = m.fn("add-translator-rule!")
    atom_pair = S["->"](S.Atom, S.Atom, S["%Undefined%"])

    # This rule rewrites a pair addition only when both arguments are pairs,
    # which is the shape the rewrite knows how to add.
    m += S[":"](S["add-pairs"], atom_pair)
    m += pair_sum(S["add-pairs"])
    add_rule(S["add-pairs"])

    assert m.one(S["add-pairs"](S.pair(1, 2), S.pair(10, 20))) == S.pair(11, 22)

    # A call the rule does not match is not an error: it carries on to ordinary
    # dispatch, so a miss has no answer.
    assert m.fn("add-pairs").all(1, 2) == []

    # That is what lets a guarded rule live inside a definition at all.
    m += equation(S["holds-a-miss"]()).to(S["add-pairs"](1, 2))
    assert m.fn("holds-a-miss").all() == []

    # To hand a miss back as DATA instead, write the identity as a second
    # equation; `noeval` stops the expansion from going round again.
    m += S[":"](S["hold-pairs"], atom_pair)
    m += pair_sum(S["hold-pairs"])
    m += equation(S["hold-pairs"](V.a, V.b)).to(
        S.noeval(S.noeval(S["hold-pairs"](V.a, V.b)))
    )
    add_rule(S["hold-pairs"])

    assert m.one(S["hold-pairs"](S.pair(1, 2), S.pair(10, 20))) == S.pair(11, 22)
    # The original writes this claim as `(test (hold-pairs 1 2) (hold-pairs 1 2))`,
    # and `test` evaluates BOTH sides, so its expected value goes through the
    # same rule and the wrapper cancels out of the comparison. An `assert`
    # compares an evaluated left against a LITERAL right, so the wrapper that
    # stops the expansion going round again is visible here.
    assert m.one(S["hold-pairs"](1, 2)) == S.noeval(S["hold-pairs"](1, 2))

    # The engine's own stream operations are written that way: `union` rewrites
    # two superpositions and hands anything else back as it was written.
    assert m.fn("union").all(S.superpose((1, 2)), S.superpose((2, 3))) == [1, 2, 2, 3]
    assert m.one(S.union(S.foo, S.bar)) == S.union(S.foo, S.bar)

    # A RULE'S BODY IS ITS CONDITION: a body with no answer declines, and the
    # next clause is tried, so `(pick a)` is rewritten by the SECOND equation.
    m += S[":"](S.pick, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.pick(S.a)).to(S.empty())
    m += equation(S.pick(V.x)).to(S.noeval(S.picked(V.x)))
    add_rule(S.pick)

    assert m.one(S.pick(S.a)) == S.picked(S.a)
    assert m.one(S.pick(S.b)) == S.picked(S.b)

    # When NO clause applies, the whole rule declines and the call carries on
    # to ordinary dispatch, which here has no answer either.
    m += S[":"](S["only-a"], S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S["only-a"](S.a)).to(S.empty())
    add_rule(S["only-a"])

    assert m.fn("only-a").all(S.a) == []

    # A rule is DETERMINISTIC in a way the function of the same equations is
    # not: written as a plain function, the same two equations answer twice.
    m += equation(S["both-ways"](V.x)).to(S["bw-one"])
    m += equation(S["both-ways"](V.x)).to(S["bw-two"])
    assert m.fn("both-ways").all(S.q) == [S["bw-one"], S["bw-two"]]
