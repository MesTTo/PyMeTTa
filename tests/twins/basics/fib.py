"""examples/basics/fib.metta in Python: the exponential fib, budgeted.

The naive fib is one Python function and the engine runs it as equations. The
deliberately exponential tree exceeds the evaluator's default branch-local
fuel, so the bound is raised first and the call is then an ordinary call.

`m.limits(...)` is the Python door for a scoped bound, but it carries
`timeout` and `inferences` only, so the stack-depth bound is set through
`pragma!` as the atom it is. The residue table records the missing kwarg
against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Raise the branch bound, then run the exponential fib."""
    @m.define
    def fib(n):
        # (= (fib $N) (if (< $N 2) $N (+ (fib (- $N 1)) (fib (- $N 2)))))
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    # (with-pragma! ((max-stack-depth 100000000)) ...) scopes the same bound
    # to one expression; there is no kwarg for it on m.limits.
    m.eval(S["pragma!"](S["max-stack-depth"], 100000000))

    assert fib(30) == [832040]
