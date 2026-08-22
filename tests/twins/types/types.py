"""examples/types/types.metta in Python: what a type is and where it lives.

Three groups of claims. Concrete types are declarations about SYMBOLS, so they
are atoms written into the space: there is no Python signature that says
`(: a A)`, because `a` is not a function. Function types are arrows, and the
type variable in `(-> $a $a)` is what a `TypeVar` means. Nondeterministic types
are the ordinary case of a symbol declared twice, which answers twice.

Two doors ask the question. A NAME's declared type is a property of the
function object, `m.fn("a").type`, and it reads `%Undefined%` as `None`,
because "no declared type" is what Python spells with None. Any other atom, an
expression or a ground value, goes through `get-type` itself.

`mid` and `testf` are written at the container door. `mid`'s body is a `let`
whose pattern is an EXPRESSION, so it unifies rather than binds, and `testf`
fixes a SYMBOL in its head; a compiled parameter list reaches neither.
"""

from petta import S, V, Var, equation, expr, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10954 to 5616, -5338 (-48.73%), by the twin-shape
#: rewrite: thirteen `test` wrappers left the engine for `assert`, and six of
#: the questions are the function object's `type` property rather than a
#: `(get-type name)` term. Against the example's 18429 the ratio is 0.3047
#: [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/types.metta`]. Prior: RE-PINNED at 10954 by P14.8's m.eval
#: fuel-scope alignment.
BUDGET = 5616


def twin(m):
    """Declare, then ask, then declare a function and ask about its answers."""
    typed, arrow = S[":"], S["->"]
    kind = m.fn("get-type")

    # Concrete types. Each declaration is a fact about a symbol.
    m += typed(S.a, S.A)
    m += typed(S.b, S.B)
    m += typed(S.A, S.Type)
    m += typed(S.x, S.Letter)
    m += typed(S.x, S.Buchstabe)

    # The type of an unbound variable is itself unknown: another variable.
    assert type(kind(V.a)) is Var
    assert m.fn("a").type == S.A
    assert m.fn("b").type == S.B
    assert m.fn("c").type is None
    assert m.fn("A").type == S.Type
    assert m.fn("B").type is None

    # An expression's type is the expression of its parts' types, and a ground
    # value carries its own.
    assert kind(S.a(S.b)) == S.A(S.B)
    assert kind(42) == S.Number
    assert kind(val("42")) == S.String

    # Two declarations, two answers: collapse is what .all() already is.
    assert kind.all(S.x) == [S.Letter, S.Buchstabe]

    # Function types.
    m += typed(S.mid, arrow(V.a, V.a))
    m += equation(S.mid(V.x)).to(S.let((S.a, S.b), V.x, V.x))  # rung: this let's pattern is an EXPRESSION, so it unifies where Python's assignment binds a name (P14.4)
    assert m.fn("mid")(expr(V.a, S.b)) == S.a(S.b)

    m += typed(S.testx, arrow(V.a, V.b, V.a))
    assert kind(S.testx(1, val("f"))) == S.Number

    # Nondeterministic types: `at` is both an A and a T, so a function
    # declared (-> $a $a) accepts it and answers a T.
    m += typed(S.at, S.A)
    m += typed(S.at, S.T)
    m += typed(S.t, S.T)
    m += typed(S.testf, arrow(V.a, V.a))
    m += equation(S.testf(S.at)).to(S.t)
    assert m.fn("testf")(S.at) == S.t
