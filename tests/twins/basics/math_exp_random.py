"""examples/basics/math_exp_random.metta in Python: exp, log, and the dice.

The engine computes `exp` and `log`; the subtraction, the absolute value and
the comparison that check them are Python's own, so the float-tolerance lines
read as ordinary Python and pay no crossing for the arithmetic around the
call.

The one thing that does not translate literally is `and`. The original writes
`(and (<= $lo $x) (<= $x $hi))`, MeTTa's own connective. Python's `and` in a
compiled body is PYTHON's `and`, short-circuiting on truthiness, and the
chained comparison written here lowers to a nested `if` instead; `&`, the
operator that would mean MeTTa's, is refused inside a body, and `and` itself
is a Python keyword no body can name. The answers agree for the booleans this
equation compares, and the residue table records the hole against P14.4.
"""

#: e, to the precision the original writes it at.
E = 2.718281828459045

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10704 to 4065, -6639 (-62.0%), by the twin
#: contract change: seven `test` wrappers left the engine for `assert`, and
#: the two float-tolerance claims moved their subtraction, absolute value
#: and comparison into Python, which leaves only `exp-math` and `log-math`
#: themselves crossing. Against the example's 14535 the ratio is 0.2797
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 4065


def twin(m):
    """Check exp against its own inverse, then check the dice stay in range."""
    exp, log = m.fn("exp-math"), m.fn("log-math")
    randint, randfloat = m.fn("random-int"), m.fn("random-float")

    assert exp(0) == 1.0
    assert exp(1.0) == E
    assert abs(exp(2.0) - E * E) < 1.0e-12
    # log-math is the inverse: log base e of e^x is x, within float error.
    assert abs(log(E, exp(3.0)) - 3.0) < 1.0e-12

    @m.define(name="in-range")
    def in_range(lo, hi, x):
        # (= (in-range $lo $hi $x) (and (<= $lo $x) (<= $x $hi)))
        return lo <= x <= hi

    # The random generators answer inside their bounds, every draw.
    assert in_range(1, 6, randint(1, 6)) == [True]
    assert in_range(0.0, 1.0, randfloat(0.0, 1.0)) == [True]
    assert in_range(5, 5, randint(5, 5)) == [True]
