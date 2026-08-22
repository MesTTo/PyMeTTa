"""examples/types/matchtypes.metta in Python: types compared as ordinary atoms.

`match-types` takes two TYPES and two branches and answers one of them. Nothing
about it is special: a type is an atom, `==` compares atoms, and the whole
function is one conditional. `match-type-or` is built on top and answers True
when the two types agree and its own value otherwise.

Both clauses are written at the container door, because the definitional
decorator refuses a name the space already answers, `match-types` among them,
and stacking a clause onto an existing definition is exactly what the original
does. The bodies are terms for the same reason, which is why the `if` and the
`==` are named rather than written as Python's own.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 7492 to 4378, -3114 (-41.56%), by the twin-shape
#: rewrite: the four `test` wrappers left the engine for `assert`; the two
#: stacked clauses and the six calls over them are all that is left. Against
#: the example's 13774 the ratio is 0.3178 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/types/matchtypes.metta`]. Prior: RE-
#: PINNED at 7492 by P14.8's m.eval fuel-scope alignment.
BUDGET = 4378


def twin(m):
    """Define the two functions, then compare four pairs of types."""
    m += equation(S["match-types"](V.A, V.B, V.Then, V.Else)).to(
        S["if"](V.A.eq(V.B), V.Then, V.Else)  # rung: the clause is a built term, so its `if` is one too (P14.4)
    )
    m += equation(S["match-type-or"](V.value, V.type1, V.type2)).to(
        S["match-types"](V.type1, V.type2, True, V.value)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    )

    matched = m.fn("match-types")
    assert matched(S.Atom, S.Atom, S.yes, S.no) == S.yes
    assert matched(S.Atom, S.Number, S.yes, S.no) == S.no

    # The two types agree, so the value never gets a say; when they differ it
    # is the answer.
    assert m.fn("match-type-or")(True, S.Number, S.Number) is True  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert m.fn("match-type-or")(False, S.Number, S.Number) is True  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert m.fn("match-type-or")(True, S.Number, S.Bool) is True  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert m.fn("match-type-or")(False, S.Number, S.Bool) is False  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
