"""examples/libraries/he_atomspace.metta in Python: writing, matching and typing atoms.

`add-atom` and `add-reduct` differ in one thing, which the two claims here
draw: add-atom stores the definition as written, and add-reduct reduces the
body to a VALUE first. Python spells the pair with one write door and an
explicit evaluation, which is the composition the ledger asks for rather than a
second method.

Reading them back is matching the space for `(= (addnormal) $X)`, which
`equation(...).to(...)` builds as a pattern the same way it builds an atom, so
the subscript door answers the stored body.

`get-type` is `space.type(atom)` now, the dissolution table's own door, so the
declaration's space is the receiver rather than an argument; and `(: a A)` is
`typed(a, A)`, the declaration as data.

The containment claims are Python's `in`: `(unify &self (hello world) Yes No)`
asks whether anything in the space unifies with a pattern, which is exactly
what `pattern in space` asks, so the twin answers True and False rather than
Yes and No.
"""

from metta import S, V, equation, typed

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Write one definition each way, read both back, then type and unify."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    m += equation(S.addnormal()).to(S["+"](1, 3))
    m += equation(S.addreduct()).to(m.answers(S["+"](1, 3)).one())

    # The stored body, as written.
    assert [row.body for row in m[equation(S.addnormal()).to(V.body)]] == [S["+"](1, 3)]
    # And reduced, because add-reduct's Python spelling evaluates first.
    assert [row.body for row in m[equation(S.addreduct()).to(V.body)]] == [4]

    # A declared type is an ordinary atom, and the space that holds it is the
    # receiver: which space you ask is what decides the answer.
    m += typed(S.a, S.A)
    assert m.type(S.a) == S.A

    # Containment is a match, so it is Python's `in`.
    m += S.hello(S.world)
    assert S.hello(S.world) in m
    assert S.hello(S.dream) not in m
