"""Purpose: spell the cyclic higher-order specialization example in Python.

Assumes:
  - the four equations and two runnable claims mirror
    examples/functions/specializecyclic.metta in source order
    [source: examples/functions/specializecyclic.metta lines 1-15; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - twin installs every equation and proves both runnable claims
    [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/functions/specializecyclic.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, equation, rules

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 26325..26409 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
BUDGET = {
    "minimum": 26325,
    "maximum": 26409,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}
RUNG = "cyclic rule equations need engine-time conditionals and variable-headed calls"


@rules
def cyclic_specialization(f, a, n):
    """The mutually recursive equations, admitted as one rule bundle."""
    yield equation(S.f1(f, a)).to(
        S["if"](
            a < 0,
            Expression((f, S.nevercalled, 42)),
            S["if"](a.eq(0), S.f2(f, a - 1), S.finish),
        )
    )
    yield equation(S.f2(f, a)).to(
        S["if"](a < 0, Expression((f, S.nevercalled, 42)), S.f1(f, a))
    )
    yield equation(S.f3(f, n)).to(
        S["if"](n.eq(0), S.finish, S.f4(f, n))
    )
    yield equation(S.f4(f, n)).to(S.f3(f, n - 1))


def twin(m):
    """Install both cycles and ask each one through the same function value."""
    m.add(*cyclic_specialization)

    assert m.eval(S.f1(S["+"], 2)) == [S.finish]
    assert m.eval(S.f3(S["+"], 1)) == [S.finish]
