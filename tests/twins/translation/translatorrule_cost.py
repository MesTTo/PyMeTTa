"""Purpose: exercise translator costs and conjunctive translator-rule heads.

Assumes:
  - the two declarations and six claims mirror the cost example
    [source: examples/translation/translatorrule_cost.metta lines 8-55; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - extraction follows the declared cost and the conjunctive rule joins through
    the surrounding space [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/translatorrule_cost.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 6308..6333 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
BUDGET = {
    "minimum": 6308,
    "maximum": 6333,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Register the costed and conjunctive rules, then exercise every case."""
    add_rule = m.fn("add-translator-rule!")

    m += S[":"](S.pow2, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.pow2(V.x)).to(S.noeval(S.mul(V.x, V.x)))
    add_rule(
        S.pow2,
        Expression((S.direction(S.bidirectional), S.cost(10))),
    )

    assert m.eval(S.pow2(3)) == [S.mul(3, 3)]

    large = S.a(S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert m.eval(S.mul(large, large)) == [S.pow2(large)]

    m += S.unit(S.mass, S.kg)
    m += S.unit(S.length, S.m)
    m += S[":"](S["unit-of"], S["->"](S.Atom, S["%Undefined%"]))

    conjuncts = Expression((S["unit-of"](V.q), S.unit(V.q, V.u)))
    add_rule(
        S["unit-of"],
        Expression((S.left(conjuncts), S.right(S["in"](V.u)))),
    )

    assert m.eval(S["unit-of"](S.mass)) == [S["in"](S.kg)]
    assert m.eval(S["unit-of"](S.length)) == [S["in"](S.m)]
    assert m.eval(S["unit-of"](S.time)) == []

    compiled = m[equation(S["unit-of"](V.q)).to(V.body)]
    assert [row.body[0] for row in compiled] == [S.match]
