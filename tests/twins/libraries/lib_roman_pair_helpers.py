"""The Python twin of examples/libraries/lib_roman_pair_helpers.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 152447


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_roman))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_roman"])))

    # (= (inc $x) (+ $x 1))
    m += expr(S["="], expr(S["inc"], V["x"]), expr(S["+"], V["x"], 1))

    # !(test (first inc (1 9)) (2 9))
    yield m.eval(expr(S["test"], expr(S["first"], S["inc"], expr(1, 9)), expr(2, 9)))

    # !(test (second inc (1 9)) (1 10))
    yield m.eval(expr(S["test"], expr(S["second"], S["inc"], expr(1, 9)), expr(1, 10)))

    # !(test (flip (left right)) (right left))
    yield m.eval(
        expr(S["test"], expr(S["flip"], expr(S["left"], S["right"])), expr(S["right"], S["left"]))
    )

    yield from ()
