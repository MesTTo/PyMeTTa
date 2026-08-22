"""The Python twin of examples/libraries/test_memo_dependency_invalidation.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 127000


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (double $x) (+ $x $x))
    m += expr(S["="], expr(S["double"], V["x"]), expr(S["+"], V["x"], V["x"]))

    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(memoize double)
    yield m.eval(expr(S["memoize"], S["double"]))

    # !(test (double 5) 10)
    yield m.eval(expr(S["test"], expr(S["double"], 5), 10))

    # !(test (double 5) 10)
    yield m.eval(expr(S["test"], expr(S["double"], 5), 10))

    yield from ()
