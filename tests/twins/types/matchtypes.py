"""Purpose: examples/types/matchtypes.metta in Python: types compared as ordinary atoms.

`match-types` takes two TYPES and two branches and answers one of them. Nothing
about it is special: a type is an atom, `==` compares atoms, and the whole
function is one conditional. `match-type-or` is built on top and answers True
when the two types agree and its own value otherwise.

Both clauses are written at the container door, because the definitional
decorator refuses a name the space already answers, `match-types` among them,
and stacking a clause onto an existing definition is exactly what the original
does. The bodies are terms for the same reason, which is why the `==` is named
rather than written as Python's own, while `if_` is the keyword builder for a
stored `if`.
"""

from metta import FALSE, TRUE, S, V, equation, if_

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Define the two functions, then compare four pairs of types."""
    matched, either = S["match-types"], S["match-type-or"]

    m += equation(matched(V.A, V.B, V.Then, V.Else)).to(
        if_(V.A.eq(V.B), V.Then, V.Else)
    )
    m += equation(either(V.value, V.type1, V.type2)).to(
        matched(V.type1, V.type2, TRUE, V.value)
    )

    assert m.fn.match_types(S.Atom, S.Atom, S.yes, S.no) == [S.yes]
    assert m.fn.match_types(S.Atom, S.Number, S.yes, S.no) == [S.no]

    # The two types agree, so the value never gets a say; when they differ it
    # is the answer.
    assert m.fn.match_type_or(TRUE, S.Number, S.Number) == [True]
    assert m.fn.match_type_or(FALSE, S.Number, S.Number) == [True]
    assert m.fn.match_type_or(TRUE, S.Number, S.Bool) == [True]
    assert m.fn.match_type_or(FALSE, S.Number, S.Bool) == [False]
