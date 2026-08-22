"""The Python twin of examples/basics/math_exp_random.metta: exp, log, random.

The one thing that does not translate literally is `and`. The original writes
`(and (<= $lo $x) (<= $x $hi))`, MeTTa's own connective. In a compiled body
Python's `and` is PYTHON's `and`, short-circuiting on truthiness, and lowers
to `let*` plus `py-truthy` plus `if`; the chained comparison written here is
tidier Python and lowers to a nested `if` instead. Neither is `(and ...)`,
and `&`, the operator that would mean it, is refused inside a body. The
answers agree for the booleans this equation compares; the residue table
records the hole against P14.4.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10696 to 10704, +8, and this one is
#: UNATTRIBUTED: it reproduces byte-stably across three runs and survives an
#: A/B of both candidate causes (the lib_json/lib_file/lib_thread counter
#: change and this file's own comment block each measure identically either
#: way), and engine/metta.pl is byte-identical to the tree the earlier figure
#: was taken on. Ten of the eighteen twins moved by exactly eight and
#: constraint_domains by forty-eight, which is the shape of the +/-8
#: instruction-layout floor this tree records elsewhere rather than a cost.
#: Pinned at the reproducible reading. Prior: #: RE-PINNED 2026-08-22, 10704 to 10696, -8, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 10137 to 10704, +567 (+5.59%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
BUDGET = 10704


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (exp-math 0) 1.0)
    yield m.eval(S.test(S["exp-math"](0), 1.0))
    # !(test (exp-math 1.0) 2.718281828459045)
    yield m.eval(S.test(S["exp-math"](1.0), 2.718281828459045))
    # !(test (< (abs-math (- (exp-math 2.0) (* e e))) 1.0e-12) true)
    yield m.eval(
        S.test(
            S["abs-math"](S["exp-math"](2.0) - S["*"](2.718281828459045, 2.718281828459045))
            < 1.0e-12,
            TRUE,
        )
    )
    # log-math is the inverse: log base e of e^x is x, within float error.
    # !(test (< (abs-math (- (log-math e (exp-math 3.0)) 3.0)) 1.0e-12) true)
    yield m.eval(
        S.test(
            S["abs-math"](S["log-math"](2.718281828459045, S["exp-math"](3.0)) - 3.0) < 1.0e-12,
            TRUE,
        )
    )

    @m.define(name="in-range")
    def in_range(lo, hi, x):
        # (= (in-range $lo $hi $x) (and (<= $lo $x) (<= $x $hi)))
        return lo <= x <= hi

    # The random generators answer inside their bounds, every draw.
    # !(test (in-range 1 6 (random-int 1 6)) true)
    yield m.eval(S.test(S["in-range"](1, 6, S["random-int"](1, 6)), TRUE))
    # !(test (in-range 0.0 1.0 (random-float 0.0 1.0)) true)
    yield m.eval(S.test(S["in-range"](0.0, 1.0, S["random-float"](0.0, 1.0)), TRUE))
    # !(test (in-range 5 5 (random-int 5 5)) true)
    yield m.eval(S.test(S["in-range"](5, 5, S["random-int"](5, 5)), TRUE))
