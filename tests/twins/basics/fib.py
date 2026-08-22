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
#: RE-PINNED 2026-08-22, 28278972 to 28278228, -744 (-0.0%), by the twin
#: contract change: the `test` wrapper left the engine for `assert` and
#: `with-pragma!` became a process-wide `pragma!` beside the call; 28.2
#: million of the 28.3 are the exponential tree itself, so the shape of the
#: twin is worth 0.003%. Against the example's 28280157 the ratio is 0.9999
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 28278228


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
