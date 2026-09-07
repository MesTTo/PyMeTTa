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
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 10702
