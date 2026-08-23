"""Purpose: examples/data/foldall.metta in Python: aggregating a generator's answers.

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
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


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
    assert fold(add, Expression((answering_f, V.x))) == [5]
    assert fold(add, Expression((answering_g, V.x))) == [5]
    assert fold(add, Expression((answering_g, V.w))) == [5]

    # And the aggregator arriving out of a syntactic construct rather than
    # out of a name.
    chosen = S["if"](True, S.let(V.agg, add, V.agg), S.empty())  # rung: the aggregator must reach foldall as a TERM, so its `if` and `let` stay terms too  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert fold(chosen, Expression((answering_g, V.w))) == [5]
    assert fold(chosen, Expression((twice_g, V.w))) == [10]
