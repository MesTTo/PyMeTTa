"""The Python twin of examples/data/multiset_operations.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 6152


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (unique-atom (a b c d d)) (a b c d))
    yield m.eval(
        expr(
            S["test"],
            expr(S["unique-atom"], expr(S["a"], S["b"], S["c"], S["d"], S["d"])),
            expr(S["a"], S["b"], S["c"], S["d"]),
        )
    )

    # !(test (union-atom (a b b c) (b c c d)) (a b b c b c c d))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["union-atom"],
                expr(S["a"], S["b"], S["b"], S["c"]),
                expr(S["b"], S["c"], S["c"], S["d"]),
            ),
            expr(S["a"], S["b"], S["b"], S["c"], S["b"], S["c"], S["c"], S["d"]),
        )
    )

    # !(test (intersection-atom (a b c c) (b c c c d)) (b c c))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["intersection-atom"],
                expr(S["a"], S["b"], S["c"], S["c"]),
                expr(S["b"], S["c"], S["c"], S["c"], S["d"]),
            ),
            expr(S["b"], S["c"], S["c"]),
        )
    )

    # !(test (subtraction-atom (a b b c) (b c c d)) (a b))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["subtraction-atom"],
                expr(S["a"], S["b"], S["b"], S["c"]),
                expr(S["b"], S["c"], S["c"], S["d"]),
            ),
            expr(S["a"], S["b"]),
        )
    )

    # !(test (intersection-atom (a b c c) (b c d)) (b c))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["intersection-atom"],
                expr(S["a"], S["b"], S["c"], S["c"]),
                expr(S["b"], S["c"], S["d"]),
            ),
            expr(S["b"], S["c"]),
        )
    )

    # !(test (intersection-atom (a a a) (a)) (a))
    yield m.eval(
        expr(
            S["test"],
            expr(S["intersection-atom"], expr(S["a"], S["a"], S["a"]), expr(S["a"])),
            expr(S["a"]),
        )
    )

    # !(test (subtraction-atom (a a a) (a)) (a a))
    yield m.eval(
        expr(
            S["test"],
            expr(S["subtraction-atom"], expr(S["a"], S["a"], S["a"]), expr(S["a"])),
            expr(S["a"], S["a"]),
        )
    )

    # !(test (intersection-atom (a b) ()) ())
    yield m.eval(
        expr(S["test"], expr(S["intersection-atom"], expr(S["a"], S["b"]), expr()), expr())
    )

    yield from ()
