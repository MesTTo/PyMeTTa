"""The Python twin of examples/libraries/he_math.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 13255


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (pow-math 2 3) 8.0)
    yield m.eval(expr(S["test"], expr(S["pow-math"], 2, 3), 8.0))

    # !(test (isnan-math (sqrt-math -1)) True)
    yield m.eval(expr(S["test"], expr(S["isnan-math"], expr(S["sqrt-math"], -1)), val(value=True)))

    # !(test (isinf-math (pow-math 0 -1)) True)
    yield m.eval(
        expr(S["test"], expr(S["isinf-math"], expr(S["pow-math"], 0, -1)), val(value=True))
    )

    # !(test (pow-math 1 2147483648.0) 1.0)
    yield m.eval(expr(S["test"], expr(S["pow-math"], 1, 2147483648.0), 1.0))

    # !(test (sqrt-math 9) 3.0)
    yield m.eval(expr(S["test"], expr(S["sqrt-math"], 9), 3.0))

    # !(test (abs-math -5) 5)
    yield m.eval(expr(S["test"], expr(S["abs-math"], -5), 5))

    # !(test (log-math 10 100) 2.0)
    yield m.eval(expr(S["test"], expr(S["log-math"], 10, 100), 2.0))

    # !(test (trunc-math 5.6) 5)
    yield m.eval(expr(S["test"], expr(S["trunc-math"], 5.6), 5))

    # !(test (ceil-math 5.2) 6)
    yield m.eval(expr(S["test"], expr(S["ceil-math"], 5.2), 6))

    # !(test (floor-math 5.8) 5)
    yield m.eval(expr(S["test"], expr(S["floor-math"], 5.8), 5))

    # !(test (round-math 5.4) 5)
    yield m.eval(expr(S["test"], expr(S["round-math"], 5.4), 5))

    # !(test (round-math 5.6) 6)
    yield m.eval(expr(S["test"], expr(S["round-math"], 5.6), 6))

    # !(test (sin-math 0) 0.0)
    yield m.eval(expr(S["test"], expr(S["sin-math"], 0), 0.0))

    # !(test (asin-math 0) 0.0)
    yield m.eval(expr(S["test"], expr(S["asin-math"], 0), 0.0))

    # !(test (cos-math 0) 1.0)
    yield m.eval(expr(S["test"], expr(S["cos-math"], 0), 1.0))

    # !(test (acos-math 1) 0.0)
    yield m.eval(expr(S["test"], expr(S["acos-math"], 1), 0.0))

    # !(test (tan-math 0) 0.0)
    yield m.eval(expr(S["test"], expr(S["tan-math"], 0), 0.0))

    # !(test (atan-math 0) 0.0)
    yield m.eval(expr(S["test"], expr(S["atan-math"], 0), 0.0))

    # !(test (isnan-math 0.0) False)
    yield m.eval(expr(S["test"], expr(S["isnan-math"], 0.0), val(value=False)))

    # !(test (isinf-math 0.0) False)
    yield m.eval(expr(S["test"], expr(S["isinf-math"], 0.0), val(value=False)))

    # !(test (min-atom (2 6 7 4 9 3)) 2)
    yield m.eval(expr(S["test"], expr(S["min-atom"], expr(2, 6, 7, 4, 9, 3)), 2))

    # !(test (max-atom (2 6 7 4 9 3)) 9)
    yield m.eval(expr(S["test"], expr(S["max-atom"], expr(2, 6, 7, 4, 9, 3)), 9))

    # !(test (isinf-math inf) True)
    yield m.eval(expr(S["test"], expr(S["isinf-math"], S["inf"]), val(value=True)))

    # !(test (isnan-math nan) True)
    yield m.eval(expr(S["test"], expr(S["isnan-math"], S["nan"]), val(value=True)))

    yield from ()
