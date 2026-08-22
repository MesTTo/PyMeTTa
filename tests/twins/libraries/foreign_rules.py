"""examples/libraries/foreign_rules.metta in Python: a foreign space holding RULES.

In MeTTa a space is BOTH a data source and where the program lives, so an
equation added to a foreign space has to evaluate rather than sit there inert.
A provider says it holds equations by declaring the `rules` capability, and
nothing else about it changes: the engine compiles the equation, so a rule in a
foreign space is the same compiled clause a native one is.

That is why this twin writes those rules the way it would write any others.
`@demo.define` compiles into the provider's space and the recursion and the
nested body come out of Python's own syntax; only `fplain`, whose body is a
bare lowercase symbol, goes to the container door, because a compiled body
resolves a lowercase free name as a function.

Evaluating IN a space is the space handle's own `eval`, which is what
`(metta $atom %Undefined% &space)` says: a rule belongs to the space that holds
it, so calling `(fdouble 21)` from `&self` would find nothing.
"""

from petta import S, V, equation, rules, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 48124 to 42388, -5736 (-11.92%), by the idiomatic
#: rewrite: six `test` wrappers, a `collapse` and a `sort-atom` left the
#: engine for `assert` and `sorted`, and three of the five rules are now
#: compiled by `@demo.define` where the source built them as atoms, which is
#: the same equation through a different door. Measured min-of-three with the
#: MORK backend linked into this worktree, which the earlier figure may not
#: have been. Prior: 48124 was the last figure for the generator twin that
#: yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 42388

#: The provider under test, thirteen lines. Its whole contribution is declaring
#: the `rules` capability beside match, enumerate, add and remove.
PROVIDER = val("./examples/libraries/_fixtures/rule_provider.pl")


def twin(m):
    """Put five rules and one fact in a foreign space, then evaluate them there."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_import)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes
    m.eval(S.import_prolog_functions_from_file(PROVIDER, ()))

    demo = m.space("&rule_demo")

    # A rule, added to the foreign space, evaluating.
    @demo.define
    def fdouble(x):
        return 2 * x

    assert demo.eval(S.fdouble(21)) == [42]

    # Several equations for one name are an answer SET, which is what MeTTa
    # promises. Sorted, because a set has no order.
    @rules
    def picks():
        yield equation(S.fpick()).to(S.one)
        yield equation(S.fpick()).to(S.two)

    demo.add(*picks)
    assert sorted(demo.eval(S.fpick()), key=str) == [S.one, S.two]

    # A body that is not a call IS the answer, the way a native equation with a
    # bare atom body behaves.
    demo += equation(S.fplain()).to(S.settled)
    assert demo.eval(S.fplain()) == [S.settled]

    # A body is evaluated FURTHER, so a nested call is evaluated inside out.
    # Reading evaluation as "match for (= (f Args) $body) and reduce $body" is
    # the naive reading, and here that shows up as (* 2 3) reaching + as a list
    # instead of as 6.
    @demo.define
    def fnest():
        return 1 + 2 * 3

    assert demo.eval(S.fnest()) == [7]

    # Recursion, and `if` evaluating only the branch it takes.
    @demo.define
    def ffact(x):
        return x * ffact(x - 1) if x > 0 else 1

    assert demo.eval(S.ffact(5)) == [120]

    # And the space is still a data source. Holding rules is an addition, not a
    # replacement, which is the whole of what "both" means.
    demo += S.edge(S.a, S.b)
    assert [(row.x, row.y) for row in demo.query(S.edge(V.x, V.y))] == [(S.a, S.b)]
