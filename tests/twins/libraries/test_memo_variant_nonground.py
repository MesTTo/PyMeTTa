"""The Python twin of examples/libraries/test_memo_variant_nonground.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 126917


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (shape-kind (Pair $x $y))
    #    pair)
    m += expr(S["="], expr(S["shape-kind"], expr(S["Pair"], V["x"], V["y"])), S["pair"])

    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(memoize shape-kind)
    yield m.eval(expr(S["memoize"], S["shape-kind"]))

    # !(test (shape-kind (Pair $a 2)) pair)
    yield m.eval(expr(S["test"], expr(S["shape-kind"], expr(S["Pair"], V["a"], 2)), S["pair"]))

    # !(test (shape-kind (Pair $b 2)) pair)
    yield m.eval(expr(S["test"], expr(S["shape-kind"], expr(S["Pair"], V["b"], 2)), S["pair"]))

    yield from ()
