"""The Python twin of examples/libraries/memo_spaces.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 142268


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_memo))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_memo"])))

    # !(bind! &metric (new-space))
    yield m.eval(expr(S["bind!"], S["&metric"], expr(S["new-space"])))

    # !(add-atom &metric (= (shipping-cost $w) (* $w 9)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&metric"],
            expr(S["="], expr(S["shipping-cost"], V["w"]), expr(S["*"], V["w"], 9)),
        )
    )

    # (= (shipping-cost $w) (* $w 2))
    m += expr(S["="], expr(S["shipping-cost"], V["w"]), expr(S["*"], V["w"], 2))

    # !(test (shipping-cost 3) 6)
    yield m.eval(expr(S["test"], expr(S["shipping-cost"], 3), 6))

    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["shipping-cost"], 3), S["&metric"]), 27))

    # !(test (is-memoized shipping-cost) false)
    yield m.eval(expr(S["test"], expr(S["is-memoized"], S["shipping-cost"]), val(value=False)))

    # !(test (evalc (is-memoized shipping-cost) &metric) false)
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["is-memoized"], S["shipping-cost"]), S["&metric"]),
            val(value=False),
        )
    )

    # !(memoize shipping-cost)
    yield m.eval(expr(S["memoize"], S["shipping-cost"]))

    # !(test (is-memoized shipping-cost) true)
    yield m.eval(expr(S["test"], expr(S["is-memoized"], S["shipping-cost"]), val(value=True)))

    # !(test (evalc (is-memoized shipping-cost) &metric) false)
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["is-memoized"], S["shipping-cost"]), S["&metric"]),
            val(value=False),
        )
    )

    # !(test (shipping-cost 3) 6)
    yield m.eval(expr(S["test"], expr(S["shipping-cost"], 3), 6))

    # !(test (shipping-cost 3) 6)
    yield m.eval(expr(S["test"], expr(S["shipping-cost"], 3), 6))

    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["shipping-cost"], 3), S["&metric"]), 27))

    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["shipping-cost"], 3), S["&metric"]), 27))

    # !(evalc (memoize shipping-cost) &metric)
    yield m.eval(expr(S["evalc"], expr(S["memoize"], S["shipping-cost"]), S["&metric"]))

    # !(test (evalc (is-memoized shipping-cost) &metric) true)
    yield m.eval(
        expr(
            S["test"],
            expr(S["evalc"], expr(S["is-memoized"], S["shipping-cost"]), S["&metric"]),
            val(value=True),
        )
    )

    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["shipping-cost"], 3), S["&metric"]), 27))

    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["shipping-cost"], 3), S["&metric"]), 27))

    # !(test (shipping-cost 3) 6)
    yield m.eval(expr(S["test"], expr(S["shipping-cost"], 3), 6))

    # !(remove-atom &self (= (shipping-cost $w) (* $w 2)))
    yield m.eval(
        expr(
            S["remove-atom"],
            S["&self"],
            expr(S["="], expr(S["shipping-cost"], V["w"]), expr(S["*"], V["w"], 2)),
        )
    )

    # (= (shipping-cost $w) (* $w 3))
    m += expr(S["="], expr(S["shipping-cost"], V["w"]), expr(S["*"], V["w"], 3))

    # !(test (shipping-cost 3) 9)
    yield m.eval(expr(S["test"], expr(S["shipping-cost"], 3), 9))

    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(expr(S["test"], expr(S["evalc"], expr(S["shipping-cost"], 3), S["&metric"]), 27))

    yield from ()
