"""The Python twin of examples/libraries/test_memo_per_arity.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 130265


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (add $x $y) (+ $x $y))
    m += expr(S["="], expr(S["add"], V["x"], V["y"]), expr(S["+"], V["x"], V["y"]))

    # (= (add $x $y $z) (+ (+ $x $y) $z))
    m += expr(
        S["="],
        expr(S["add"], V["x"], V["y"], V["z"]),
        expr(S["+"], expr(S["+"], V["x"], V["y"]), V["z"]),
    )

    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(memoize add 2)
    yield m.eval(expr(S["memoize"], S["add"], 2))

    # !(test (add 3 4) 7)
    yield m.eval(expr(S["test"], expr(S["add"], 3, 4), 7))

    # !(test (add 3 4) 7)
    yield m.eval(expr(S["test"], expr(S["add"], 3, 4), 7))

    # !(test (add 1 2 3) 6)
    yield m.eval(expr(S["test"], expr(S["add"], 1, 2, 3), 6))

    # !(test (add 5 6) 11)
    yield m.eval(expr(S["test"], expr(S["add"], 5, 6), 11))

    # !(test (add 5 6) 11)
    yield m.eval(expr(S["test"], expr(S["add"], 5, 6), 11))

    yield from ()
