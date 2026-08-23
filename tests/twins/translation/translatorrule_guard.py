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
`m.fn.<name>(...)` is what an answer set with nothing in it looks like from
Python: the empty list, not an error.
"""

import petta
from petta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def pair_sum(head):
    """The guarded clause both `add-pairs` and `hold-pairs` are written from.

    `(= (head (pair $a $b) (pair $c $d)) (noeval (pair (+ $a $c) (+ $b $d))))`.
    """
    return equation(head(S.pair(V.a, V.b), S.pair(V.c, V.d))).to(
        S.noeval(S.pair(V.a + V.c, V.b + V.d))
    )


def twin(m):
    """Register four guarded rules, and ask each of them a hit and a miss."""
    reflection = petta.reflection
    reflection += (S["dispatch-policy"], S["add-pairs"], S.NoMatchEnum, S.NoMatchFail)
    atom_pair = S["->"](S.Atom, S.Atom, S["%Undefined%"])

    # This rule rewrites a pair addition only when both arguments are pairs,
    # which is the shape the rewrite knows how to add.
    m += S[":"](S["add-pairs"], atom_pair)
    m += pair_sum(S["add-pairs"])
    m.fn.add_translator_rule(S["add-pairs"])

    assert m.fn.add_pairs(S.pair(1, 2), S.pair(10, 20)).one() == S.pair(11, 22)

    # A call the rule does not match is not an error: it carries on to ordinary
    # dispatch, so a miss has no answer.
    assert m.fn.add_pairs(1, 2) == []

    # That is what lets a guarded rule live inside a definition at all.
    m += equation(S["holds-a-miss"]()).to(S["add-pairs"](1, 2))
    assert m.fn.holds_a_miss() == []

    # To hand a miss back as DATA instead, write the identity as a second
    # equation; `noeval` stops the expansion from going round again.
    m += S[":"](S["hold-pairs"], atom_pair)
    m += pair_sum(S["hold-pairs"])
    m += equation(S["hold-pairs"](V.a, V.b)).to(
        S.noeval(S.noeval(S["hold-pairs"](V.a, V.b)))
    )
    m.fn.add_translator_rule(S["hold-pairs"])

    assert m.fn.hold_pairs(S.pair(1, 2), S.pair(10, 20)).one() == S.pair(11, 22)
    # The original writes this claim as `(test (hold-pairs 1 2) (hold-pairs 1 2))`,
    # and `test` evaluates BOTH sides, so its expected value goes through the
    # same rule and the wrapper cancels out of the comparison. An `assert`
    # compares an evaluated left against a LITERAL right, so the wrapper that
    # stops the expansion going round again is visible here.
    assert m.fn.hold_pairs(1, 2).one() == S.noeval(S["hold-pairs"](1, 2))

    # The engine's own stream operations are written that way: `union` rewrites
    # two superpositions and hands anything else back as it was written.
    assert m.fn.union(S.superpose((1, 2)), S.superpose((2, 3))) == [1, 2, 2, 3]
    assert m.fn.union(S.foo, S.bar).one() == S.union(S.foo, S.bar)

    # A RULE'S BODY IS ITS CONDITION: a body with no answer declines, and the
    # next clause is tried, so `(pick a)` is rewritten by the SECOND equation.
    m += S[":"](S.pick, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.pick(S.a)).to(S.empty())
    m += equation(S.pick(V.x)).to(S.noeval(S.picked(V.x)))
    m.fn.add_translator_rule(S.pick)

    assert m.fn.pick(S.a).one() == S.picked(S.a)
    assert m.fn.pick(S.b).one() == S.picked(S.b)

    # When NO clause applies, the whole rule declines and the call carries on
    # to ordinary dispatch, which here has no answer either.
    m += S[":"](S["only-a"], S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S["only-a"](S.a)).to(S.empty())
    m.fn.add_translator_rule(S["only-a"])

    assert m.fn.only_a(S.a) == []

    # A rule is DETERMINISTIC in a way the function of the same equations is
    # not: written as a plain function, the same two equations answer twice.
    m += equation(S["both-ways"](V.x)).to(S["bw-one"])
    m += equation(S["both-ways"](V.x)).to(S["bw-two"])
    assert m.fn.both_ways(S.q) == [S["bw-one"], S["bw-two"]]
