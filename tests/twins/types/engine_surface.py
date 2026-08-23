"""Purpose: examples/types/engine_surface.metta in Python: the engine's own type surface.

Nothing is imported here. The engine reads its own declarations at boot and
consults them LAST, so `get-type` answers for a special form, a structure
operation or the state cell while the program's space stays the program's own.
This twin asks all of them through `space.type(atom)`, the get-type accessor,
and builds every expected arrow from PYTHON TYPES: `Atom`, `Variable` and
`Expression` are the metatype classes, `int`, `bool` and `str` are Number, Bool
and String, and `Any` is `%Undefined%`, all through the one conversion table.

Two things it also shows. The declarations are FACTS the engine holds, not
atoms in the program's space, so iterating that space finds only what the
program itself declared. And a program's own declaration is answered AHEAD of
the engine's, without taking the operation away: after `(: car-atom MyOverride)`
the builtin still answers, and `get-type` answers both.
"""

from typing import Any

from petta import Atom, Expression, S, V, Variable, arrow, fn, ground, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Read the engine's declared types, then overlay one of them."""
    # Special forms are compiled by the translator and have no registry entry,
    # so they were the least reachable half of the surface.
    assert m.type(fn["if"]).alpha_eq(arrow(bool, Atom, Atom, V.t))
    assert m.type(fn.let) == arrow(Atom, Any, Atom, Any)
    assert m.type(fn.chain) == arrow(Atom, Variable, Atom, Any)
    assert m.type(fn.quote) == arrow(Atom, Atom)
    assert m.type(fn.collapse) == arrow(Atom, Atom)
    assert m.type(fn.superpose) == arrow(Expression, Any)
    assert m.type(fn.match) == arrow(S.SpaceType, Atom, Atom, Any)
    assert m.type(fn.map_atom) == arrow(Expression, Variable, Atom, Expression)

    # Expression structure, from the reference corelib dump.
    assert m.type(fn.car_atom) == arrow(Expression, Any)
    assert m.type(fn.cdr_atom) == arrow(Expression, Expression)
    assert m.type(fn.cons_atom) == arrow(Atom, Expression, Atom)
    assert m.type(fn.size_atom) == arrow(Expression, int)
    assert m.type(fn.index_atom) == arrow(Expression, int, Atom)

    # PeTTa's own, with no dump entry to take.
    assert m.type(fn.sort_atom) == arrow(Expression, Expression)
    assert m.type(fn.is_var) == arrow(Atom, bool)
    assert m.type(fn.repr) == arrow(Atom, str)
    assert m.type(fn.current_time) == arrow(int)

    # The state cell is a VALUE and its type says what it holds.
    cell = S.StateMonad
    assert m.type(fn.new_state).alpha_eq(arrow(V.t, cell(V.t)))
    assert m.type(fn.change_state).alpha_eq(arrow(cell(V.t), V.t, cell(V.t)))
    assert m.type(fn.get_state).alpha_eq(arrow(cell(V.t), V.t))
    assert m.type(fn.new_state(5)) == cell(S.Number)
    assert m.type(fn.new_state(ground("hi"))) == cell(S.String)

    # The surface is FACTS, not atoms in the program's space: a program still
    # sees only its own declarations when it enumerates them, which is what
    # iterating a space is for. The subscript door would be the other spelling
    # and it reads a wholly-variable `(: $n $t)` as an annotation rather than
    # as data, where the engine's own match keeps it structural (friction).
    m += typed(S["program-own-type"], S.MyType)
    assert list(m) == [typed(S["program-own-type"], S.MyType)]

    # And a program's own declaration is answered ahead of the engine's,
    # because the table is consulted last. The operation itself is untouched:
    # this asks the ENGINE for the head of an expression, which is the whole
    # point of the claim, where `e[0]` would only ask Python.
    m += typed(fn.car_atom, S.MyOverride)
    assert m.fn.car_atom(S.a(S.b)) == [S.a]
    assert m.fn.get_type(fn.car_atom) == [S.MyOverride, arrow(Expression, Any)]
