"""Purpose: exercise forward and bidirectional translator-rule declarations.

Assumes:
  - the rule metadata and six claims mirror the direction example
    [source: examples/translation/translatorrule_direction.metta lines 8-46; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - the inverse fires only while its bidirectional declaration is installed
    [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/translatorrule_direction.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 8926..8978 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
BUDGET = {
    "minimum": 8926,
    "maximum": 8978,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Register both direction policies, exercise them, then withdraw one."""
    add_rule = m.fn("add-translator-rule!")

    m += S[":"](S.celsius, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.celsius(S.degrees(V.c))).to(
        S.noeval(S.kelvin(V.c + 273))
    )
    add_rule(S.celsius, Expression((S.direction(S.forward),)))

    assert m.eval(S.celsius(S.degrees(27))) == [S.kelvin(300)]

    m += S[":"](S.unpack, S["->"](S.Atom, S["%Undefined%"]))
    m += equation(S.unpack(S.wrap(S.box(V.x)))).to(
        S.noeval(S.twin(V.x, V.x))
    )
    add_rule(S.unpack, Expression((S.direction(S.bidirectional),)))

    small = S.twin(1, 1)
    small_unpack = S.unpack(S.wrap(S.box(1)))
    large = S.a(S.b, S.c)
    large_twin = S.twin(large, large)
    large_unpack = S.unpack(S.wrap(S.box(large)))

    assert m.eval(small_unpack) == [small]
    assert m.eval(large_twin) == [large_unpack]
    assert m.eval(small) == [small_unpack]
    assert m.eval(large_unpack) == [large_unpack]

    m.fn("remove-translator-rule!")(S.unpack)

    assert m.eval(large_twin) == [large_twin]
