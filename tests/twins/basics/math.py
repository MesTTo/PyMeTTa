"""The Python twin of examples/basics/math.metta: the numeric surface.

Two things to notice. Python's arithmetic operators build MeTTa terms only on
SYMBOLIC atoms; on a grounded number they are that number's own arithmetic,
so `val(7) / 0` raises ZeroDivisionError in Python instead of building
`(/ 7 0)`. A term over ground operands is therefore spelled at the naming
door, `S["/"](7, 0)`, which is also what makes the error atoms below
constructible as the DATA they are.

The method forms do not close the gap either. `a.eq(b)` is the table's spelling
for the taken `==` and does build `(== a b)`, but it wants an atom on the left,
which two bare literals are not; and `a.ne(b)` builds `(not (== a b))`, a
different atom from the `(!= 1.0 1)` the original writes.

And an error is an ordinary answer here, so the expected value of a failing
operation is a term like `(Error (/ 7 0) DivisionByZero)`, built the same way
as any other.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 21844 to 21852, +8, and this one is
#: UNATTRIBUTED: it reproduces byte-stably across three runs and survives an
#: A/B of both candidate causes (the lib_json/lib_file/lib_thread counter
#: change and this file's own comment block each measure identically either
#: way), and engine/metta.pl is byte-identical to the tree the earlier figure
#: was taken on. Ten of the eighteen twins moved by exactly eight and
#: constraint_domains by forty-eight, which is the shape of the +/-8
#: instruction-layout floor this tree records elsewhere rather than a cost.
#: Pinned at the reproducible reading. Prior: #: RE-PINNED 2026-08-22, 21876 to 21844, -32, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 21061 to 21876, +815 (+3.87%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
BUDGET = 21852


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
            S.collapse(S["/"](7, 0)),
            S.noeval((S.Error(S["/"](7, 0), S.DivisionByZero),)),
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
            S["sqrt-math"](S["math-string"]()),
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
    yield m.eval(S.test(S["min-atom"]((2, 6, 7, 4, 9, 3)), 2))
    # !(test (max-atom (2 6 7 4 9 3)) 9)
    yield m.eval(S.test(S["max-atom"]((2, 6, 7, 4, 9, 3)), 9))
    # !(test (isinf-math inf) True)
    yield m.eval(S.test(S["isinf-math"](S.inf), TRUE))
    # !(test (isnan-math nan) True)
    yield m.eval(S.test(S["isnan-math"](S.nan), TRUE))
