"""examples/basics/math_exp_random.metta in Python: exp, log, and the dice.

The engine computes `exp` and `log`; the subtraction, the absolute value and
the comparison that check them are Python's own, so the float-tolerance lines
read as ordinary Python and pay no crossing for the arithmetic around the
call. A nested call is BUILT with the static `fn` namespace and evaluated
once, so `(log-math e (exp-math 3.0))` is one term rather than two crossings,
which is the crossing rule as well as the spelling.

The one thing that does not translate literally is `and`. The original writes
`(and (<= $lo $x) (<= $x $hi))`, MeTTa's own connective. Python's `and` in a
compiled body is PYTHON's `and`, short-circuiting on truthiness, and the
chained comparison written here lowers to a nested `if` instead; `&`, the
operator that would mean MeTTa's, is refused inside a body, and `and` itself
is a Python keyword no body can name. The answers agree for the booleans this
equation compares, and the residue table records the hole against P14.4.
"""

from petta import fn

#: e, to the precision the original writes it at.
E = 2.718281828459045

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Check exp against its own inverse, then check the dice stay in range."""
    exp, log = m.fn.exp_math, m.fn.log_math

    assert exp(0) == [1.0]
    assert exp(1.0) == [E]
    assert abs(exp(2.0).one() - E * E) < 1.0e-12
    # log-math is the inverse: log base e of e^x is x, within float error.
    assert abs(log(E, fn.exp_math(3.0)).one() - 3.0) < 1.0e-12

    @m.define(name="in-range")
    def in_range(lo, hi, x):
        # (= (in-range $lo $hi $x) (and (<= $lo $x) (<= $x $hi)))
        return lo <= x <= hi

    # The random generators answer inside their bounds, every draw.
    assert in_range(1, 6, fn.random_int(1, 6)) == [True]
    assert in_range(0.0, 1.0, fn.random_float(0.0, 1.0)) == [True]
    assert in_range(5, 5, fn.random_int(5, 5)) == [True]
