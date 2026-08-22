"""The Python twin of examples/translation/callquoteevalreduce2.metta.

Four wrappers around the same call, differing only in which evaluation-control
symbol they put in front of it, and the four answers are what the example
teaches: `call` and `eval` and `reduce` all answer 5, and `quote` answers the
term itself, unevaluated.

`fib` and `myfunc` are computations and are written as ones. `eval-fib` and
`reduce-fib` are computations too: `eval` and `reduce` are functions the
engine knows under exactly those names, so a compiled body reaches them and
`@m.define(name=...)` gives each equation its hyphenated MeTTa name.

`call-fib` and `quote-fib` drop to the container door for the reason that
asymmetry documents: `call` and `quote` are interpreter forms rather than
functions the engine knows, so a compiled body refuses their names, and the
residue table records that against P14.4.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10973 to 13558, +2585 (+23.56%), by the wave-4 idiom
#: rewrite moving `fib`, `myfunc`, `eval-fib` and `reduce-fib` onto @m.define.
#: COMPILING a definition costs more than STORING one, and the difference is
#: paid once per process plus a little per definition, never per call: four
#: trivial one-parameter definitions in a fresh process measured
#: 2221 / 2986 / 3751 / 4516 inferences through @m.define against
#: 592 / 1164 / 1736 / 2308 through `m += equation(...).to(...)`, so the first
#: compiled definition costs 1,629 more and each one after it 193 more.
#: The whole move is those four: the same file with every definition stored
#: instead measured 10973, the figure this twin was pinned at before. The 330
#: above 1629 + 3*193 is `fib`'s body being larger than the trivial ones the
#: rate was taken on.
#: A second, smaller cause is in this figure: binding an engine function with
#: `m.fn(...)` makes its name PYTHON-RESOLVABLE, so @m.define records no
#: hazard and builds a RUNNABLE Python twin where it would otherwise build one
#: that refuses. Measured by deleting only that binding line: 13511 against
#: 13558, and with it `reduce_fib.py()` answers where without it the twin raises
#: "its body uses the engine function ..., which exist only in the engine".
BUDGET = 13558


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # The engine's own `reduce`, bound so the Python below stays valid. A
    # compiled body resolves the NAME through the engine's registry rather
    # than through this object, so the binding changes nothing it emits.
    reduce = m.fn("reduce")

    @m.define
    def fib(n):
        # (= (fib $N) (if (< $N 2) $N (+ (fib (- $N 1)) (fib (- $N 2)))))
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    @m.define
    def myfunc():
        # (= (myfunc) 5)
        return 5

    # (= (call-fib) (call (fib (myfunc))))
    m += equation(S["call-fib"]()).to(S.call(S.fib(S.myfunc())))

    # (= (quote-fib) (quote (fib (myfunc))))
    m += equation(S["quote-fib"]()).to(S.quote(S.fib(S.myfunc())))

    @m.define(name="eval-fib")
    def eval_fib():
        # (= (eval-fib) (eval (fib (myfunc))))
        return eval(fib(myfunc()))

    @m.define(name="reduce-fib")
    def reduce_fib():
        # (= (reduce-fib) (reduce (fib (myfunc))))
        return reduce(fib(myfunc()))

    # !(test (fib-call (call-fib)) (fib-call 5))
    yield m.eval(S.test(S["fib-call"](S["call-fib"]()), S["fib-call"](5)))
    # !(test (fib-quote (quote-fib)) (fib-quote (quote (fib (myfunc)))))
    yield m.eval(
        S.test(
            S["fib-quote"](S["quote-fib"]()),
            S["fib-quote"](S.quote(S.fib(S.myfunc()))),
        )
    )
    # !(test (fib-eval (eval-fib)) (fib-eval 5))
    yield m.eval(S.test(S["fib-eval"](S["eval-fib"]()), S["fib-eval"](5)))
    # !(test (fib-reduce (reduce-fib)) (fib-reduce 5))
    yield m.eval(S.test(S["fib-reduce"](S["reduce-fib"]()), S["fib-reduce"](5)))
