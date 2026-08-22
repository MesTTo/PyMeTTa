"""examples/data/foldallspacecount.metta in Python: counting by folding ones.

`countitem` answers 1 once per atom the match finds, and folding those ones
with `merge` counts them, so three `foo` facts make 3. The counting is done by
the fold rather than by a length, which is the point: the generator answers
once per row and the aggregator never sees the rows at all.

`countitem` and `spacecount` are written as equations because their bodies are
generator terms: `foldall` is an interpreter form rather than a registered
function, so a compiled body has no name for it, and the match's template
repeats its own pattern, which the compiled match reads as a function call
(both filed as friction). `merge` is an ordinary compiled function.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4892 to 4746, -146 (-2.98%), by the twin-shape
#: rewrite: the `test` wrapper left the engine for `assert`, and `merge` is
#: now compiled BEFORE the `spacecount` equation that names it: the same file
#: with those two statements the other way round measures 5584, so ordering a
#: definition ahead of the equation that mentions it saves 838 inferences.
#: Against the example's 6871 the ratio is 0.6907 [measured 2026-08-22 min-
#: of-3: `twin_coverage.py --measure examples/data/foldallspacecount.metta`].
#: Prior: RE-PINNED at 4892 by the wave-4 idiom rewrite.
BUDGET = 4746


def twin(m):
    """Put three facts in the space, then count them by folding ones."""
    m += S.foo(1)
    m += S.foo(2)
    m += S.foo(3)

    found = S.match(S["&self"], S.foo(V.n), S.foo(V.n))  # rung: the generator reaches foldall as a term, and a term names its space
    m += equation(S.countitem()).to(S.let(V.x, found, 1))  # rung: same clause; the `let` throws the row away and answers one

    @m.define
    def merge(a, b):
        return a + b

    m += equation(S.spacecount(V.x)).to(S.foldall(S.merge, S.countitem(), 0))

    assert m.eval(S.foldall(S.merge, S.countitem(), 0)) == [3]
