"""examples/basics/math.metta in Python: the numeric surface.

Every `-math` operation is an engine function, so `m.fn` names it once and it
is then an ordinary Python callable: `sqrt(9)` is `(sqrt-math 9)` evaluated,
and it answers 3.0. An operation that refuses answers an Error ATOM rather
than raising, which is why the refusals below are compared as data.

Two things Python's own punctuation will not do here. Arithmetic operators
build MeTTa terms only on SYMBOLIC atoms; over two grounded numbers they are
that number's own arithmetic, so `val(7) / 0` raises ZeroDivisionError in
Python instead of building `(/ 7 0)`, and the terms whose refusals this file
is about are named at the `m.fn` door instead. And `==` is Python's own
structural equality on atoms, so MeTTa's `==` and `!=`, which compare NUMERIC
VALUES across int and float, are named too.

`min-atom` and `max-atom` dissolve: an expression is a sequence, so Python's
own `min` and `max` read it with no engine crossing at all.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-23, 6383 to 5991, -392, by the p14-tabling merge, the
#: sole change between the two readings: the define-path saving seen corpus-
#: wide. Ratio 5991/33601 = 0.1783 [measured 2026-08-23 min-of-3 via
#: tools/twin_coverage.py --measure]. Prior:
#: RE-PINNED 2026-08-22, 21852 to 6383, -15469 (-70.8%), by the twin
#: contract change: thirty-one `test` wrappers left the engine for
#: `assert`, `min-atom` and `max-atom` left it for Python's own `min` and
#: `max` over an expression, which is a sequence, and one `collapse` became
#: `len()` over the answer list; every `-math` call and every refusal
#: stayed, reached through `m.fn`. Against the example's 33807 the ratio is
#: 0.1888 [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The
#: old figure priced a different program.
BUDGET = 5991

#: The six numbers `min-atom` and `max-atom` are asked about.
NUMBERS = expr(2, 6, 7, 4, 9, 3)


def twin(m):
    """Ask every numeric operation what it answers, refusals included."""
    equal, unequal = m.fn("=="), m.fn("!=")
    divide, remainder = m.fn("/"), m.fn("%")
    sqrt, power, log = m.fn("sqrt-math"), m.fn("pow-math"), m.fn("log-math")
    isnan, isinf = m.fn("isnan-math"), m.fn("isinf-math")
    absolute = m.fn("abs-math")
    trunc, ceil, floor, rounded = (
        m.fn("trunc-math"), m.fn("ceil-math"), m.fn("floor-math"), m.fn("round-math")
    )
    sin, asin, cos, acos = (
        m.fn("sin-math"), m.fn("asin-math"), m.fn("cos-math"), m.fn("acos-math")
    )
    tan, atan = m.fn("tan-math"), m.fn("atan-math")

    # Mixed integer/float equality compares numeric VALUES.
    assert equal(1, 1.0) is True
    assert unequal(1.0, 1) is False

    # Division and remainder by zero answer contained error atoms, and an
    # error is an ordinary ANSWER: `.all()` is the door that says so, where a
    # plain call raises on one, and the form after it still runs.
    division_error = S.Error(S["/"](7, 0), S.DivisionByZero)
    assert divide.all(7, 0) == [division_error]
    assert remainder.all(7, 0) == [S.Error(S["%"](7, 0), S.DivisionByZero)]
    # (collapse (/ 7 0)) adds the cardinality: exactly one answer, and it is
    # that error. `list()` is what collapse means, and an evaluation already
    # answers the list of its answers.
    assert len(divide.all(7, 0)) == 1

    @m.define(name="math-string")
    def math_string():
        # (= (math-string) "s")
        return "s"

    # A COMPUTED string reaches the operation's own guard and is refused
    # there, before the host can treat one character as its code.
    assert sqrt.all(S["math-string"]()) == [
        S.Error(S["sqrt-math"](val("s")), S.BadArgType(1, S.Number, S.String))
    ]

    assert power(2, 3) == 8.0
    assert isnan(sqrt(-1)) is True
    assert isinf(power(0, -1)) is True
    # An integer exponent is bounded to signed i32; a float one is not.
    assert power.all(2, 2147483648) == [
        S.Error(
            S["pow-math"](2, 2147483648),
            val("power argument is too big, try using float value"),
        )
    ]
    assert power(1, 2147483648.0) == 1.0

    # Real-valued operations promote integer operands to Float.
    assert sqrt(9) == 3.0
    assert absolute(-5) == 5
    assert log(10, 100) == 2.0
    assert trunc(5.6) == 5
    assert ceil(5.2) == 6
    assert floor(5.8) == 5
    assert rounded(5.4) == 5
    assert rounded(5.6) == 6
    assert sin(0) == 0.0
    assert asin(0) == 0.0
    assert cos(0) == 1.0
    assert acos(1) == 0.0
    assert tan(0) == 0.0
    assert atan(0) == 0.0
    assert isnan(0.0) is False
    assert isinf(0.0) is False

    # (min-atom (2 6 7 4 9 3)) and (max-atom ...): an expression IS a
    # sequence, so these are Python's own, at no engine cost.
    assert min(NUMBERS) == 2
    assert max(NUMBERS) == 9

    assert isinf(S.inf) is True
    assert isnan(S.nan) is True
