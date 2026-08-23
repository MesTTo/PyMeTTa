"""examples/data/foldall.metta in Python: ten spellings of one fold.

`foldall` takes an aggregator, a GENERATOR TERM and a seed, and folds every
answer the generator gives. The term is what makes the file: `(f)` answers 2
and then 3, and foldall sees both, so the argument may not be evaluated on the
way in. That is what the mention door is for. Calling a Symbol BUILDS, so
`S.f()` is the term `(f)` and nothing has run; calling the Python name `f()`
would run it and hand foldall a value.

The ten claims are the same fold with the aggregator and the generator each
written four ways: a defined function, a lambda, a lambda bound by a name, and
a lambda applied to a variable. A `let` that only names a value IS Python's
assignment, so those bindings are locals here and only the last two keep a
construct of their own.

`f` and `g` are the two shapes of stacked clause, and Python spells each one.
`f` is nullary, so its two clauses are two ALTERNATIVES and Python's word for
several results is `yield`: each independent yield stores one equation. `g`'s
clauses fix a literal in an argument position, which is what a parameter
default is, so `g` is two ordinary defs.
"""

from metta import TRUE, Expression, S, V, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Fold two answers into five, ten ways round."""

    @m.define
    def f():                        # (= (f) 2)
        yield 2                     # (= (f) 3)
        yield 3                     #   one equation per alternative

    @m.define
    def g(_=1):                     # (= (g 1) 2): the default IS the head's
        return 2                    #   literal, so the parameter never appears

    @m.define
    def g(_=2):  # noqa: F811  -- two literal heads are two equations, so the second def stacks rather than replacing
        return 3                    # (= (g 2) 3)

    @m.define
    def merge(a, b):                # (= (merge $A $B) (+ $A $B))
        return a + b

    def fold(aggregate, generator, start=0):
        """Aggregate every answer of `generator`, starting from `start`."""
        return m.fn.foldall(aggregate, generator, start).one()

    add = S["|->"]((V.x, V.y), V.x + V.y)     # (|-> ($x $y) (+ $x $y))
    answering_f = S["|->"]((V.z,), S.f())     # (|-> ($z) (f))
    answering_g = S["|->"]((V.z,), S.g(V.z))  # (|-> ($z) (g $z))
    twice_g = S["|->"]((V.z,), 2 * S.g(V.z))  # (|-> ($z) (* 2 (g $z)))

    # A named aggregator, over an argument-free and then an argument-ful
    # generator.
    assert fold(S.merge, S.f()) == 5          # (foldall merge (f) 0)
    assert fold(S.merge, S.g(V.x)) == 5       # (foldall merge (g $x) 0)

    # The same folds with a lambda. `(let $agglambda <lambda> ...)` is this
    # local: a let that only names a value is Python's own assignment.
    assert fold(add, S.f()) == 5
    assert fold(add, S.g(V.z)) == 5
    assert fold(add, S.g(V.z)) == 5

    # A lambda generator, applied to a variable it ignores and then uses.
    assert fold(add, Expression((answering_f, V.x))) == 5
    assert fold(add, Expression((answering_g, V.x))) == 5
    assert fold(add, Expression((answering_g, V.w))) == 5

    # And the aggregator arriving out of a syntactic construct rather than out
    # of a name. `if_` has the arity the engine's `if` has, which is why it is
    # the builder for stored code.
    chosen = if_(TRUE, S.let(V.f, add, V.f), S.empty())  # rung: this `let` is inside a STORED term, where there is no Python statement position for an assignment
    assert fold(chosen, Expression((answering_g, V.w))) == 5
    assert fold(chosen, Expression((twice_g, V.w))) == 10
