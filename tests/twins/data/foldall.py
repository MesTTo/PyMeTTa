"""examples/data/foldall.metta in Python: aggregating a generator's answers.

`foldall` takes an aggregator, a GENERATOR TERM and a seed, and folds every
answer the generator gives. The term matters: `(f)` answers 2 and then 3, and
foldall sees both, so the argument cannot be evaluated on the way in. That is
why the calls here build the term and hand it over rather than calling anything
in Python first.

The ten claims are the same fold with the aggregator and the generator each
written four ways: a defined function, a lambda, a lambda bound by a `let`,
and a lambda applied to a variable. A `let` that only names a value is Python's
own assignment, so the bindings become locals and only the two `if`-wrapped
forms keep a term of their own.

`f` and `g` are the two shapes of stacked clause. `g`'s clauses fix a LITERAL
in an argument position, which is what a compiled default is, so `g` is two
ordinary defs. `f` is nullary and has no argument position to fix, so a second
`def f()` would REBIND the Python name and lose the first equation; those two
clauses are written as the equations they are (filed as friction).
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 24789 to 22717, -2072 (-8.36%), by the twin-shape
#: rewrite: ten `test` wrappers left the engine for `assert`, and the `let`
#: and `let*` terms that bound the lambdas became Python locals, so nothing
#: reduces to bind them. `f` moved the other way, from one compiled generator
#: to the TWO stored equations the original writes: the generator spelling
#: stores `(= (f) (superpose (2 3)))`, one clause where the example has two,
#: and the same file with it measures 22660, so faithfulness costs 57 here.
#: Against the example's 35344 the ratio is 0.6427 [measured 2026-08-22 min-
#: of-3: `twin_coverage.py --measure examples/data/foldall.metta`]. Prior:
#: RE-PINNED at 24789 by the wave-4 idiom rewrite.
BUDGET = 22717


def twin(m):
    """Fold two answers into five, ten ways round."""
    add = S["|->"]((V.x, V.y), V.x + V.y)
    answering_f = S["|->"]((V.z,), S.f())
    answering_g = S["|->"]((V.z,), S.g(V.z))
    twice_g = S["|->"]((V.z,), 2 * S.g(V.z))

    def fold(aggregate, generator, start=0):
        """Aggregate every answer of `generator`, starting from `start`."""
        return m.eval(S.foldall(aggregate, generator, start))

    m += equation(S.f()).to(2)
    m += equation(S.f()).to(3)

    @m.define
    def g(x=1):  # noqa: ARG001  -- the default IS the head pattern, and this clause answers a constant
        return 2

    @m.define
    def g(x=2):  # noqa: ARG001, F811  -- stacked clauses are stacked equations, so the second def adds one rather than replacing it
        return 3

    @m.define
    def merge(a, b):
        return a + b

    # A named aggregator over an argument-free and then an argument-ful
    # generator.
    assert fold(S.merge, S.f()) == [5]
    assert fold(S.merge, S.g(V.x)) == [5]

    # The same folds with a lambda. `(let $agg <lambda> ...)` is this local.
    assert fold(add, S.f()) == [5]
    assert fold(add, S.g(V.z)) == [5]
    assert fold(add, S.g(V.z)) == [5]

    # A lambda generator, applied to a variable it ignores and then uses.
    assert fold(add, expr(answering_f, V.x)) == [5]
    assert fold(add, expr(answering_g, V.x)) == [5]
    assert fold(add, expr(answering_g, V.w)) == [5]

    # And the aggregator arriving out of a syntactic construct rather than
    # out of a name.
    chosen = S["if"](True, S.let(V.agg, add, V.agg), S.empty())  # rung: the aggregator must reach foldall as a TERM, so its `if` and `let` stay terms too  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert fold(chosen, expr(answering_g, V.w)) == [5]
    assert fold(chosen, expr(twice_g, V.w)) == [10]
