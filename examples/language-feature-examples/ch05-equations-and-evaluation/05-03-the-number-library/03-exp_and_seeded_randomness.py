"""examples/ch05-equations-and-evaluation/05-03-the-number-library/03-exp_and_seeded_randomness.metta in Python: e, and a repeatable draw.

`exp` and `exp-math` are two names for one operation, so the twin calls both
through the function namespace and compares them.

`with-seed` HOLDS its body, and that is what decides the Python spelling: the
body is built as an ATOM with `S`, never called, and handed over. `S.random_int(0, 100)`
is the expression `(random-int 0 100)` as data, so the scope receives a
program rather than a number the host already drew.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S

#: The body every seeded claim runs, built once because it is data.
ONE_DRAW = S.random_int(0, 100)

#: A draw NESTED inside another call, so the claim is about the body's whole
#: extent rather than about its outermost operation.
NESTED_DRAW = S.abs_math(S.random_int(-100, 100))


def twin(m):
    """E to a power, and a random draw that repeats."""
    assert m.fn.exp(0) == [1.0]
    assert m.fn.exp(1) == [2.718281828459045]
    assert m.fn.exp(2) == m.fn.exp_math(2)

    # The same seed draws the same number, which is what makes a randomised
    # program testable: the draw stays random and the RUN stops being.
    assert m.fn.with_seed(42, ONE_DRAW) == m.fn.with_seed(42, ONE_DRAW)

    # The scope is the body's whole dynamic extent, so a draw buried inside
    # the body is seeded too.
    assert m.fn.with_seed(7, NESTED_DRAW) == m.fn.with_seed(7, NESTED_DRAW)

    # A different seed is a different sequence, so the seed is doing work
    # rather than switching randomness off.
    assert m.fn.with_seed(42, ONE_DRAW) != m.fn.with_seed(43, ONE_DRAW)

    # One generator serves both draws, so the scope reaches `random-float` too.
    float_draw = S.random_float(0.0, 1.0)
    assert m.fn.with_seed(5, float_draw) == m.fn.with_seed(5, float_draw)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. min-of-3 in fresh processes
#: [measured 2026-09-07: 3991 inferences, 0.5639x the example's 7077; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch05-equations-and-evaluation/05-03-the-number-library/03-exp_and_seeded_randomness.metta;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 3991
