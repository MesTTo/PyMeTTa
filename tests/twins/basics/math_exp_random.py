"""examples/basics/math_exp_random.metta in Python: exp, log, and the dice.

The engine computes `exp` and `log`; the subtraction, the absolute value and
the comparison that check them are Python's own, so the float-tolerance lines
read as ordinary Python and pay no crossing for the arithmetic around the
call. A nested call is BUILT with the static `fn` namespace and evaluated
once, so `(log-math e (exp-math 3.0))` is one term rather than two crossings,
which is the crossing rule as well as the spelling.

The original's `and` is a Python keyword, so the compiled body takes the exact
static-function escape, `fn["and"]`, while each comparison uses Python's
operator spelling and lowers to the corresponding engine relation.
"""

from metta import fn

#: e, to the precision the original writes it at.
E = 2.718281828459045

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1


def twin(m):
    """Check exp against its own inverse, then check the dice stay in range."""
    exp, log = m.fn.exp_math, m.fn.log_math

    assert exp(0) == [1.0]
    assert exp(1.0) == [E]
    assert abs(exp(2.0).one() - E * E) < 1.0e-12
    # log-math is the inverse: log base e of e^x is x, within float error.
    assert abs(log(E, fn.exp_math(3.0)).one() - 3.0) < 1.0e-12

    @m.define
    def in_range(lo, hi, x):
        # (= (in-range $lo $hi $x) (and (<= $lo $x) (<= $x $hi)))
        return fn["and"](lo <= x, x <= hi)  # rung: & is refused inside a compiled body, and `and` is a keyword

    # The random generators answer inside their bounds, every draw.
    assert in_range(1, 6, fn.random_int(1, 6)) == [True]
    assert in_range(0.0, 1.0, fn.random_float(0.0, 1.0)) == [True]
    assert in_range(5, 5, fn.random_int(5, 5)) == [True]
