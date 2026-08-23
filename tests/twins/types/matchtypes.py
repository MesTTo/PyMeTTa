"""Purpose: examples/types/matchtypes.metta in Python: types compared as ordinary atoms.

`match-types` takes two TYPES and two branches and answers one of them. Nothing
about it is special: a type is an atom, `==` compares atoms, and the whole
function is one conditional. `match-type-or` is built on top and answers True
when the two types agree and its own value otherwise.

Both are `@m.rules` equations rather than `@m.define` functions, because this
engine already answers both names (`match-types` at arity 5, `match-type-or` at
arity 3) and the definitional decorator refuses a name the space answers.
`@m.rules` is the door that lands bare coexisting equations deliberately, the
parameters ARE the equations' variables, and a rules body EXECUTES, so its
terms are built rather than lowered.

The equality is therefore built by its WORD, `S.eq(a, b)` for `(== $A $B)`,
where Python's own `==` between two atoms is a structural test that answers a
bool. `if_` is the keyword builder for a stored `if`, and it takes the arity
the engine's `if` has.
"""

from metta import FALSE, TRUE, S, equation, if_

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Define the two functions, then compare four pairs of types."""

    @m.rules
    def comparison(left, right, then, otherwise, value):
        """The example's two equations, over five shared rule variables."""
        # (= (match-types $A $B $Then $Else) (if (== $A $B) $Then $Else))
        yield equation(S.match_types(left, right, then, otherwise)).to(
            if_(S.eq(left, right), then, otherwise)
        )
        # (= (match-type-or $value $type1 $type2)
        #    (match-types $type1 $type2 True $value))
        yield equation(S.match_type_or(value, left, right)).to(
            S.match_types(left, right, TRUE, value)
        )

    # !(match-types Atom Atom "Matched!" "Didn't match")
    assert m.fn.match_types(S.Atom, S.Atom, S.yes, S.no) == [S.yes]
    # !(match-types Atom Number "Matched!" "Didn't match")
    assert m.fn.match_types(S.Atom, S.Number, S.yes, S.no) == [S.no]

    # The two types agree, so the value never gets a say; when they differ it
    # is the answer.
    # !(test (match-type-or True Number Number) True)
    assert m.fn.match_type_or(TRUE, S.Number, S.Number) == [True]
    # !(test (match-type-or False Number Number) True)
    assert m.fn.match_type_or(FALSE, S.Number, S.Number) == [True]
    # !(test (match-type-or True Number Bool) True)
    assert m.fn.match_type_or(TRUE, S.Number, S.Bool) == [True]
    # !(test (match-type-or False Number Bool) False)
    assert m.fn.match_type_or(FALSE, S.Number, S.Bool) == [False]
