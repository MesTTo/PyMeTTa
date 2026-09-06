"""Purpose: mirror safe held deconstruction in examples/ch08-data/08-01-atoms-lists-and-folds/16-if_decons_expr.metta.

Python starred unpacking binds an expression's first item and remaining items.
The native call binds the first item and remaining expression,
then evaluates its selected branch. Empty or unbound operands choose fallback.
Already-bound head and tail positions act as constraints. A known wrong type
produces an Error answer through the same engine contract as other builtins.
"""

from metta import Expression, S, V


def twin(m):
    """Exercise binding, fallback, held inputs and selected-branch answers."""
    deconstruct = m.fn.if_decons_expr
    h, t = V.h, V.t
    pair = S.pair(h, t)
    fallback = S.fallback

    head, *tail = Expression(S.a, S.b, S.c)
    assert S.pair(head, Expression(tail)) == S.pair(S.a, Expression(S.b, S.c))
    assert deconstruct(Expression(), h, t, pair, fallback) == [fallback]
    assert deconstruct(V.unknown, h, t, pair, fallback) == [fallback]
    assert deconstruct(S['+'](1, 2), h, t, t, fallback) == [Expression(1, 2)]
    assert deconstruct(Expression(1, 2), h, t, S['+'](h, 10), S['/'](1, 0)) == [11]
    assert deconstruct(Expression(S.a, S.b), S.a, Expression(S.b), S.matched, fallback) == [S.matched]
    assert deconstruct(Expression(S.a, S.b), S.wrong, Expression(S.b), S.matched, fallback) == [fallback]
    assert deconstruct(Expression(S.a, S.b), S.a, Expression(), S.matched, fallback) == [fallback]
    assert deconstruct(Expression(S.a, S.b), h, t, S.superpose(Expression(1, 2, 2)), fallback) == [1, 2, 2]
    assert m.eval(S.if_error(
        S.if_decons_expr(42, h, t, S.yes, fallback), S.refused, S.answered,
    )) == [S.refused]


#: The final image includes the provisioned engine and MORK artifacts.
#: [measured: 16981, 16981, 16981 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-01-atoms-lists-and-folds/16-if_decons_expr.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
#: RE-PINNED 2026-09-06, 16981 to 17036 (+55), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 17036
