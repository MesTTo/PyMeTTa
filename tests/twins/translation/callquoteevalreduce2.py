"""examples/translation/callquoteevalreduce2.metta in Python: four ways to not reduce.

One inner term, `(fib (myfunc))`, under four wrappers. `call` and `eval` and
`reduce` all get to 5; `quote` holds the term as it was written. Each claim
wraps the answer in a symbol of its own so the comparison sees what came back
rather than what it would reduce to next.

`fib` and `myfunc` are ordinary compiled definitions. The four wrappers are
terms: their names carry hyphens, which a compiled body resolves exactly as
written, and `call` and `quote` are translator forms rather than registry
functions, so `is_function` answers False for both (residue, P14.4).
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13558 to 11859, -1699 (-12.5%), by the twin contract
#: change: four `(test ...)` terms became four Python `assert`s, so the `test`
#: wrapper left the engine four times while the six definitions and the four
#: evaluations over them stayed in it. Against the example's 17576 the ratio is
#: 0.6747.
#: Prior: 13558, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 11859


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

    assert m.one(S["fib-call"](S["call-fib"]())) == S["fib-call"](5)
    # quote keeps its wrapper AND the term under it, unreduced.
    assert m.one(S["fib-quote"](S["quote-fib"]())) == S["fib-quote"](S.quote(inner))
    assert m.one(S["fib-eval"](S["eval-fib"]())) == S["fib-eval"](5)
    assert m.one(S["fib-reduce"](S["reduce-fib"]())) == S["fib-reduce"](5)
