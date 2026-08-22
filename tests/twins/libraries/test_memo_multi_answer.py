"""The Python twin of examples/libraries/test_memo_multi_answer.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 128335


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (choose $x)
    #    (Pair $x $x))
    m += expr(S["="], expr(S["choose"], V["x"]), expr(S["Pair"], V["x"], V["x"]))

    # (= (choose $x)
    #    $x)
    m += expr(S["="], expr(S["choose"], V["x"]), V["x"])

    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(memoize choose)
    yield m.eval(expr(S["memoize"], S["choose"]))

    # !(test (choose 7) (7 (Pair 7 7)))
    yield m.eval(expr(S["test"], expr(S["choose"], 7), expr(7, expr(S["Pair"], 7, 7))))

    # !(test (choose 7) (7 (Pair 7 7)))
    yield m.eval(expr(S["test"], expr(S["choose"], 7), expr(7, expr(S["Pair"], 7, 7))))

    yield from ()
