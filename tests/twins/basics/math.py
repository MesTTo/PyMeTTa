"""The Python twin of examples/basics/math.metta: the numeric surface.

Two things to notice. Python's arithmetic operators build MeTTa terms only on
SYMBOLIC atoms; on a grounded number they are that number's own arithmetic,
so `val(7) / 0` raises ZeroDivisionError in Python instead of building
`(/ 7 0)`. A term over ground operands is therefore spelled at the naming
door, `S["/"](7, 0)`, which is also what makes the error atoms below
constructible as the DATA they are.

And an error is an ordinary answer here, so the expected value of a failing
operation is a term like `(Error (/ 7 0) DivisionByZero)`, built the same way
as any other.
"""

from petta import S, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 20987


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # Mixed integer/float equality compares numeric VALUES.
    # !(test (== 1 1.0) True)
    yield m.eval(S.test(S["=="](1, 1.0), TRUE))
    # !(test (!= 1.0 1) False)
    yield m.eval(S.test(S["!="](1.0, 1), FALSE))

    # Division and remainder by zero answer contained error atoms.
    # !(test (/ 7 0) (Error (/ 7 0) DivisionByZero))
    yield m.eval(S.test(S["/"](7, 0), S.Error(S["/"](7, 0), S.DivisionByZero)))
    # !(test (% 7 0) (Error (% 7 0) DivisionByZero))
    yield m.eval(S.test(S["%"](7, 0), S.Error(S["%"](7, 0), S.DivisionByZero)))
    # !(test (collapse (/ 7 0)) (noeval ((Error (/ 7 0) DivisionByZero))))
    yield m.eval(
        S.test(
            S["collapse"](S["/"](7, 0)),
            S.noeval(expr(S.Error(S["/"](7, 0), S.DivisionByZero))),
        )
    )

    @m.define(name="math-string")
    def math_string():
        # (= (math-string) "s")
        return "s"

    # A computed string reaches the operation's own guard and is refused.
    # !(test (sqrt-math (math-string)) (Error (sqrt-math "s") (BadArgType 1 Number String)))
    yield m.eval(
        S.test(
            S["sqrt-math"](math_string()),
            S.Error(S["sqrt-math"](val("s")), S.BadArgType(1, S.Number, S.String)),
        )
    )

    # !(test (pow-math 2 3) 8.0)
    yield m.eval(S.test(S["pow-math"](2, 3), 8.0))
    # !(test (isnan-math (sqrt-math -1)) True)
    yield m.eval(S.test(S["isnan-math"](S["sqrt-math"](-1)), TRUE))
    # !(test (isinf-math (pow-math 0 -1)) True)
    yield m.eval(S.test(S["isinf-math"](S["pow-math"](0, -1)), TRUE))
    # !(test (pow-math 2 2147483648) (noeval (Error (pow-math 2 2147483648) "...")))
    yield m.eval(
        S.test(
            S["pow-math"](2, 2147483648),
            S.noeval(
                S.Error(
                    S["pow-math"](2, 2147483648),
                    val("power argument is too big, try using float value"),
                )
            ),
        )
    )
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
    yield m.eval(S.test(S["min-atom"](expr(2, 6, 7, 4, 9, 3)), 2))
    # !(test (max-atom (2 6 7 4 9 3)) 9)
    yield m.eval(S.test(S["max-atom"](expr(2, 6, 7, 4, 9, 3)), 9))
    # !(test (isinf-math inf) True)
    yield m.eval(S.test(S["isinf-math"](S.inf), TRUE))
    # !(test (isnan-math nan) True)
    yield m.eval(S.test(S["isnan-math"](S.nan), TRUE))
