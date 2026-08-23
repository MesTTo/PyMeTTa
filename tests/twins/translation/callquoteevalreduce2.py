"""examples/translation/callquoteevalreduce2.metta in Python: four ways to not reduce.

One inner term, `(fib (myfunc))`, under four wrappers. `call` and `eval` and
`reduce` all get to 5; `quote` holds the term as it was written. Each claim
wraps the answer in a symbol of its own so the comparison sees what came back
rather than what it would reduce to next. That wrapper is not a function, so
the whole claim is one term handed to `m.answers`, whose `one()` is the
cardinality door.

`fib` and `myfunc` are ordinary compiled definitions. The four wrappers are
terms: their names carry hyphens, which a compiled body resolves exactly as
written, and `call` and `quote` are translator forms rather than registry
functions, so `is_function` answers False for both (residue, P14.4).
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Wrap one term four ways, and see which of them reduce."""

    @m.define
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    @m.define
    def myfunc():
        return 5

    inner = S.fib(S.myfunc())
    m += equation(S["call-fib"]()).to(S.call(inner))
    m += equation(S["quote-fib"]()).to(S.quote(inner))
    m += equation(S["eval-fib"]()).to(S.eval(inner))
    m += equation(S["reduce-fib"]()).to(S.reduce(inner))

    assert m.answers(S["fib-call"](S["call-fib"]())).one() == S["fib-call"](5)
    # quote keeps its wrapper AND the term under it, unreduced.
    assert m.answers(S["fib-quote"](S["quote-fib"]())).one() == S["fib-quote"](S.quote(inner))
    assert m.answers(S["fib-eval"](S["eval-fib"]())).one() == S["fib-eval"](5)
    assert m.answers(S["fib-reduce"](S["reduce-fib"]())).one() == S["fib-reduce"](5)
