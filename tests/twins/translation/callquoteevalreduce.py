"""examples/translation/callquoteevalreduce.metta in Python: the same four, timed.

`call`, `quote`, `eval` and `reduce` around `(fib 5)`, asked three times: before
`fib` exists, from inside the definition that installs it, and after. What each
one answers depends on whether the compiler had seen `fib` when the wrapper was
compiled, which is the whole file.

Every definition compiles. `fib` does not exist when the `before-*` wrappers
are written, so their inner call is mentioned rather than called; the four
outer heads carry hyphens and no equations, so they are mentioned too.

`compilefib` is the interesting one and it compiles whole. Its body installs an
equation from inside itself, which is `add-atom` at the function namespace
taking the handle it was given, and the original's `let` around that write is a
Python assignment to a name the body then ignores. The equation being installed
is built in place, `if` and all, because a compiled body's expressions are the
stored term rather than control flow: `$n < 2` there BUILDS `(< $n 2)`, where
the same comparison on an atom in hand would order it instead.
"""

from metta import Expression, S, V, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Install wrappers around a dynamically installed Fibonacci definition."""
    fib5 = S.fib(5)

    @m.define
    def before_call():                  # (= (before-call) (call-before (call (fib 5))))
        return S["call-before"](S.call(S.fib(5)))

    @m.define
    def before_quote():                 # (= (before-quote) (quote-before (quote (fib 5))))
        return S["quote-before"](S.quote(S.fib(5)))

    @m.define
    def before_eval():                  # (= (before-eval) (eval-before (eval (fib 5))))
        return S["eval-before"](S.eval(S.fib(5)))

    @m.define
    def before_reduce():                # (= (before-reduce) (reduce-before (reduce (fib 5))))
        return S["reduce-before"](S.reduce(S.fib(5)))

    # With no fib to reduce, quote keeps its payload and the other two hand
    # theirs back unevaluated. `before-call` is left out because it errors,
    # which is what the original's head says in as many words. The original
    # writes the two unevaluated payloads as `(noeval (fib 5))`, because `test`
    # evaluates its expected side too and `noeval` comes off there; an assert
    # compares against a literal, so the payload is written as it arrives.
    assert m.eval(S["before-call-errors-ofc"](
        S["before-quote"](), S["before-eval"](), S["before-reduce"]()
    )) == [S["before-call-errors-ofc"](
        S["quote-before"](S.quote(fib5)),
        S["eval-before"](fib5),
        S["reduce-before"](fib5),
    )]

    @m.define
    def compilefib():
        # (= (compilefib) (let $temp (add-atom &self (= (fib $N) (if (< $N 2) $N
        #      (+ (fib (- $N 1)) (fib (- $N 2)))))) ((within (fib 5)) ...)))
        _temp = fn.add_atom(m, S["="](
            S.fib(V.n), V.n if V.n < 2 else S.fib(V.n - 1) + S.fib(V.n - 2)
        ))
        return (S.within(S.fib(5)),
                S["call-within"](S.call(S.fib(5))),
                S["quote-within"](S.quote(S.fib(5))),
                S["eval-within"](S.eval(S.fib(5))),
                S["reduce-within"](S.reduce(S.fib(5))))

    # The five inside were compiled before the add-atom ran, so `within` still
    # holds an unevaluated call while the four wrappers reduce.
    assert compilefib().one() == Expression((
        S.within(fib5),
        S["call-within"](5),
        S["quote-within"](S.quote(fib5)),
        S["eval-within"](5),
        S["reduce-within"](5),
    ))

    @m.define
    def after_call():                   # (= (after-call) (call-after (call (fib 5))))
        return S["call-after"](S.call(S.fib(5)))

    @m.define
    def after_quote():                  # (= (after-quote) (quote-after (quote (fib 5))))
        return S["quote-after"](S.quote(S.fib(5)))

    @m.define
    def after_eval():                   # (= (after-eval) (eval-after (eval (fib 5))))
        return S["eval-after"](S.eval(S.fib(5)))

    @m.define
    def after_reduce():                 # (= (after-reduce) (reduce-after (reduce (fib 5))))
        return S["reduce-after"](S.reduce(S.fib(5)))

    # fib exists now, so the four wrappers written BEFORE it reduce too.
    assert m.eval(Expression((
        S["before-call"](), S["before-quote"](), S["before-eval"](), S["before-reduce"]()
    ))) == [Expression((
        S["call-before"](5),
        S["quote-before"](S.quote(fib5)),
        S["eval-before"](5),
        S["reduce-before"](5),
    ))]

    assert m.eval(Expression((
        S["after-call"](), S["after-quote"](), S["after-eval"](), S["after-reduce"]()
    ))) == [Expression((
        S["call-after"](5),
        S["quote-after"](S.quote(fib5)),
        S["eval-after"](5),
        S["reduce-after"](5),
    ))]
