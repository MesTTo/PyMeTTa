"""examples/ch08-data/08-03-the-shipped-libraries/14-reflect_lib.metta in Python: the engine's own surface as data.

Every enumeration answers a name per solution, so a Python list IS the
collapse and `len` is the count. The `engine-` predicates under the MeTTa
names are the same operations, and the claims that pair them are what says
so.

`surface-counts` moves as libraries are imported, so what is pinned here is
the SHAPE rather than the numbers.

An extension point's name keeps its underscore, `foreign_space`, so that one
comes through the exact subscript door where every other name here takes the
host-convention map.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib


def twin(m):
    """Ask what the engine knows, where a name came from, and how many."""
    m += lib.reflect

    @m.define
    def mine(x):
        # (= (mine $x) $x)
        return x

    knows, arity = m.fn["knows?"], m.fn["arity-of"]
    origin = m.fn["origin-of"]

    assert knows(S.car_atom) == [True]
    assert knows(S.mine) == [True]
    assert knows(S.no_such_name_anywhere) == [False]

    # A registered arity counts the ANSWER position, so `car-atom` takes one
    # argument and is registered at 2.
    assert arity(S.car_atom) == [2]
    assert arity(S.cons_atom) == [3]
    assert arity(S.no_such_name_anywhere) == []

    # Where a name comes from, which a flat list of names cannot say.
    assert origin(S.car_atom) == [(S.builtin,)]
    assert origin(S.mine)[0][0] == S.equation
    assert origin(S.case) == [(S.special_form,)]

    # The four enumerations. `special-forms` is what the translator COMPILES
    # and so appears in no registry.
    builtins, special = m.fn["builtins"], m.fn["special-forms"]
    functions, mine_only = m.fn["functions"], m.fn["user-functions"]
    assert len(builtins()) > 100
    assert len(special()) > 10
    assert S.mine in mine_only()
    assert S.car_atom not in mine_only()
    assert S.car_atom in functions()
    assert S.case not in builtins()
    assert S.case in special()
    # `let` is in BOTH, which is what a name with a registered implementation
    # and a compiled form looks like.
    assert S.let in builtins()
    assert S.let in special()

    # The seam catalogue, one (name arity kind) per point.
    points = m.fn["extension-points"]
    assert len(points()) > 3
    assert S["foreign_space"](1, S.ownership) in points()

    # The cheap health check: four pairs rather than four enumerations.
    counts = m.fn["surface-counts"]()[0]
    assert len(counts) == 4
    assert counts[0][0] == S.builtins

    # The whole thing as JSON, which is what an outside tool consumes.
    surface = str(m.fn["surface-json"]()[0].value)
    assert len(surface) > 1000
    assert surface[0] == "{"

    # Every name above has a Prolog rung under it, and the MeTTa name is one
    # equation over it.
    assert m.fn["engine-arity"](S.car_atom) == arity(S.car_atom)
    assert m.fn["engine-knows"](S.car_atom) == [True]
    assert m.fn["engine-knows"](S.no_such_name_anywhere) == [False]
    assert m.fn["engine-origin"](S.car_atom) == [(S.builtin,)]
    assert m.fn["engine-surface-counts"]() == m.fn["surface-counts"]()
    assert len(m.fn["engine-builtin"]()) == len(builtins())
    assert len(m.fn["engine-special-form"]()) == len(special())
    assert len(m.fn["engine-function"]()) == len(functions())
    assert len(m.fn["engine-user-function"]()) == len(mine_only())
    assert len(m.fn["engine-extension-point"]()) == len(points())


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 161415 inferences, 1.0621x the example's 151980; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 161415
