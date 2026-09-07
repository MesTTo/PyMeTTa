"""examples/ch05-equations-and-evaluation/05-04-arithmetic-that-runs-backwards/04-relational_integer_division.metta in Python: truncating against flooring.

`#//` and `#div` have no Python spelling and want none: they are CLP(FD)
constraints rather than evaluations, and running in either direction is the
point. The subscript door names them exactly, because neither is an
identifier and Python's own `//` is a different operation on a different
domain.

Two doors, one per job, the same split `02-relational_arithmetic.py` uses.
`m.fn["#//"]` CALLS the constraint; the static `fn["#//"]` BUILDS the term,
which is what a backward query needs, since what is being solved for has to
reach the engine unevaluated.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, S, V, fn


def twin(m):
    """The two integer divisions, forwards, on negatives, and backwards."""
    truncating, flooring = m.fn["#//"], m.fn["#div"]

    # On non-negative operands they agree.
    assert truncating(7, 2) == [3]
    assert flooring(7, 2) == [3]

    # A negative operand is where they part: -3.5 truncates toward zero and
    # floors away from it.
    assert truncating(-7, 2) == [-3]
    assert flooring(-7, 2) == [-4]
    assert truncating(7, -2) == [-3]
    assert flooring(7, -2) == [-4]

    # `#div` and `#mod` round the same way, so quotient times divisor plus
    # remainder reconstructs the dividend. `#//` has no matching remainder in
    # this surface -- there is no `#rem` -- so the same sum is off by the
    # divisor, which is exactly the gap between truncating and flooring.
    # Built rather than computed in Python: `*` and `+` on atoms BUILD the
    # term, which is what makes one claim one engine evaluation.
    assert m.answers(fn["#div"](-7, 2) * 2 + fn["#mod"](-7, 2)) == [-7]
    assert m.answers(fn["#//"](-7, 2) * 2 + fn["#mod"](-7, 2)) == [-5]

    # Backwards: the quotient and the dividend are known, the divisor is not.
    assert m.solve(3, fn["#//"](7, V.d)).d == 2

    # The other direction is a relation rather than a function, because
    # truncation loses information: 6 and 7 both divide to 3. A second
    # constraint decides it, and the two have to be posted and asked inside
    # ONE derivation, which is `(let True <constraint> <question>)`; `m.solve`
    # does not reach it, and the residue table records that guard against
    # P14.4.
    quotient = S.let(3, fn["#//"](V.n, 2), V.n)  # rung: let as a binder
    assert m.answers(S.let(TRUE, fn["#<"](V.n, 7), quotient)) == [6]  # rung: let as a guard
    assert m.answers(S.let(TRUE, fn["#>"](V.n, 6), quotient)) == [7]  # rung: let as a guard


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 8613 inferences, 0.9070x the example's 9496; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 8613
