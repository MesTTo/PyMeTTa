"""Purpose: preserve call, quote, eval, and reduce across definition timing.

Assumes:
  - fib is absent for the first claim, installed by compilefib, and present for
    the final two claims [source: examples/translation/callquoteevalreduce.metta lines 1-48; commit=WORKTREE]
Guarantees:
  - all four runnable claims distinguish quoted, unevaluated, and reduced terms
    [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/callquoteevalreduce.metta; fixture=fresh isolated process; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 28011..28139 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 28011,
    "maximum": 28139,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}
RUNG = "compilefib installs an equation from inside a stored let, so the program stays at the term door"

SELF = S["&self"]


def twin(m):
    """Install wrappers around a dynamically installed Fibonacci definition."""
    fib5 = S.fib(5)

    m += equation(S["before-call"]()).to(S["call-before"](S.call(fib5)))
    m += equation(S["before-quote"]()).to(S["quote-before"](S.quote(fib5)))
    m += equation(S["before-eval"]()).to(S["eval-before"](S.eval(fib5)))
    m += equation(S["before-reduce"]()).to(S["reduce-before"](S.reduce(fib5)))

    before_missing = S["before-call-errors-ofc"](
        S["before-quote"](),
        S["before-eval"](),
        S["before-reduce"](),
    )
    assert m.eval(before_missing) == [
        S["before-call-errors-ofc"](
            S["quote-before"](S.quote(fib5)),
            S["eval-before"](fib5),
            S["reduce-before"](fib5),
        )
    ]

    fib_equation = equation(S.fib(V.n)).to(
        S["if"](
            V.n < 2,
            V.n,
            S.fib(V.n - 1) + S.fib(V.n - 2),
        )
    )
    compiled_body = Expression(
        (S.within(fib5),
        S["call-within"](S.call(fib5)),
        S["quote-within"](S.quote(fib5)),
        S["eval-within"](S.eval(fib5)),
        S["reduce-within"](S.reduce(fib5)),
    ))
    m += equation(S.compilefib()).to(
        S.let(
            V.temp,
            S["add-atom"](SELF, fib_equation),  # rung: the target is computed inside the stored program
            compiled_body,
        )
    )

    assert m.eval(S.compilefib()) == [
        Expression(
            (S.within(fib5),
            S["call-within"](5),
            S["quote-within"](S.quote(fib5)),
            S["eval-within"](5),
            S["reduce-within"](5),
        ))
    ]

    m += equation(S["after-call"]()).to(S["call-after"](S.call(fib5)))
    m += equation(S["after-quote"]()).to(S["quote-after"](S.quote(fib5)))
    m += equation(S["after-eval"]()).to(S["eval-after"](S.eval(fib5)))
    m += equation(S["after-reduce"]()).to(S["reduce-after"](S.reduce(fib5)))

    assert m.eval(
        Expression(
            (S["before-call"](),
            S["before-quote"](),
            S["before-eval"](),
            S["before-reduce"](),
        ))
    ) == [
        Expression(
            (S["call-before"](5),
            S["quote-before"](S.quote(fib5)),
            S["eval-before"](5),
            S["reduce-before"](5),
        ))
    ]
    assert m.eval(
        Expression(
            (S["after-call"](),
            S["after-quote"](),
            S["after-eval"](),
            S["after-reduce"](),
        ))
    ) == [
        Expression(
            (S["call-after"](5),
            S["quote-after"](S.quote(fib5)),
            S["eval-after"](5),
            S["reduce-after"](5),
        ))
    ]
