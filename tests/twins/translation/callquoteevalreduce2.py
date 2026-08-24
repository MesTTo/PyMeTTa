"""examples/translation/callquoteevalreduce2.metta in Python: four ways to not reduce.

One inner term, `(fib (myfunc))`, under four wrappers. `call`, `eval` and
`reduce` all get to 5; `quote` holds the term as it was written. Each claim
wraps the answer in a symbol of its own so the comparison sees what came back
rather than what it would reduce to next.

Everything here compiles. `fib` and `myfunc` are ordinary functions, and the
four wrappers are ordinary functions whose bodies mention a translator form:
`call`, `quote`, `eval` and `reduce` are forms the compiler reads rather than
functions the catalog holds, so a body names them at the `S` door and hands
them a call built out of the two Python names beside it.

The outer wrappers in the claims are not functions at all. `fib-call` has no
equation, so evaluating `(fib-call (call-fib))` reduces what is inside it and
leaves the wrapper standing, which is exactly what the claim is measuring; that
makes each one a term to evaluate rather than a call to make.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
BUDGET = 1


def twin(m):
    """Wrap one term four ways, and see which of them reduce."""

    @m.define
    def fib(n):                          # (= (fib $N) (if (< $N 2) $N
        if n < 2:                        #     (+ (fib (- $N 1)) (fib (- $N 2)))))
            return n
        return fib(n - 1) + fib(n - 2)

    @m.define
    def myfunc():                        # (= (myfunc) 5)
        return 5

    @m.define
    def call_fib():                      # (= (call-fib) (call (fib (myfunc))))
        return S.call(fib(myfunc()))

    @m.define
    def quote_fib():                     # (= (quote-fib) (quote (fib (myfunc))))
        return S.quote(fib(myfunc()))

    @m.define
    def eval_fib():                      # (= (eval-fib) (eval (fib (myfunc))))
        return S.eval(fib(myfunc()))

    @m.define
    def reduce_fib():                    # (= (reduce-fib) (reduce (fib (myfunc))))
        return S.reduce(fib(myfunc()))

    inner = S.fib(S.myfunc())
    assert m.answers(S["fib-call"](S["call-fib"]())).one() == S["fib-call"](5)
    # quote keeps its wrapper AND the term under it, unreduced.
    assert m.answers(S["fib-quote"](S["quote-fib"]())).one() == S["fib-quote"](S.quote(inner))
    assert m.answers(S["fib-eval"](S["eval-fib"]())).one() == S["fib-eval"](5)
    assert m.answers(S["fib-reduce"](S["reduce-fib"]())).one() == S["fib-reduce"](5)
