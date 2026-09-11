"""Purpose: preserve the native rational species across Python atom operations.

Guarantees: decoded rationals retain numeric wire, value identity, hashing,
ordering, copy/pickle and storage; Python-created Fractions remain opaque
[tested: test_native_rational_wire_round_trip, test_native_rational_identity,
test_native_rational_storage_and_matching, test_native_number_order; commit=WORKTREE].
Owns resources: each storage probe drops its temporary space on every outcome.
"""

import copy
import math
import pickle
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Expression, G, Grounded, S, V, convert, unify
from metta._atoms.factories import order_key
from metta.structures import AlphaSet, MatchIndex, PatternMap


@pytest.mark.parametrize("value", [Fraction(1, 3), Fraction(-7, 2),
                                   Fraction((1 << 54) + 1, 1 << 1129)])
def test_native_rational_wire_round_trip(value):
    """Leaf, nested, sliced and rebuilt atoms resend the native number tag."""
    atom = convert.atom_from_wire(["n", value])
    nested = convert.atom_from_wire(["e", [["n", value], ["e", [["n", value]]]]])
    for candidate in (atom, nested[0], nested[1][0], nested[:1][0], Expression(atom)[0]):
        assert candidate.to_wire() == ["n", value]
        assert candidate.value == value
        assert convert.atom_from_wire(candidate.to_wire()) == candidate
    assert nested.to_wire() == ["e", [["n", value], ["e", [["n", value]]]]]


def test_native_rational_identity():
    """Native equality follows value, while a host Fraction still uses identity."""
    value = Fraction(1, 3)
    a = convert.atom_from_wire(["n", value])
    b = convert.atom_from_wire(["n", Fraction(2, 6)])
    host = G(value)
    assert a == b and b == a and hash(a) == hash(b)
    assert a != host
    assert host != a
    assert a != value
    assert value != a
    assert host == value and value == host
    assert G(Fraction(1, 3)) != host
    assert len({a, b, host}) == 2
    assert unify(a, b) == {}
    assert unify(a, host) is None
    assert Expression(a) == Expression(b)
    assert hash(Expression(a)) == hash(Expression(b))
    assert host.to_wire()[0] == "o"
    assert host.to_wire()[1].value is value


@pytest.mark.parametrize("value", [Fraction(0), Fraction(3), Fraction(-7)])
def test_integral_rational_wire_is_canonical(value):
    """Denominator one denotes the same engine term as the integer."""
    atom = convert.atom_from_wire(["n", value])
    assert atom == G(value.numerator)
    assert atom.to_wire() == ["n", value.numerator]
    assert type(atom.value) is int


def test_native_rational_copy_pickle_and_format():
    """The immutable numeric atom can be serialized and formatted by value."""
    atom = convert.atom_from_wire(["n", Fraction(1, 3)])
    assert copy.copy(atom) is atom and copy.deepcopy(atom) is atom
    restored = pickle.loads(pickle.dumps(Expression(atom)))
    assert restored == Expression(atom)
    assert restored[0].to_wire() == atom.to_wire()
    assert str(atom) == "1r3"
    assert format(atom, ".3f") == "0.333"
    assert float(atom) == 1 / 3
    assert 0 < atom < 1
    assert 1 > atom > 0
    with pytest.raises(TypeError, match="process-local identity"):
        pickle.dumps(G(Fraction(1, 3)))


def test_native_rational_storage_and_matching(metta):
    """Independent decodes match the same stored native term and index entry."""
    a = convert.atom_from_wire(["n", Fraction(1, 3)])
    b = convert.atom_from_wire(["n", Fraction(2, 6)])
    with metta._new_space() as stored:
        stored.add(S.rational(a))
        assert len(stored.match(S.rational(b))) == 1
        row = stored.match(S.rational(V.x))[0]
        assert row.x == b
        assert row.x.to_wire() == ["n", Fraction(1, 3)]
    assert b in AlphaSet([a])
    table = PatternMap([(S.rational(a), "value")])
    assert table[S.rational(b)] == "value"
    index = MatchIndex()
    index.add(S.rational(a), "value")
    assert [value for _, value in index.matches(S.rational(b))] == ["value"]


NUMBERS = [math.nan, -math.inf, -(1 << 3000), -1, -0.0, 0.0, 0,
           Fraction(1, 10), 0.1, 0.5, Fraction(1, 2), 1, 1 << 3000, math.inf]


@settings(max_examples=100)
@given(st.permutations(NUMBERS))
def test_native_number_order(metta, values):
    """Native rational, integer and IEEE ordering agrees with SWI msort."""
    atoms = [convert.atom_from_wire(["n", value]) for value in values]
    row = metta.runtime.must(
        "metta_py_decode_shared(W,_Terms,_),msort(_Terms,_Sorted),metta_py_encode(_Sorted,Out)",
        W=Expression(atoms).to_wire(),
    )
    expected = convert.atom_from_wire(row["Out"])
    assert Expression(sorted(atoms, key=order_key)) == expected
    assert Expression(sorted(atoms)) == expected


def test_native_rational_sorts_before_an_opaque_numeric_subclass():
    """A Python float subclass retains its object-channel kind when sorting."""
    class FloatObject(float):
        pass

    rational = convert.atom_from_wire(["n", Fraction(1, 3)])
    opaque = Grounded(FloatObject(-100))
    assert opaque.to_wire()[0] == "o"
    assert sorted([opaque, rational]) == [rational, opaque]
