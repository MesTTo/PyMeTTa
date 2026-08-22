"""The Python twin of examples/libraries/test_memo_same_name_multi_arity.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 133122


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # (= (mix $x) (+ $x 1))
    m += expr(S["="], expr(S["mix"], V["x"]), expr(S["+"], V["x"], 1))

    # (= (mix $x $y) (+ $x $y))
    m += expr(S["="], expr(S["mix"], V["x"], V["y"]), expr(S["+"], V["x"], V["y"]))

    # !(memoize mix 1)
    yield m.eval(expr(S["memoize"], S["mix"], 1))

    # !(test (is-memoized mix 1) true)
    yield m.eval(expr(S["test"], expr(S["is-memoized"], S["mix"], 1), val(value=True)))

    # !(test (is-memoized mix 2) false)
    yield m.eval(expr(S["test"], expr(S["is-memoized"], S["mix"], 2), val(value=False)))

    # !(test (mix 5) 6)
    yield m.eval(expr(S["test"], expr(S["mix"], 5), 6))

    # !(test (mix 5) 6)
    yield m.eval(expr(S["test"], expr(S["mix"], 5), 6))

    # !(test (mix 3 4) 7)
    yield m.eval(expr(S["test"], expr(S["mix"], 3, 4), 7))

    # !(test (mix 3 4) 7)
    yield m.eval(expr(S["test"], expr(S["mix"], 3, 4), 7))

    # !(memoize mix 2)
    yield m.eval(expr(S["memoize"], S["mix"], 2))

    # !(test (is-memoized mix 2) true)
    yield m.eval(expr(S["test"], expr(S["is-memoized"], S["mix"], 2), val(value=True)))

    # !(test (mix 8 9) 17)
    yield m.eval(expr(S["test"], expr(S["mix"], 8, 9), 17))

    # !(test (mix 8 9) 17)
    yield m.eval(expr(S["test"], expr(S["mix"], 8, 9), 17))

    yield from ()
