"""Purpose: unit tests for the atom model and wire encoding, engine-free.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, Expr, Gnd, Sym, Var, alpha_eq, encode, expr, unify, val, variables
from petta.atoms import Box, from_wire, is_ground


def test_symbols_are_not_strings():
    assert S.foo == Sym("foo")
    assert S.foo != "foo"
    assert Gnd("foo") == "foo"
    assert S.foo != Gnd("foo")


def test_grounded_primitives_compare_as_their_value():
    assert Gnd(3) == 3
    assert Gnd(3.5) == 3.5
    assert Gnd(True) == True  # noqa: E712
    assert Gnd(True) != 1
    assert Gnd(1) != True  # noqa: E712
    assert Gnd("s") == "s"


def test_grounded_hash_agrees_with_equality():
    assert hash(Gnd(3)) == hash(3)
    assert {Gnd(3), 3} == {3}
    assert Gnd("a") in {"a"}


def test_expr_is_a_sequence():
    e = expr(S.a, 1, "s")
    assert len(e) == 3
    assert e[0] == S.a
    head, *args = e
    assert head == S.a and args == [Gnd(1), Gnd("s")]
    match e:
        case [h, *rest]:
            assert h == S.a and len(rest) == 2
        case _:
            raise AssertionError("sequence pattern did not match")


def test_symbol_application_builds_expressions():
    assert S.Parent(S.Tom, S.Bob) == expr(S.Parent, S.Tom, S.Bob)
    assert S.f(1, "x") == expr(S.f, 1, "x")


def test_atoms_are_immutable():
    with pytest.raises(AttributeError):
        S.foo.name = "bar"
    with pytest.raises(AttributeError):
        expr(S.a).children = ()


def test_printing_is_source_spelling():
    assert str(S.foo) == "foo"
    assert str(V.x) == "$x"
    assert str(Gnd(True)) == "True"
    assert str(Gnd('say "hi"')) == '"say \\"hi\\""'
    assert str(expr(S.a, 1, expr())) == "(a 1 ())"


def test_encode_python_values():
    assert encode(3) == Gnd(3)
    assert encode("s") == Gnd("s")
    assert encode([1, 2]) == expr(1, 2)
    assert encode((S.a, S.b)) == expr(S.a, S.b)
    assert encode(S.a) is S.a


def test_encode_metta_hook():
    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y

        def __metta__(self):
            return S.Point(self.x, self.y)

    assert encode(Point(1, 2)) == S.Point(1, 2)


def test_val_keeps_containers_whole_via_boxing():
    data = [1, 2, 3]
    wire = val(data).to_wire()
    assert wire[0] == "o" and isinstance(wire[1], Box) and wire[1].value is data
    assert from_wire(wire).value is data


def test_objects_cross_unboxed():
    class Thing:
        pass

    thing = Thing()
    wire = val(thing).to_wire()
    assert wire == ["o", thing]
    assert from_wire(wire).value is thing


def test_object_equality_is_identity():
    a, b = object(), object()
    assert val(a) == val(a)
    assert val(a) != val(b)
    assert val(a) == a


def test_wire_round_trip():
    atoms = [
        S.foo,
        V.x,
        Gnd(1),
        Gnd(2.5),
        Gnd(True),
        Gnd("text"),
        expr(S.a, expr(S.b, V.y), 3, "s", False),
        expr(),
    ]
    for a in atoms:
        assert from_wire(a.to_wire()) == a


def test_casting_protocol():
    assert int(Gnd(3)) == 3
    assert float(Gnd(3)) == 3.0
    assert int(Gnd(3.9)) == 3
    assert list(range(Gnd(3))) == [0, 1, 2]
    with pytest.raises(TypeError):
        int(Gnd("3"))
    with pytest.raises(TypeError):
        int(Gnd(True))
    with pytest.raises(TypeError):
        int(S.three)


def test_variables_and_groundness():
    assert variables(expr(S.f, V.x, expr(V.y, V.x))) == ["x", "y"]
    assert is_ground(expr(S.a, 1))
    assert not is_ground(V.x)


def test_alpha_eq():
    a = expr(S.f, V.x, V.y, V.x)
    b = expr(S.f, V.p, V.q, V.p)
    c = expr(S.f, V.p, V.q, V.q)
    assert alpha_eq(a, b)
    assert not alpha_eq(a, c)
    assert alpha_eq(S.a, S.a)
    assert not alpha_eq(S.a, S.b)


def test_unify():
    got = unify(S.Parent(V.x, S.Bob), S.Parent(S.Tom, S.Bob))
    assert got == {"x": S.Tom}
    assert unify(S.Parent(V.x, V.x), S.Parent(S.a, S.b)) is None
    assert unify(V.x, expr(S.a)) == {"x": expr(S.a)}
