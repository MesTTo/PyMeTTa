"""Purpose: examples/types/types.metta in Python: what a type is and where it lives.

Three groups of claims. Concrete types are declarations about SYMBOLS, so they
are atoms written into the space: there is no Python signature that says
`(: a A)`, because `a` is not a function, and `typed(x, T)` is the builder for
that declaration term. Function types are arrows, and the type variable in
`(-> $a $a)` is what a variable in `arrow(V.a, V.a)` means. Nondeterministic
types are the ordinary case of a symbol declared twice, which answers twice.

`space.type(atom)` is the get-type accessor and answers the FIRST type, which
is every claim here but one: `x` is declared twice, and the whole answer set is
the form itself, evaluated.

`mid` and `testf` are written at the container door. `mid`'s body is a `let`
whose pattern is an EXPRESSION, so it unifies rather than binds, and `testf`
fixes a SYMBOL in its head; a compiled parameter list reaches neither.
"""

from petta import Expression, S, V, Variable, arrow, equation, fn, ground, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1

#: The unconstrained type. Python's grammar cannot spell `%Undefined%`, so the
#: name takes the bracket; `Any` is its image in a DECLARING position, where
#: `typed` and `arrow` read it through the annotation table.
#:
#: Known issue: that table is one-way. A twin comparing an ANSWER against a
#: type atom has no Python-type spelling for it, so the marked name is written
#: out. It should read `assert m.type(S.c) == Any`, with the same table
#: reading `Any` on the right of an equality as it already reads it inside
#: `arrow(...)` and `typed(...)`.
UNDEFINED = S["%Undefined%"]


def twin(m):
    """Declare, then ask, then declare a function and ask about its answers."""
    # Concrete types. Each declaration is a fact about a symbol.
    m += typed(S.a, S.A)
    m += typed(S.b, S.B)
    m += typed(S.A, S.Type)
    m += typed(S.x, S.Letter)
    m += typed(S.x, S.Buchstabe)

    # The type of an unbound variable is itself unknown: another variable.
    assert type(m.type(V.a)) is Variable
    assert m.type(S.a) == S.A
    assert m.type(S.b) == S.B
    assert m.type(S.c) == UNDEFINED
    assert m.type(S.A) == S.Type
    assert m.type(S.B) == UNDEFINED

    # An expression's type is the expression of its parts' types, and a ground
    # value carries its own.
    assert m.type(S.a(S.b)) == S.A(S.B)
    assert m.type(42) == S.Number
    assert m.type(ground("42")) == S.String

    # Two declarations, two answers, so this one calls the relation: the
    # accessor answers the first type and the example collapses every one.
    assert m.fn.get_type(S.x) == [S.Letter, S.Buchstabe]

    # Function types.
    m += typed(S.mid, arrow(V.a, V.a))
    m += equation(S.mid(V.x)).to(fn.let(S.a(S.b), V.x, V.x))  # rung: this let's pattern is an EXPRESSION, so it unifies where Python's assignment binds a name (P14.4)
    # Known issue: a call carrying a caller variable answers that variable's
    # BINDINGS and drops the value, so this claim reads the form. It should
    # read:
    #     assert m.fn.mid(Expression((V.a, S.b))) == [S.a(S.b)]
    assert m.eval(S.mid(Expression((V.a, S.b)))) == [S.a(S.b)]

    m += typed(S.testx, arrow(V.a, V.b, V.a))
    assert m.type(S.testx(1, ground("f"))) == S.Number

    # Nondeterministic types: `at` is both an A and a T, so a function
    # declared (-> $a $a) accepts it and answers a T.
    m += typed(S.at, S.A)
    m += typed(S.at, S.T)
    m += typed(S.t, S.T)
    m += typed(S.testf, arrow(V.a, V.a))
    m += equation(S.testf(S.at)).to(S.t)
    assert m.fn.testf(S.at) == [S.t]
