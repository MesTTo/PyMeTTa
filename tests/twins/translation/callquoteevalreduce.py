"""Purpose: preserve call, quote, eval, and reduce across definition timing.

`compilefib` installs an equation from inside a stored `let`, so the program
stays at the term door; the space that `add-atom` writes is the handle itself,
which crosses into the built term as a grounded operand.

The guard below names its head. Python's `<`, `>`, `<=` and `>=` carry the
engine's total atom ORDER, so none of the four builds a term and a comparison
a stored equation is going to hold is written at the naming door.

Assumes:
  - fib is absent for the first claim, installed by compilefib, and present for
    the final two claims [source: examples/translation/callquoteevalreduce.metta lines 1-48; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - all four runnable claims distinguish quoted, unevaluated, and reduced terms
    [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/callquoteevalreduce.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


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
        # The `if` is the stored BODY of an equation, so it is data rather
        # than control flow.
        if_(S["<"](V.n, 2), V.n, S.fib(V.n - 1) + S.fib(V.n - 2))
    )
    compiled_body = Expression(
        (S.within(fib5),
        S["call-within"](S.call(fib5)),
        S["quote-within"](S.quote(fib5)),
        S["eval-within"](S.eval(fib5)),
        S["reduce-within"](S.reduce(fib5)),
    ))
    m += equation(S.compilefib()).to(
        S.let(  # rung: this `let` sequences INSIDE a stored program, where Python's assignment cannot reach
            V.temp,
            S["add-atom"](m, fib_equation),  # rung: add-atom is the target of a stored program, not this twin's own write
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
