"""The Python twin of examples/data/nestedcons.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1252


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (f (cons $a (cons $b $L)))
    #    $b)
    m += expr(
        S["="], expr(S["f"], expr(S["cons"], V["a"], expr(S["cons"], V["b"], V["L"]))), V["b"]
    )

    # !(test (f (a b c d)) b)
    yield m.eval(expr(S["test"], expr(S["f"], expr(S["a"], S["b"], S["c"], S["d"])), S["b"]))

    yield from ()
