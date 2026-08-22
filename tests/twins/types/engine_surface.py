"""examples/types/engine_surface.metta in Python: the engine's own type surface.

Nothing is imported here. The engine reads its own declarations at boot and
consults them LAST, so `get-type` answers for a special form, a structure
operation or the state cell while the program's space stays the program's own.
This twin asks all of them the same way the sibling `builin_types` asks the
library's: the declared type of a name is a property of its function object.

Two things it also shows. The declarations are FACTS the engine holds, not
atoms in `&self`, so matching the program's space for `(: $n $t)` retrieves
only what the program itself declared. And a program's own declaration is
answered AHEAD of the engine's, without taking the operation away: after
`(: car-atom MyOverride)` the builtin still answers, and `get-type` answers
both.

`%Undefined%` and the arrow are written at the `S.` door because a type ATOM
in an expected answer has no Python-type conversion, unlike a type in a
declaring position, where an annotation says it (filed as friction).
"""

from petta import S, V, alpha_eq, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 18710 to 10205, -8505 (-45.46%), by the twin-shape
#: rewrite: twenty-five `test` wrappers left the engine for `assert`, and the
#: space-contents claim reads the space by ITERATING it in Python where the
#: original collapses a match. Against the example's 34086 the ratio is
#: 0.2994 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/engine_surface.metta`]. Prior: RE-PINNED at 18710 by
#: P14.8's typed state cell plus fuel-scope parity.
BUDGET = 10205


def twin(m):
    """Read the engine's declared types, then overlay one of them."""
    typed, arrow = S[":"], S["->"]
    undefined = S["%Undefined%"]
    kind = m.fn("get-type")

    # Special forms are compiled by the translator and have no registry entry,
    # so they were the least reachable half of the surface.
    assert alpha_eq(m.fn("if").type, arrow(S.Bool, S.Atom, S.Atom, V.t))
    assert m.fn("let").type == arrow(S.Atom, undefined, S.Atom, undefined)
    assert m.fn("chain").type == arrow(S.Atom, S.Variable, S.Atom, undefined)
    assert m.fn("quote").type == arrow(S.Atom, S.Atom)
    assert m.fn("collapse").type == arrow(S.Atom, S.Atom)
    assert m.fn("superpose").type == arrow(S.Expression, undefined)
    assert m.fn("match").type == arrow(S.SpaceType, S.Atom, S.Atom, undefined)
    assert m.fn("map-atom").type == arrow(
        S.Expression, S.Variable, S.Atom, S.Expression
    )

    # Expression structure, from the reference corelib dump.
    assert m.fn("car-atom").type == arrow(S.Expression, undefined)
    assert m.fn("cdr-atom").type == arrow(S.Expression, S.Expression)
    assert m.fn("cons-atom").type == arrow(S.Atom, S.Expression, S.Atom)
    assert m.fn("size-atom").type == arrow(S.Expression, S.Number)
    assert m.fn("index-atom").type == arrow(S.Expression, S.Number, S.Atom)

    # PeTTa's own, with no dump entry to take.
    assert m.fn("sort-atom").type == arrow(S.Expression, S.Expression)
    assert m.fn("is-var").type == arrow(S.Atom, S.Bool)
    assert m.fn("repr").type == arrow(S.Atom, S.String)
    assert m.fn("current-time").type == arrow(S.Number)

    # The state cell is a VALUE and its type says what it holds.
    cell = S.StateMonad
    assert alpha_eq(m.fn("new-state").type, arrow(V.t, cell(V.t)))
    assert alpha_eq(m.fn("change-state!").type, arrow(cell(V.t), V.t, cell(V.t)))
    assert alpha_eq(m.fn("get-state").type, arrow(cell(V.t), V.t))
    assert kind(S["new-state"](5)) == cell(S.Number)
    assert kind(S["new-state"](val("hi"))) == cell(S.String)

    # The surface is FACTS, not atoms in &self: a program still sees only its
    # own declarations when it enumerates them, which is what iterating a
    # space is for. The subscript door would be the other spelling and it
    # reads a wholly-variable `(: $n $t)` as an annotation rather than as
    # data, where the engine's own match keeps it structural (friction).
    m += typed(S["program-own-type"], S.MyType)
    assert list(m) == [typed(S["program-own-type"], S.MyType)]

    # And a program's own declaration is answered ahead of the engine's,
    # because the table is consulted last. The operation itself is untouched:
    # this asks the ENGINE for the head of an expression, which is the whole
    # point of the claim, where `e[0]` would only ask Python.
    m += typed(S["car-atom"], S.MyOverride)
    assert m.fn("car-atom")(S.a(S.b)) == S.a
    assert kind.all(S["car-atom"]) == [
        S.MyOverride,
        arrow(S.Expression, undefined),
    ]
