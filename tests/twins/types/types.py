"""Purpose: examples/types/types.metta in Python: what a type is and where it lives.

Three groups of claims. Concrete types are declarations about SYMBOLS, so they
are atoms written into the space: there is no Python signature that says
`(: a A)`, because `a` is not a function, and `typed(x, T)` is the builder for
that declaration term. Function types are arrows, and the type variable in
`(-> $a $a)` is what Python's own type parameter says, so `mid` and `testf` are
ordinary generic functions and `@m.define` publishes the arrow their signatures
name.

`space.type(atom)` is the get-type accessor and answers the FIRST type, which
is every claim here but one: `x` is declared twice, and the whole answer set is
the form itself, evaluated.

Both function bodies select on a STRUCTURE, and Python's `match` statement is
MeTTa's own `case`: `mid` keeps only an argument shaped `(a b)` and `testf`
keeps only the symbol `at`. Measured on this engine, `case` unifies both ways,
so `mid(($a b))` answers `(a b)` exactly as the original's `let` does.
"""

from metta import Expression, S, V, Variable, arrow, ground, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1

#: The unconstrained type. Python's grammar cannot spell `%Undefined%`, so the
#: name takes the bracket; `Any` is its image in a DECLARING position, where
#: `typed` and `arrow` read it through the annotation table.
#:
#: The table is one-way, which is friction against P14.9: a twin comparing an
#: ANSWER against a type atom has no Python-type spelling for it, so the marked
#: name is written out. It should read `assert m.type(S.c) == Any`, with the
#: same table reading `Any` on the right of an equality as it already reads it
#: inside `arrow(...)` and `typed(...)`.
UNDEFINED = S["%Undefined%"]


def twin(m):
    """Declare, then ask, then declare a function and ask about its answers."""
    # Concrete types. Each declaration is a fact about a symbol.
    # (: a A) (: b B) (: A Type) (: x Letter) (: x Buchstabe)
    m += typed(S.a, S.A)
    m += typed(S.b, S.B)
    m += typed(S.A, S.Type)
    m += typed(S.x, S.Letter)
    m += typed(S.x, S.Buchstabe)

    # The type of an unbound variable is itself unknown: another variable.
    # !(test (get-type $a) $z)
    assert type(m.type(V.a)) is Variable
    # !(test (get-type a) A)
    assert m.type(S.a) == S.A
    # !(test (get-type b) B)
    assert m.type(S.b) == S.B
    # !(test (get-type c) %Undefined%)
    assert m.type(S.c) == UNDEFINED
    # !(test (get-type A) Type)
    assert m.type(S.A) == S.Type
    # !(test (get-type B) %Undefined%)
    assert m.type(S.B) == UNDEFINED

    # An expression's type is the expression of its parts' types, and a ground
    # value carries its own.
    # !(test (get-type (a b)) (A B))
    assert m.type(S.a(S.b)) == S.A(S.B)
    # !(test (get-type 42) Number)
    assert m.type(42) == S.Number
    # !(test (get-type "42") String)
    assert m.type(ground("42")) == S.String

    # Two declarations, two answers, so this one calls the relation: the
    # accessor answers the first type and the example collapses every one.
    # !(test (collapse (get-type x)) (Letter Buchstabe))
    assert m.fn.get_type(S.x) == [S.Letter, S.Buchstabe]

    @m.define
    def mid[T](x: T) -> T:
        """(: mid (-> $a $a)), and a body that keeps only an `(a b)`."""
        match x:
            case (S.a, S.b):
                return x

    # !(test (mid ($a b)) (a b))
    assert mid(Expression((V.a, S.b))) == [S.a(S.b)]

    # `testx` is a declaration and nothing else: no equation defines it, so
    # the arrow is the whole of what the file says about it.
    # (: testx (-> $a $b $a))
    m += typed(S.testx, arrow(V.a, V.b, V.a))
    # !(test (get-type (testx 1 "f")) Number)
    assert m.type(S.testx(1, ground("f"))) == S.Number

    # Nondeterministic types: `at` is both an A and a T, so a function
    # declared (-> $a $a) accepts it and answers a T.
    # (: at A) (: at T) (: t T)
    m += typed(S.at, S.A)
    m += typed(S.at, S.T)
    m += typed(S.t, S.T)

    @m.define
    def testf[T](x: T) -> T:
        """(: testf (-> $a $a)), and a body that answers only for `at`."""
        match x:
            case S.at:
                return S.t

    # !(test (testf at) t)
    assert testf(S.at) == [S.t]
