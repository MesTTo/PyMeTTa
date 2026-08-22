"""examples/types/meta_types.metta in Python: the metatype IS the Python class.

MeTTa's four kinds are four Python classes here, so `get-metatype` and Python's
own `type()` answer the same question and this twin asks both of every atom the
example asks about. `Sym`, `Var`, `Expr` and `Gnd` are the classes; `Symbol`,
`Variable`, `Expression` and `Grounded` are the names the engine answers with.

One atom answers differently on the two sides, and it is the interesting one:
`+` is a Symbol as Python holds it, because a name built at the `S.` door is
just a name, and Grounded as the engine reads it, because the engine resolves
that name to a builtin operation. The class is what the atom IS; the metatype
is what the engine MAKES of it.
"""

from petta import Expr, Gnd, S, Sym, V, Var, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2046 to 1077, -969 (-47.36%), by the twin-shape
#: rewrite: the six `test` wrappers left the engine for `assert`, and every
#: claim gained a Python-side half, `type(atom) is Sym`, which IS the
#: metatype and costs no engine. Against the example's 4594 the ratio is
#: 0.2344 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/meta_types.metta`]. Prior: RE-PINNED at 2046 by P14.8's
#: m.eval fuel-scope alignment.
BUDGET = 1077


def twin(m):
    """Ask both sides for the metatype of one atom of every kind."""
    metatype = m.fn("get-metatype")

    # An expression, however it was built.
    assert type(S.foo(1, 2)) is Expr
    assert metatype(S.foo(1, 2)) == S.Expression
    assert type(S.a(S.b)) is Expr
    assert metatype(S.a(S.b)) == S.Expression

    # A ground value, a variable and a plain symbol.
    assert type(val(1)) is Gnd
    assert metatype(val(1)) == S.Grounded
    assert type(V.x) is Var
    assert metatype(V.x) == S.Variable
    assert type(S.a) is Sym
    assert metatype(S.a) == S.Symbol

    # The one disagreement, and it is not a defect on either side.
    assert type(S["+"]) is Sym
    assert metatype(S["+"]) == S.Grounded
