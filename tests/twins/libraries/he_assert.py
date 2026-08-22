"""The Python twin of examples/libraries/he_assert.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 21497


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # !(test (assertEqual (+ 1 2) (- 6 3)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["assertEqual"], expr(S["+"], 1, 2), expr(S["-"], 6, 3)),
            val(value=True),
        )
    )

    # !(test (assertAlphaEqual (h $x $y) (h $a $b)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["assertAlphaEqual"], expr(S["h"], V["x"], V["y"]), expr(S["h"], V["a"], V["b"])),
            val(value=True),
        )
    )

    # !(test (assertAlphaEqual (quote (+ $x $y)) (quote (+ $a $b))) True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["assertAlphaEqual"],
                expr(S["quote"], expr(S["+"], V["x"], V["y"])),
                expr(S["quote"], expr(S["+"], V["a"], V["b"])),
            ),
            val(value=True),
        )
    )

    # !(test (assertEqualToResult (+ 1 2) (3)) True)
    yield m.eval(
        expr(
            S["test"], expr(S["assertEqualToResult"], expr(S["+"], 1, 2), expr(3)), val(value=True)
        )
    )

    # !(test (assertEqualToResult (superpose (1 2)) (1 2)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["assertEqualToResult"], expr(S["superpose"], expr(1, 2)), expr(1, 2)),
            val(value=True),
        )
    )

    # (= (adder) ($x))
    m += expr(S["="], expr(S["adder"]), expr(V["x"]))

    # !(test (assertAlphaEqualToResult (adder) (($y))) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["assertAlphaEqualToResult"], expr(S["adder"]), expr(expr(V["y"]))),
            val(value=True),
        )
    )

    # !(test (assertIncludes (superpose (1 2 3)) (2)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["assertIncludes"], expr(S["superpose"], expr(1, 2, 3)), expr(2)),
            val(value=True),
        )
    )

    # !(test (assertIncludes (superpose (1 2 3)) (2 3)) True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["assertIncludes"], expr(S["superpose"], expr(1, 2, 3)), expr(2, 3)),
            val(value=True),
        )
    )

    # !(test (assertEqualMsg (+ 1 2) (- 6 3) "sums differ") True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["assertEqualMsg"], expr(S["+"], 1, 2), expr(S["-"], 6, 3), val("sums differ")),
            val(value=True),
        )
    )

    # !(test (assertAlphaEqualMsg (h $x $y) (h $a $b) "not alpha equal") True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["assertAlphaEqualMsg"],
                expr(S["h"], V["x"], V["y"]),
                expr(S["h"], V["a"], V["b"]),
                val("not alpha equal"),
            ),
            val(value=True),
        )
    )

    # !(test (assertEqualToResultMsg (+ 1 2) (3) "not the expected result") True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["assertEqualToResultMsg"],
                expr(S["+"], 1, 2),
                expr(3),
                val("not the expected result"),
            ),
            val(value=True),
        )
    )

    # !(test (assertAlphaEqualToResultMsg (adder) (($y)) "not alpha equal") True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["assertAlphaEqualToResultMsg"],
                expr(S["adder"]),
                expr(expr(V["y"])),
                val("not alpha equal"),
            ),
            val(value=True),
        )
    )

    yield from ()
