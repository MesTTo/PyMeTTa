"""The Python twin of examples/libraries/he_math.metta.

The numeric surface: real-valued math promotes integers, pow answers Float and
enforces the signed-i32 bound only for integer exponents.

Every head here is a MeTTa name with a hyphen in it, which Python cannot spell
as an attribute, so each is named at the `S["..."]` door and called. The
argument tuples are Python tuples, which is what a MeTTa expression already is,
and `True`/`False` are Python's own booleans, which is what MeTTa's Bool atoms
are on this substrate.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13255 to 13255, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 13255 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 13255


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(test (pow-math 2 3) 8.0)
    yield m.eval(S.test(S["pow-math"](2, 3), 8.0))
    # !(test (isnan-math (sqrt-math -1)) True)
    yield m.eval(S.test(S["isnan-math"](S["sqrt-math"](-1)), TRUE))
    # !(test (isinf-math (pow-math 0 -1)) True)
    yield m.eval(S.test(S["isinf-math"](S["pow-math"](0, -1)), TRUE))
    # !(test (pow-math 1 2147483648.0) 1.0)
    yield m.eval(S.test(S["pow-math"](1, 2147483648.0), 1.0))
    # !(test (sqrt-math 9) 3.0)
    yield m.eval(S.test(S["sqrt-math"](9), 3.0))
    # !(test (abs-math -5) 5)
    yield m.eval(S.test(S["abs-math"](-5), 5))
    # !(test (log-math 10 100) 2.0)
    yield m.eval(S.test(S["log-math"](10, 100), 2.0))
    # !(test (trunc-math 5.6) 5)
    yield m.eval(S.test(S["trunc-math"](5.6), 5))
    # !(test (ceil-math 5.2) 6)
    yield m.eval(S.test(S["ceil-math"](5.2), 6))
    # !(test (floor-math 5.8) 5)
    yield m.eval(S.test(S["floor-math"](5.8), 5))
    # !(test (round-math 5.4) 5)
    yield m.eval(S.test(S["round-math"](5.4), 5))
    # !(test (round-math 5.6) 6)
    yield m.eval(S.test(S["round-math"](5.6), 6))
    # !(test (sin-math 0) 0.0)
    yield m.eval(S.test(S["sin-math"](0), 0.0))
    # !(test (asin-math 0) 0.0)
    yield m.eval(S.test(S["asin-math"](0), 0.0))
    # !(test (cos-math 0) 1.0)
    yield m.eval(S.test(S["cos-math"](0), 1.0))
    # !(test (acos-math 1) 0.0)
    yield m.eval(S.test(S["acos-math"](1), 0.0))
    # !(test (tan-math 0) 0.0)
    yield m.eval(S.test(S["tan-math"](0), 0.0))
    # !(test (atan-math 0) 0.0)
    yield m.eval(S.test(S["atan-math"](0), 0.0))
    # !(test (isnan-math 0.0) False)
    yield m.eval(S.test(S["isnan-math"](0.0), FALSE))
    # !(test (isinf-math 0.0) False)
    yield m.eval(S.test(S["isinf-math"](0.0), FALSE))
    # !(test (min-atom (2 6 7 4 9 3)) 2)
    yield m.eval(S.test(S["min-atom"]((2, 6, 7, 4, 9, 3)), 2))
    # !(test (max-atom (2 6 7 4 9 3)) 9)
    yield m.eval(S.test(S["max-atom"]((2, 6, 7, 4, 9, 3)), 9))
    # !(test (isinf-math inf) True)
    yield m.eval(S.test(S["isinf-math"](S.inf), TRUE))
    # !(test (isnan-math nan) True)
    yield m.eval(S.test(S["isnan-math"](S.nan), TRUE))
