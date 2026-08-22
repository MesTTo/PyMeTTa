"""examples/libraries/he_atomspace.metta in Python: writing, matching and typing atoms.

`add-atom` and `add-reduct` differ in one thing, which the two claims here
draw: add-atom stores the definition as written, and add-reduct reduces the
body to a VALUE first. Python spells the pair with one write door and an
explicit evaluation, which is the composition the ledger asks for rather than a
second method.

Reading them back is matching the space for `(= (addnormal) $X)`, which
`equation(...).to(...)` builds as a pattern the same way it builds an atom, so
the subscript door answers the stored body.

The containment claims are Python's `in`: `(unify &self (hello world) Yes No)`
asks whether anything in the space unifies with a pattern, which is exactly
what `pattern in space` asks, so the twin answers True and False rather than
Yes and No.

`get-type-space` stays named. The dissolution table's `space.type(atom)` is not
on the handle (`type` there is the class-declaration decorator), which the
residue table records.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11625 to 8389, -3236 (-27.84%), by the idiomatic
#: rewrite: the two `match` forms, their `collapse`s and the two `unify`
#: calls left the engine for the subscript door and Python's `in`, and add-
#: reduct's reduction is now one evaluation whose answer Python hands back to
#: the write door. Measured min-of-three with the MORK backend linked into
#: this worktree, which the earlier figure may not have been. Prior: 11625
#: was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 8389


def twin(m):
    """Write one definition each way, read both back, then type and unify."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += equation(S.addnormal()).to(S["+"](1, 3))
    m += equation(S.addreduct()).to(m.one(S["+"](1, 3)))

    # The stored body, as written.
    assert m[equation(S.addnormal()).to(V.body)]["body"] == [S["+"](1, 3)]
    # And reduced, because add-reduct's Python spelling evaluates first.
    assert m[equation(S.addreduct()).to(V.body)]["body"] == [4]

    # A declared type is an ordinary atom, and asking for it names the space,
    # because the answer depends on which space you ask.
    m += S[":"](S.a, S.A)
    assert m.fn("get-type-space")(S["&self"], S.a) == S.A  # rung: the queried space is this function's ARGUMENT; the dissolution table's space.type(atom) is not on the handle, so the space is named

    # Containment is a match, so it is Python's `in`.
    m += S.hello(S.world)
    assert S.hello(S.world) in m
    assert S.hello(S.dream) not in m
