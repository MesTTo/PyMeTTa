"""examples/ch09-types/20-type_casts_that_hold.metta in Python: the Bool a cast decides on.

`type-cast-holds` answers whether any declared type of an atom, in a space,
unifies with the one asked about. It takes the space as an argument, so the
twin hands it the handle rather than naming a space as text.

The declarations are the `m.declare` door and the definition is an ordinary
compiled one, so the two spaces below hold what the original's `(: ...)` rows
and `(= ...)` hold.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, arrow, if_, typed


def twin(m):
    """Ask the question, then ask the operation that enforces it."""
    holds = m.fn["type-cast-holds"]
    cast = m.fn["type-cast"]

    m += typed(S.five, S.Number)
    m += typed(S.greeting, S.String)

    @m.define
    def twice(x: int) -> int:
        # (= (twice $x) (* 2 $x))
        return 2 * x

    # A declared symbol holds its own type and nothing else.
    assert holds(S.five, S.Number, m) == [True]
    assert holds(S.five, S.Bool, m) == [False]
    assert holds(S.greeting, S.String, m) == [True]

    # A literal carries its type without a declaration.
    assert holds(1, S.Number, m) == [True]
    assert holds(G_TEXT, S.String, m) == [True]
    assert holds(1, S.String, m) == [False]

    # An arrow is a type like any other.
    assert holds(S.twice, arrow(S.Number, S.Number), m) == [True]
    assert holds(S.twice, arrow(S.String, S.String), m) == [False]

    # `%Undefined%` unifies with everything, which is what makes it the
    # gradual default rather than a type.
    assert holds(S.five, S["%Undefined%"], m) == [True]
    assert holds(S.undeclared_name, S.Number, m) == [True]
    assert holds(S.undeclared_name, S.String, m) == [True]

    # The space is the context the declarations are read from, so the same
    # atom answers differently in two spaces.
    other = m.metta.space(S.other)
    other += typed(S.five, S.String)
    assert holds(S.five, S.String, other) == [True]
    assert holds(S.five, S.String, m) == [False]

    # `type-cast` is this question with the atom or an error as its answer.
    assert cast(1, S.Number, m) == [1]
    assert cast(S.five, S.Bool, m) == [S.Error(S.five, S.BadType)]
    assert m.answers(if_(holds(S.five, S.Bool, m)[0], S.yes, S.no)) == [S.no]


from metta import G  # noqa: E402  -- the one string this file compares, as data

G_TEXT = G("text")


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 10702 inferences, 0.8564x the example's 12496; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 10702 to 10723 (+21), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
BUDGET = 10723
