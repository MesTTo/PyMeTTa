"""examples/data/nestedcons.metta in Python: two cons cells in one head.

`(cons $a (cons $b $L))` takes an expression apart twice over and answers the
second element. The head is nested structure, which a compiled parameter list
cannot spell, so the clause is written as the equation it is; the call then
reads `(a b c d)` as head `a`, then `(b c d)` as head `b`, and answers `b`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1252 to 1124, -128 (-10.22%), by the twin-shape
#: rewrite: the `test` wrapper left the engine for `assert`; the doubly-
#: nested clause and the one call over it are unchanged. Against the
#: example's 2778 the ratio is 0.4046 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/data/nestedcons.metta`]. Prior: the
#: file's first pin, uncommented.
BUDGET = 1124


def twin(m):
    """Define the doubly-nested clause and take the second element with it."""
    m += equation(S.f(S.cons(V.a, S.cons(V.b, V.L)))).to(V.b)

    assert m.fn("f")(S.a(S.b, S.c, S.d)) == S.b
