"""examples/types/dont_eval_type.metta in Python: a user-declared lazy type.

`DontEvalType` is a kind of type, and a parameter declared with a type of that
kind receives its argument BEFORE evaluation. So `inspect-opaque` sees the term
`(+ 1 2)` rather than 3, and reports its metatype, Expression.

The clause is written at the container door for one reason: its body is
`get-metatype`, and a compiled body has no name for it. Python's own `type()`
is the metatype accessor out here, where the atom is already in hand, and the
last line says so by asking both sides about the same term.
"""

from petta import Expr, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1544 to 1412, -132 (-8.55%), by the twin-shape
#: rewrite: the `test` wrapper left the engine for `assert`, and the claim
#: gained a Python-side half, `type(term) is Expr`, which asks no engine at
#: all. Against the example's 4840 the ratio is 0.2917 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure
#: examples/types/dont_eval_type.metta`]. Prior: RE-PINNED at 1544 by P14.8's
#: m.eval fuel-scope alignment.
BUDGET = 1412


def twin(m):
    """Declare the lazy type, then read what the body was handed."""
    typed, arrow = S[":"], S["->"]
    sum_term = S["+"](1, 2)

    m += typed(S.OpaquePayload, S.DontEvalType)
    m += typed(S["inspect-opaque"], arrow(S.OpaquePayload, S.Symbol))
    m += equation(S["inspect-opaque"](V.written)).to(S["get-metatype"](V.written))

    assert m.fn("inspect-opaque")(sum_term) == S.Expression
    assert type(sum_term) is Expr
