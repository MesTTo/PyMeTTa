"""examples/spaces/state.metta in Python: a state cell is a value.

`new-state` answers a cell, `get-state` reads it, and `change-state!` answers
the CELL it wrote, so a write composes with a read in one expression. The
original's `bind!` is the concept Python spells with `=`, so the name below is
an ordinary Python variable and the cross-form ceremony the earlier twin needed
is gone.

The three cell operations reach the engine through `m.fn`, which is the door
for an engine function as an ordinary Python callable, and `get-type` reaches
it the same way: the space handle's `type` is the class-declaration decorator,
so `space.type(atom)` is not yet the get-type accessor the ledger names
(residue, P14.10).
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3971 to 1211, -2760 (-69.5%), by the twin contract
#: change: six `(test ...)` terms became six Python `assert`s, so the `test`
#: wrapper left the engine while every cell operation and both `get-type`
#: questions stayed in it. Against the example's 8879 the ratio is 0.1364.
#: Prior: 3971, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 1211


def twin(m):
    """Make a cell, read it, write through it, and ask what it holds."""
    cell, read, write = m.fn("new-state"), m.fn("get-state"), m.fn("change-state!")
    kind = m.fn("get-type")

    # !(bind! state (new-state rest)): binding a name to the cell is Python's
    # own name binding, which is why the two spellings below read alike.
    state = cell(S.rest)
    assert read(state) == S.rest
    assert read(write(state, S.active)) == S.active
    assert read(state) == S.active

    # The type says what the cell HOLDS, which is upstream's own signature
    # (: new-state (-> $t (StateMonad $t))).
    assert kind(cell(5)) == S.StateMonad(S.Number)
    assert kind(cell(val("hi"))) == S.StateMonad(S.String)

    # And a cell needs no name at all: built, written and read in place.
    assert read(write(cell(1), 2)) == 2
