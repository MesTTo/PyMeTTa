"""examples/data/foldallspacecount.metta in Python: counting by folding ones.

`countitem` answers 1 once per atom the match finds, and folding those ones
with `merge` counts them, so three `foo` facts make 3. The counting is done by
the fold rather than by a length, which is the point: the generator answers
once per row and the aggregator never sees the rows at all.

`countitem` and `spacecount` are written as equations because their bodies are
generator terms: `foldall` is an interpreter form rather than a registered
function, so a compiled body has no name for it, and the match's template
repeats its own pattern, which the compiled match reads as a function call
(both filed as friction). `merge` is an ordinary compiled function. The space inside the match term
is the handle itself, which crosses into a built term as a grounded operand.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Put three facts in the space, then count them by folding ones."""
    m += S.foo(1)
    m += S.foo(2)
    m += S.foo(3)

    found = S.match(m, S.foo(V.n), S.foo(V.n))  # rung: the generator reaches foldall as a term, and the space crosses into it as a handle
    m += equation(S.countitem()).to(S.let(V.x, found, 1))  # rung: same clause; the `let` throws the row away and answers one

    @m.define
    def merge(a, b):
        return a + b

    m += equation(S.spacecount(V.x)).to(S.foldall(S.merge, S.countitem(), 0))

    assert m.fn.foldall(S.merge, S.countitem(), 0).one() == 3
