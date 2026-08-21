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
BUDGET = 10061


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
            S["<"](
                S["abs-math"](
                    S["-"](
                        S["exp-math"](2.0),
                        S["*"](2.718281828459045, 2.718281828459045),
                    )
                ),
                1.0e-12,
            ),
            TRUE,
        )
    )
    # log-math is the inverse: log base e of e^x is x, within float error.
    # !(test (< (abs-math (- (log-math e (exp-math 3.0)) 3.0)) 1.0e-12) true)
    yield m.eval(
        S.test(
            S["<"](
                S["abs-math"](
                    S["-"](
                        S["log-math"](2.718281828459045, S["exp-math"](3.0)),
                        3.0,
                    )
                ),
                1.0e-12,
            ),
            TRUE,
        )
    )

    @m.define(name="in-range")
    def in_range(lo, hi, x):
        # (= (in-range $lo $hi $x) (and (<= $lo $x) (<= $x $hi)))
        return lo <= x <= hi

    # The random generators answer inside their bounds, every draw.
    # !(test (in-range 1 6 (random-int 1 6)) true)
    yield m.eval(S.test(in_range(1, 6, S["random-int"](1, 6)), TRUE))
    # !(test (in-range 0.0 1.0 (random-float 0.0 1.0)) true)
    yield m.eval(S.test(in_range(0.0, 1.0, S["random-float"](0.0, 1.0)), TRUE))
    # !(test (in-range 5 5 (random-int 5 5)) true)
    yield m.eval(S.test(in_range(5, 5, S["random-int"](5, 5)), TRUE))
