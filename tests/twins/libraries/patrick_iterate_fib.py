"""The Python twin of examples/libraries/patrick_iterate_fib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 31840


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_patrick))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_patrick"])))

    # (= (fib-step $i ($a $b))
    #    ($b (+ $a $b)))
    m += expr(
        S["="],
        expr(S["fib-step"], V["i"], expr(V["a"], V["b"])),
        expr(V["b"], expr(S["+"], V["a"], V["b"])),
    )

    # (= (fib $n)
    #    (first (iterate 0 $n (0 1) fib-step)))
    m += expr(
        S["="],
        expr(S["fib"], V["n"]),
        expr(S["first"], expr(S["iterate"], 0, V["n"], expr(0, 1), S["fib-step"])),
    )

    # !(test (fib 100) 354224848179261915075)
    yield m.eval(expr(S["test"], expr(S["fib"], 100), 354224848179261915075))

    yield from ()
