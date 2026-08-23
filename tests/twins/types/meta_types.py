"""Purpose: examples/types/meta_types.metta in Python: the metatype IS the Python class.

MeTTa's four kinds are four Python classes here, so `get-metatype` and Python's
own `type()` answer the same question, and this twin asks both of every atom the
example asks about.

One atom answers differently on the two sides, and it is the interesting one:
`+` is a Symbol as Python holds it, because a name built at the operator WORD
door is just a name, and Grounded as the engine reads it, because the engine
resolves that name to a builtin operation. The class is what the atom IS; the
metatype is what the engine MAKES of it.
"""

from metta import Expression, Grounded, S, Symbol, V, Variable, ground

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Ask both sides for the metatype of one atom of every kind."""
    metatype = m.fn.get_metatype

    # An expression, however it was built.
    # !(test (get-metatype (foo 1 2)) Expression)
    assert type(S.foo(1, 2)) is Expression
    assert metatype(S.foo(1, 2)) == [S.Expression]
    # !(test (get-metatype (a b)) Expression)
    assert type(S.a(S.b)) is Expression
    assert metatype(S.a(S.b)) == [S.Expression]

    # A ground value, a variable and a plain symbol.
    # !(test (get-metatype 1) Grounded)
    assert type(ground(1)) is Grounded
    assert metatype(ground(1)) == [S.Grounded]
    # !(test (get-metatype $x) Variable)
    assert type(V.x) is Variable
    assert metatype(V.x) == [S.Variable]
    # !(test (get-metatype a) Symbol)
    assert type(S.a) is Symbol
    assert metatype(S.a) == [S.Symbol]

    # The one disagreement, and it is not a defect on either side.
    # !(test (get-metatype +) Grounded)
    assert type(S.add) is Symbol
    assert metatype(S.add) == [S.Grounded]
