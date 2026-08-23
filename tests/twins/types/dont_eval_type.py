"""Purpose: examples/types/dont_eval_type.metta in Python: a user-declared lazy type.

`DontEvalType` is a kind of type, and a parameter declared with a type of that
kind receives its argument BEFORE evaluation. So `inspect-opaque` sees the term
`(+ 1 2)` rather than 3, and reports its metatype, Expression.

The clause is written at the container door for one reason: its body is
`get-metatype`, and a compiled body has no name for it. Python's own `type()`
is the metatype accessor out here, where the atom is already in hand, and the
last line says so by asking both sides about the same term.
"""

from petta import Expression, S, V, arrow, equation, fn, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Declare the lazy type, then read what the body was handed."""
    sum_term = S["+"](1, 2)

    m += typed(S.OpaquePayload, S.DontEvalType)
    m += typed(S["inspect-opaque"], arrow(S.OpaquePayload, S.Symbol))
    m += equation(S["inspect-opaque"](V.written)).to(fn.get_metatype(V.written))

    assert m.fn.inspect_opaque(sum_term) == [S.Expression]
    assert type(sum_term) is Expression
