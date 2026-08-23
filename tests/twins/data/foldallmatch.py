"""examples/data/foldallmatch.metta in Python: folding a match, and a let.

Both claims fold something that answers more than once. The first generator is
a MATCH over the space, and the second is a `let` over a two-clause function.
Neither can be run in Python first: `foldall` reads its generator as a term and
enumerates it itself, so handing it a list of rows the subscript door already
collected would fold a value rather than a generator.

The space inside that term is the HANDLE itself, not its name written as a
symbol: a space is a grounded operand, so `m` crosses into a built term the
way any other value does.

The template is where the arithmetic happens, `(+ $n 1)` per row, so the fold
sees 2 and 3 and answers 5.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Fold a query's rows, then fold a function's two answers."""
    m += S.kb(1)
    m += S.kb(2)
    m += equation(S.f()).to(1)
    m += equation(S.f()).to(2)

    rows = S.match(m, S.kb(V.n), V.n + 1)  # rung: foldall enumerates its generator itself, so the match stays a term
    assert m.eval(S.foldall(S["+"], rows, 0)) == [5]

    answers = S.let(V.x, S.f(), 1 + V.x)  # rung: the same reason, and this `let` is inside the generator rather than around it
    assert m.eval(S.foldall(S["+"], answers, 0)) == [5]
