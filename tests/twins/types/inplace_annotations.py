"""Purpose: examples/types/inplace_annotations.metta in Python: a type where it prunes.

`(: $x Person)` in a head or a match pattern matches anything of type Person
and binds `$x` to it. It is not a new relation: it desugars to a plain variable
plus exactly the acceptance the engine already compiles for a declared
parameter, so anyone who knows one knows the other. Rex never reaches `greet`'s
body, `type-of` answers once per declared type, one type variable in two
positions makes them agree, and a METATYPE restriction works for the same
reason with nothing added.

Every clause here selects on a STRUCTURE in its head, so all of them are
written as the equations they are: a compiled parameter list carries plain
names and literal defaults, and `typed(V.x, S.Person)` is neither.

The two gates that make the position rule work are claims too. A pattern that
IS a colon expression stays structural, so the knowledge base still answers
with the declarations somebody wrote; and only `(: $variable expected)` is an
annotation, so `(: a tail)` and the tutorial's `::` list stay ordinary data.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import petta
from petta import Expression, S, V, equation, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1

#: The tutorial's own cons constructor, which means nothing to the engine.
CONS = S["::"]


def twin(m):
    """Declare types, then prune with them in heads and in queries."""
    reflection = petta.reflection
    reflection += S["dispatch-policy"](S["shape-of"], S.NoMatchEnum, S.NoMatchFail)

    m += typed(S.Ann, S.Person)
    m += typed(S.Ann, S.Employee)
    m += typed(S.Bob, S.Person)
    m += typed(S.Rex, S.Dog)

    # Restrict a head parameter. Rex never reaches the body.
    m += equation(S.greet(typed(V.x, S.Person))).to(S.hello(V.x))
    assert m.fn.greet(S.Ann) == [S.hello(S.Ann)]
    assert m.fn.greet(S.Rex) == []

    # Bind the type to a variable instead, and a symbol with two declared
    # types gives a branch each, because nondeterminism is native.
    m += equation(S["type-of"](typed(V.x, V.t))).to(V.t)
    assert m.fn.type_of(S.Ann) == [S.Person, S.Employee]
    assert m.fn.type_of(S.Rex) == [S.Dog]

    # One type variable in two positions constrains them to agree.
    m += equation(S["same-kind"](typed(V.x, V.t), typed(V.y, V.t))).to((V.x, V.y))
    assert m.fn.same_kind(S.Ann, S.Bob) == [S.Ann(S.Bob)]
    assert m.fn.same_kind(S.Ann, S.Rex) == []

    # A METATYPE restriction works for the same reason and needs nothing
    # extra: the acceptance falls through to the metatype when nobody
    # declared the symbol.
    m += equation(S.fmap(V.f, typed(V.c, S.Symbol))).to((V.f, V.c))
    assert m.fn.fmap(S.g, S.sym) == [S.g(S.sym)]
    assert m.fn.fmap(S.g, 42) == []

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
    #
    # Known issue: the eager Rows a subscript answers projects only through a
    # string key, `rows["t"]`, where the lazy Answers projects by attribute
    # and by variable. Reading each row keeps the string out; the whole-column
    # spelling should read:
    #     assert m[typed(S.Zeus, V.t)].t == [S.God]
    assert [row.t for row in m[typed(S.Zeus, V.t)]] == [S.God]

    # `::` means nothing special to the engine, which is the point of not
    # having taken it. Here is the tutorial's own list program, verbatim.
    m += equation(S["list-length"](Expression(()))).to(0)
    m += equation(S["list-length"](CONS(V.x, V.xs))).to(1 + S["list-length"](V.xs))
    assert m.fn.list_length(CONS(S.A, CONS(S.B, CONS(S.C, Expression(()))))) == [3]

    # GATE 2: the annotation position must hold a VARIABLE, or the form stays
    # structural and nothing looks inside it.
    m += equation(S["shape-of"](typed(S.a, V.rest))).to(V.rest)
    assert m.fn.shape_of(typed(S.a, S.tail)) == [S.tail]
    assert m.fn.shape_of(typed(S.z, S.tail)) == []
