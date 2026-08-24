"""examples/basics/fib.metta in Python: the exponential fib, budgeted.

The naive fib is one Python function and the engine runs it as equations. The
deliberately exponential tree exceeds the evaluator's default branch-local
fuel, so the bound is raised first and the call is then an ordinary call.

The static settings tuple and `m.fn.with_pragma` preserve the source's scoped
`with-pragma!` boundary, including restoration after the call.
"""

from metta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Raise the branch bound, then run the exponential fib."""
    @m.define
    def fib(n):
        # (= (fib $N) (if (< $N 2) $N (+ (fib (- $N 1)) (fib (- $N 2)))))
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    raised_stack = ((S.max_stack_depth, 100_000_000),)
    assert m.fn.with_pragma(raised_stack, S.fib(30)) == [832040]
