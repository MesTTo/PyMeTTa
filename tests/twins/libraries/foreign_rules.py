"""examples/libraries/foreign_rules.metta in Python: a foreign space holding RULES.

In MeTTa a space is BOTH a data source and where the program lives, so an
equation added to a foreign space has to evaluate rather than sit there inert.
A provider says it holds equations by declaring the `rules` capability, and
nothing else about it changes: the engine compiles the equation, so a rule in a
foreign space is the same compiled clause a native one is.

That is why this twin writes those rules the way it would write any others.
`@demo.define` compiles into the provider's space, the recursion and the nested
body come out of Python's own syntax, a body that is a bare lowercase symbol is
the `S` factory, and the two equations that share a head are two yields, since
each independent yield stores one equation.

Evaluating IN a space is the space handle's own `eval`, which is what
`(metta $atom %Undefined% &space)` says: a rule belongs to the space that holds
it, so calling `(fdouble 21)` from `&self` would find nothing.

The provider's space is reached by ATOM, `metta.space(S["rule_demo"])`, because
a space name is a symbol and never text; that one keeps the bracket, as
`import_prolog_functions_from_file` does, because both MeTTa names really have
underscores and the attribute door maps every underscore to a hyphen.
"""

import metta
from metta import G, S, V

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1

#: The provider under test, thirteen lines. Its whole contribution is declaring
#: the `rules` capability beside match, enumerate, add and remove.
PROVIDER = G("./examples/libraries/_fixtures/rule_provider.pl")


def twin(m):
    """Put five rules and one fact in a foreign space, then evaluate them there."""
    m.fn["import!"](m, S.library(S["lib_import"]))
    m.eval(S["import_prolog_functions_from_file"](PROVIDER, ()))

    demo = metta.space(S["rule_demo"])

    # A rule, added to the foreign space, evaluating.
    @demo.define
    def fdouble(x):
        # (= (fdouble $x) (* 2 $x))
        return 2 * x

    assert demo.eval(S.fdouble(21)) == [42]

    # Several equations for one name are an answer SET, which is what MeTTa
    # promises, and two yields are those two equations. Sorted, because a set
    # has no order.
    @demo.define
    def fpick():
        yield S.one
        yield S.two

    assert sorted(demo.eval(S.fpick())) == [S.one, S.two]

    # A body that is not a call IS the answer, the way a native equation with a
    # bare atom body behaves.
    @demo.define
    def fplain():
        return S.settled

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
    assert [(row.x, row.y) for row in demo.match(S.edge(V.x, V.y))] == [(S.a, S.b)]
