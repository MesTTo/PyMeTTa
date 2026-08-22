"""The Python twin of examples/libraries/test_memo_aggregate.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 130573


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (choices $x) $x)
    m += expr(S["="], expr(S["choices"], V["x"]), V["x"])

    # (= (choices $x) (+ $x 1))
    m += expr(S["="], expr(S["choices"], V["x"]), expr(S["+"], V["x"], 1))

    # (= (choices $x) (+ $x 2))
    m += expr(S["="], expr(S["choices"], V["x"]), expr(S["+"], V["x"], 2))

    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(config-memoize (aggregate sum))
    yield m.eval(expr(S["config-memoize"], expr(S["aggregate"], S["sum"])))

    # !(memoize choices)
    yield m.eval(expr(S["memoize"], S["choices"]))

    # !(test (choices 5) 18)
    yield m.eval(expr(S["test"], expr(S["choices"], 5), 18))

    # !(config-memoize (aggregate none))
    yield m.eval(expr(S["config-memoize"], expr(S["aggregate"], S["none"])))

    yield from ()
