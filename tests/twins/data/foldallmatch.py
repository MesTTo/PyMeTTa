"""examples/data/foldallmatch.metta in Python: folding a match, and a let.

Both claims fold something that answers more than once. The first generator is
a MATCH over the space, and the second is a `let` over a two-clause function.
Neither can be run in Python first: `foldall` reads its generator as a term and
enumerates it itself, so handing it a list of rows the subscript door already
collected would fold a value rather than a generator.

The template is where the arithmetic happens, `(+ $n 1)` per row, so the fold
sees 2 and 3 and answers 5.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5583 to 3920, -1663 (-29.79%), by the twin-shape
#: rewrite: the two `test` wrappers left the engine for `assert`, and `f`
#: moved from one compiled generator to the TWO stored equations the original
#: writes. Nothing else in this file is compiled, so that generator was
#: paying the compiler's one-time warm-up alone: the same file with it
#: measures 5291. Against the example's 6828 the ratio is 0.5741 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/foldallmatch.metta`]. Prior: RE-PINNED at 5583 by the wave-4
#: idiom rewrite.
BUDGET = 3920


def twin(m):
    """Fold a query's rows, then fold a function's two answers."""
    m += S.kb(1)
    m += S.kb(2)
    m += equation(S.f()).to(1)
    m += equation(S.f()).to(2)

    rows = S.match(S["&self"], S.kb(V.n), V.n + 1)  # rung: foldall enumerates its generator itself, so the match stays a term, and a term names its space
    assert m.eval(S.foldall(S["+"], rows, 0)) == [5]

    answers = S.let(V.x, S.f(), 1 + V.x)  # rung: the same reason, and this `let` is inside the generator rather than around it
    assert m.eval(S.foldall(S["+"], answers, 0)) == [5]
