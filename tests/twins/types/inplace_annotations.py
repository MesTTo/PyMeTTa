"""examples/types/inplace_annotations.metta in Python: a type where it prunes.

`(: $x Person)` in a head or a match pattern matches anything of type Person
and binds `$x` to it. It is not a new relation: it desugars to a plain variable
plus exactly the acceptance the engine already compiles for a declared
parameter, so anyone who knows one knows the other. Rex never reaches `greet`'s
body, `type-of` answers once per declared type, one type variable in two
positions makes them agree, and a METATYPE restriction works for the same
reason with nothing added.

Every clause here selects on a STRUCTURE in its head, so all of them are
written as the equations they are: a compiled parameter list carries plain
names and literal defaults, and `(: $x Person)` is neither.

The two gates that make the position rule work are claims too. A pattern that
IS a colon expression stays structural, so the knowledge base still answers
with the declarations somebody wrote; and only `(: $variable expected)` is an
annotation, so `(: a tail)` and the tutorial's `::` list stay ordinary data.
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 21927 to 12585, -9342 (-42.61%), by the twin-shape
#: rewrite: fourteen `test`-plus-`collapse` wrappers left the engine for
#: `assert` over `.all()`, and the two annotated queries read rows at the
#: subscript door instead of collapsing a match template. Against the
#: example's 41321 the ratio is 0.3046 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/types/inplace_annotations.metta`].
#: Prior: RE-PINNED at 21927 by the lift onto @rules plus one m.add(*group).
BUDGET = 12585


def twin(m):
    """Declare types, then prune with them in heads and in queries."""
    typed = S[":"]
    cons = S["::"]

    reflection = m.space("&petta")
    reflection += S["dispatch-policy"](S["shape-of"], S.NoMatchEnum, S.NoMatchFail)

    m += typed(S.Ann, S.Person)
    m += typed(S.Ann, S.Employee)
    m += typed(S.Bob, S.Person)
    m += typed(S.Rex, S.Dog)

    # Restrict a head parameter. Rex never reaches the body.
    m += equation(S.greet(typed(V.x, S.Person))).to(S.hello(V.x))
    assert m.fn("greet").all(S.Ann) == [S.hello(S.Ann)]
    assert m.fn("greet").all(S.Rex) == []

    # Bind the type to a variable instead, and a symbol with two declared
    # types gives a branch each, because nondeterminism is native.
    m += equation(S["type-of"](typed(V.x, V.t))).to(V.t)
    assert m.fn("type-of").all(S.Ann) == [S.Person, S.Employee]
    assert m.fn("type-of").all(S.Rex) == [S.Dog]

    # One type variable in two positions constrains them to agree.
    m += equation(S["same-kind"](typed(V.x, V.t), typed(V.y, V.t))).to((V.x, V.y))
    assert m.fn("same-kind").all(S.Ann, S.Bob) == [S.Ann(S.Bob)]
    assert m.fn("same-kind").all(S.Ann, S.Rex) == []

    # A METATYPE restriction works for the same reason and needs nothing
    # extra: the acceptance falls through to the metatype when nobody
    # declared the symbol.
    m += equation(S.fmap(V.f, typed(V.c, S.Symbol))).to((V.f, V.c))
    assert m.fn("fmap").all(S.g, S.sym) == [S.g(S.sym)]
    assert m.fn("fmap").all(S.g, 42) == []

    # And in a match query, which is where it prunes the search rather than
    # the call. Zeus is a God, so the restricted query does not reach him.
    m += typed(S.Plato, S.Human)
    m += typed(S.Socrates, S.Human)
    m += typed(S.Zeus, S.God)
    m += S.knows(S.Plato, S.Socrates)
    m += S.knows(S.Plato, S.Zeus)

    humans = m[S.knows(typed(V.x, S.Human), typed(V.y, S.Human))]
    assert [(row.x, row.y) for row in humans] == [(S.Plato, S.Socrates)]
    agreeing = m[S.knows(typed(V.x, V.t), typed(V.y, V.t))]
    assert [(row.x, row.y, row.t) for row in agreeing] == [(S.Plato, S.Socrates, S.Human)]

    # GATE 1: the whole pattern is a colon expression, so this retrieves the
    # stored declaration rather than annotating anything.
    assert m[typed(S.Zeus, V.t)]["t"] == [S.God]

    # `::` means nothing special to the engine, which is the point of not
    # having taken it. Here is the tutorial's own list program, verbatim.
    m += equation(S["list-length"](expr())).to(0)
    m += equation(S["list-length"](cons(V.x, V.xs))).to(1 + S["list-length"](V.xs))
    assert m.fn("list-length")(cons(S.A, cons(S.B, cons(S.C, expr())))) == 3

    # GATE 2: the annotation position must hold a VARIABLE, or the form stays
    # structural and nothing looks inside it.
    m += equation(S["shape-of"](typed(S.a, V.rest))).to(V.rest)
    assert m.fn("shape-of").all(typed(S.a, S.tail)) == [S.tail]
    assert m.fn("shape-of").all(typed(S.z, S.tail)) == []
