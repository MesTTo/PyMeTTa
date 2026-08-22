"""examples/libraries/he_math.metta in Python: the engine's numeric library, checked.

Twenty-four claims about the `*-math` family and the two atom-level extrema.
Every one of them names the operation it is about, because the operations ARE
the subject: real-valued math promotes integers, `pow-math` answers a Float
while enforcing the signed-i32 bound only for integer exponents, and the
nan/inf predicates are how a caller finds out.

Nesting is Python's, so `(isnan-math (sqrt-math -1))` is one call inside
another; and the two special float symbols are what the engine names them,
`inf` and `nan`.
"""

from petta import S

#: Why this twin sits below the top rung: `min-atom` and `max-atom` dissolve
#: into Python's `min` and `max` everywhere else in the corpus, and here they
#: are two of the numeric operations under test, so a Python max over a Python
#: tuple would check Python rather than the engine.
RUNG = "min-atom and max-atom are two of the stdlib numeric operations this file checks, not a request to take a maximum"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13255 to 3148, -10107 (-76.25%), by the idiomatic
#: rewrite: twenty-four `test` wrappers left the engine, which is three
#: quarters of this file: twenty-four numeric calls and two nested ones are
#: all that is left, and nothing here imports a library. Measured min-of-
#: three with the MORK backend linked into this worktree, which the earlier
#: figure may not have been. Prior: 13255 was the last figure for the
#: generator twin that yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 3148


def twin(m):
    """Ask each numeric operation for its answer."""
    pow_math, sqrt_math = m.fn("pow-math"), m.fn("sqrt-math")
    isnan, isinf = m.fn("isnan-math"), m.fn("isinf-math")

    assert pow_math(2, 3) == 8.0
    assert isnan(sqrt_math(-1)) is True
    assert isinf(pow_math(0, -1)) is True
    # The signed-i32 bound is enforced only for INTEGER exponents.
    assert pow_math(1, 2147483648.0) == 1.0
    assert sqrt_math(9) == 3.0
    assert m.fn("abs-math")(-5) == 5
    assert m.fn("log-math")(10, 100) == 2.0

    assert m.fn("trunc-math")(5.6) == 5
    assert m.fn("ceil-math")(5.2) == 6
    assert m.fn("floor-math")(5.8) == 5
    round_math = m.fn("round-math")
    assert round_math(5.4) == 5
    assert round_math(5.6) == 6

    assert m.fn("sin-math")(0) == 0.0
    assert m.fn("asin-math")(0) == 0.0
    assert m.fn("cos-math")(0) == 1.0
    assert m.fn("acos-math")(1) == 0.0
    assert m.fn("tan-math")(0) == 0.0
    assert m.fn("atan-math")(0) == 0.0

    assert isnan(0.0) is False
    assert isinf(0.0) is False

    assert m.fn("min-atom")((2, 6, 7, 4, 9, 3)) == 2
    assert m.fn("max-atom")((2, 6, 7, 4, 9, 3)) == 9

    assert isinf(S.inf) is True
    assert isnan(S.nan) is True
