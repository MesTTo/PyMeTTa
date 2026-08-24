"""examples/translation/translatorrule_guard.metta in Python: rules that decline.

A translator rule's head is a PATTERN, so a rule can carry a guard: it names
the shape it rewrites, and a call of another shape is left to ordinary
dispatch rather than bringing the translation down. The example walks that from
both sides, then adds the half a head shape cannot say, which is that a rule's
BODY is its condition too: a clause whose body has no answer declines, and the
next clause is tried.

Five of the six definitions are LAWS with structured heads, and that is what
`@m.rules` is for: a bundle whose parameters ARE the equations' variables,
whose clauses coexist rather than being made exclusive, and which derives no
guard of its own. So `(add-pairs (pair $a $b) (pair $c $d))` is written as the
head it is, and `hold-pairs` and `pick` each carry their two clauses in one
bundle, in the order the rule tries them.

A bundle body EXECUTES rather than lowering, so its arithmetic on the rule
variables BUILDS: `a + c` there is the term `(+ $a $c)`. Its type declaration
is data for the same reason, `typed(head, arrow(...))` rather than an
annotation, because a bundle has no signature to annotate.

The sixth is not a law. `both-ways` has one head and two answers, which is
Python's `yield`, and its point is that the same two equations answer twice
where a rule would take only the first.

What is ordinary throughout is the asking. A rule that declines has no answer,
and that is what an empty answer set looks like from Python: the empty list,
not an error.
"""

from typing import Any

import metta
from metta import Atom, S, arrow, equation, fn, typed

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
BUDGET = 1


def twin(m):
    """Register five guarded rules, and ask each of them a hit and a miss."""
    metta.reflection += (S["dispatch-policy"], S["add-pairs"], S.NoMatchEnum, S.NoMatchFail)

    # This rule rewrites a pair addition only when both arguments are pairs,
    # which is the shape the rewrite knows how to add.
    m += typed(S["add-pairs"], arrow(Atom, Atom, Any))

    @m.rules
    def summing(a, b, c, d):             # (= (add-pairs (pair $a $b) (pair $c $d))
        yield equation(S["add-pairs"](S.pair(a, b), S.pair(c, d))).to(
            S.noeval(S.pair(a + c, b + d)))      # (noeval (pair (+ $a $c) (+ $b $d))))

    m.fn.add_translator_rule(S["add-pairs"])

    assert m.fn.add_pairs(S.pair(1, 2), S.pair(10, 20)).one() == S.pair(11, 22)

    # A call the rule does not match is not an error: it carries on to ordinary
    # dispatch, so a miss has no answer.
    assert m.fn.add_pairs(1, 2) == []

    # That is what lets a guarded rule live inside a definition at all.
    @m.define
    def holds_a_miss():                  # (= (holds-a-miss) (add-pairs 1 2))
        return fn.add_pairs(1, 2)

    assert holds_a_miss() == []

    # To hand a miss back as DATA instead, write the identity as a second
    # equation. The rule tries them in order, so the guarded one still wins
    # where it fits, and `noeval` stops the expansion going round again.
    m += typed(S["hold-pairs"], arrow(Atom, Atom, Any))

    @m.rules
    def holding(a, b, c, d):             # (= (hold-pairs (pair $a $b) (pair $c $d))
        yield equation(S["hold-pairs"](S.pair(a, b), S.pair(c, d))).to(
            S.noeval(S.pair(a + c, b + d)))      # (noeval (pair (+ $a $c) (+ $b $d))))
        yield equation(S["hold-pairs"](a, b)).to(       # (= (hold-pairs $a $b)
            S.noeval(S.noeval(S["hold-pairs"](a, b))))  # (noeval (noeval (hold-pairs $a $b))))

    m.fn.add_translator_rule(S["hold-pairs"])

    assert m.fn.hold_pairs(S.pair(1, 2), S.pair(10, 20)).one() == S.pair(11, 22)
    # The original writes this claim as `(test (hold-pairs 1 2) (hold-pairs 1 2))`,
    # and `test` evaluates BOTH sides, so its expected value goes through the
    # same rule and the wrapper cancels out of the comparison. An assert
    # compares an evaluated left against a LITERAL right, so the wrapper that
    # stops the expansion going round again is visible here.
    assert m.fn.hold_pairs(1, 2).one() == S.noeval(S["hold-pairs"](1, 2))

    # The engine's own stream operations are written that way: `union` rewrites
    # two superpositions and hands anything else back as it was written.
    assert m.fn.union(S.superpose((1, 2)), S.superpose((2, 3))) == [1, 2, 2, 3]
    assert m.fn.union(S.foo, S.bar).one() == S.union(S.foo, S.bar)

    # A RULE'S BODY IS ITS CONDITION: a body with no answer declines, and the
    # next clause is tried, so `(pick a)` is rewritten by the SECOND equation.
    m += typed(S.pick, arrow(Atom, Any))

    @m.rules
    def picking(x):
        yield equation(S.pick(S.a)).to(S.empty())          # (= (pick a) (empty))
        yield equation(S.pick(x)).to(S.noeval(S.picked(x)))  # (= (pick $x) (noeval (picked $x)))

    m.fn.add_translator_rule(S.pick)

    assert m.fn.pick(S.a).one() == S.picked(S.a)
    assert m.fn.pick(S.b).one() == S.picked(S.b)

    # When NO clause applies, the whole rule declines and the call carries on
    # to ordinary dispatch, which here has no answer either.
    m += typed(S["only-a"], arrow(Atom, Any))

    @m.rules
    def only_a():
        yield equation(S["only-a"](S.a)).to(S.empty())     # (= (only-a a) (empty))

    m.fn.add_translator_rule(S["only-a"])

    assert m.fn.only_a(S.a) == []

    # A rule is DETERMINISTIC in a way the function of the same equations is
    # not: written as a plain function, the same two equations answer twice.
    @m.define
    def both_ways(_):                    # (= (both-ways $x) bw-one)
        yield S["bw-one"]                # (= (both-ways $x) bw-two)
        yield S["bw-two"]

    assert both_ways(S.q) == [S["bw-one"], S["bw-two"]]
