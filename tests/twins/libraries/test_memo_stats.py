"""The Python twin of examples/libraries/test_memo_stats.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 127317


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (sq $x) (* $x $x))
    m += expr(S["="], expr(S["sq"], V["x"]), expr(S["*"], V["x"], V["x"]))

    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(memoize sq)
    yield m.eval(expr(S["memoize"], S["sq"]))

    # !(test (sq 9) 81)
    yield m.eval(expr(S["test"], expr(S["sq"], 9), 81))

    # !(test (sq 9) 81)
    yield m.eval(expr(S["test"], expr(S["sq"], 9), 81))

    # !(test (sq 9) 81)
    yield m.eval(expr(S["test"], expr(S["sq"], 9), 81))

    yield from ()
