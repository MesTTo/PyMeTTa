"""Purpose: unit tests for the atom model and wire encoding, engine-free.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import copy
import multiprocessing
import pickle
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
from fractions import Fraction

import pytest

from petta import (
    Expr,
    Gnd,
    S,
    Sym,
    V,
    alpha_eq,
    encode,
    expr,
    map_atoms,
    unify,
    val,
    variables,
)
from petta.atoms import Box, atom_from_wire, from_wire, is_ground


def test_symbols_are_not_strings():
    assert S.foo == Sym("foo")
    assert S.foo != "foo"
    assert Gnd("foo") == "foo"
    assert S.foo != Gnd("foo")


def test_map_atoms_transforms_bottom_up_and_preserves_unchanged_nodes():
    atom = S.outer(S.inner(S.before), S.keep)
    assert map_atoms(atom, lambda node: node) is atom

    mapped = map_atoms(
        atom,
        lambda node: S.after if node is S.before else node,
    )
    assert mapped == S.outer(S.inner(S.after), S.keep)


def test_map_atoms_handles_depth_as_data_and_validates_transform_results():
    atom = S.leaf
    for _ in range(2_000):
        atom = Expr([atom])

    mapped = map_atoms(atom, lambda node: S.tip if node is S.leaf else node)
    for _ in range(2_000):
        assert isinstance(mapped, Expr)
        mapped = mapped[0]
    assert mapped is S.tip

    with pytest.raises(TypeError, match="transform must return an Atom"):
        map_atoms(S.leaf, lambda _node: None)


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


def test_numpy_scalars_are_engine_numbers(metta):
    np = pytest.importorskip("numpy")
    cases = [np.int32(7), np.int64(2), np.float32(1.5), np.float64(3.5)]
    for scalar in cases:
        atom = Gnd(scalar)
        expected = int(scalar) if isinstance(scalar, np.integer) else float(scalar)
        assert type(atom.value) is type(expected)
        assert atom == scalar
        assert atom.to_wire() == ["n", expected]
        assert str(atom) == repr(expected)
        assert metta.eval(expr(S["+"], atom, 1)) == [Gnd(expected + 1)]


def test_non_real_numpy_values_stay_opaque():
    np = pytest.importorskip("numpy")
    for value in (np.bool_(True), np.array([1.0])):
        atom = Gnd(value)
        assert atom.value is value
        assert atom.to_wire()[0] == "o"


def test_numbers_tower_reals_normalize_and_non_reals_stay_opaque():
    real = Gnd(Fraction(3, 2))
    assert type(real.value) is float
    assert real.to_wire() == ["n", 1.5]

    decimal = Decimal("1.5")
    opaque = Gnd(decimal)
    assert opaque.value is decimal
    assert opaque.to_wire()[0] == "o"


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


def test_expr_sequence_index_and_count():
    atom = expr(S.f, S.a, S.b, S.a)
    assert atom.index(S.a) == 1
    assert atom.index(S.a, 2) == 3
    assert atom.count(S.a) == 2
    with pytest.raises(ValueError):
        atom.index(S.missing)


def test_expr_identity_equality():
    shared = expr(S.node, S.leaf)
    atom = expr(S.root, shared, shared)
    assert atom == atom
    assert atom == expr(S.root, shared, shared)


def test_symbol_application_builds_expressions():
    assert S.Parent(S.Tom, S.Bob) == expr(S.Parent, S.Tom, S.Bob)
    assert S.f(1, "x") == expr(S.f, 1, "x")


def test_atoms_are_immutable():
    with pytest.raises(AttributeError):
        S.foo.name = "bar"
    with pytest.raises(AttributeError):
        expr(S.a).children = ()


@pytest.mark.parametrize(
    "atom",
    [S.foo, V.x, Gnd(3), Gnd("text"), expr(S.f, S.a, Gnd(2))],
)
def test_atoms_copy_by_identity(atom):
    assert copy.copy(atom) is atom
    assert copy.deepcopy(atom) is atom


@pytest.mark.parametrize(
    "atom",
    [S.foo, V.x, Gnd(3), Gnd("text"), expr(S.f, S.a, Gnd(2))],
)
def test_atoms_pickle_by_value(atom):
    restored = pickle.loads(pickle.dumps(atom))
    assert restored == atom
    assert type(restored) is type(atom)


def test_process_local_grounded_values_refuse_pickle():
    value = object()
    for identity_value in (Gnd(value), Box(value)):
        with pytest.raises(TypeError, match="process-local.*identity"):
            pickle.dumps(identity_value)


def test_atoms_cross_a_spawned_process_boundary():
    atom = expr(S.edge, S.Ada, Gnd(3))
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        restored = pool.submit(pickle.loads, pickle.dumps(atom)).result(timeout=15)
    assert restored == atom


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


def test_every_object_crosses_boxed():
    # Uniformly boxed: which types janus rewrites is janus's decision, so no
    # object crosses bare, and unboxing is every consumer's first move.
    class Thing:
        pass

    thing = Thing()
    wire = val(thing).to_wire()
    assert wire[0] == "o" and isinstance(wire[1], Box) and wire[1].value is thing
    assert from_wire(wire).value is thing
    already = val(thing)
    assert val(already.value).to_wire()[1].value is thing


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


def test_wire_intern_tables_are_bounded():
    from petta.atoms import (
        _WIRE_CACHE_FAST_MAX,
        _WIRE_CACHE_MAX,
        _WIRE_SYMS,
        _WIRE_SYMS_FAST,
        _WIRE_VARS,
        _WIRE_VARS_FAST,
    )

    for cache in (_WIRE_SYMS, _WIRE_SYMS_FAST, _WIRE_VARS, _WIRE_VARS_FAST):
        cache.clear()

    first_sym = from_wire(["s", "evicted"])
    first_var = from_wire(["v", "evicted"])
    for index in range(_WIRE_CACHE_MAX + _WIRE_CACHE_FAST_MAX + 10):
        from_wire(["s", f"symbol-{index}"])
        from_wire(["v", f"variable-{index}"])

    assert len(_WIRE_SYMS) <= _WIRE_CACHE_MAX
    assert len(_WIRE_VARS) <= _WIRE_CACHE_MAX
    assert len(_WIRE_SYMS_FAST) <= _WIRE_CACHE_FAST_MAX
    assert len(_WIRE_VARS_FAST) <= _WIRE_CACHE_FAST_MAX
    assert from_wire(["s", "symbol-0"]) is from_wire(["s", "symbol-0"])
    assert from_wire(["v", "variable-0"]) is from_wire(["v", "variable-0"])
    assert from_wire(["s", "evicted"]) == first_sym
    assert from_wire(["s", "evicted"]) is not first_sym
    assert from_wire(["v", "evicted"]) == first_var
    assert from_wire(["v", "evicted"]) is not first_var


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


def test_ground_equality_is_the_engines():
    """Python-side == must never disagree with an equation's ==: booleans
    are not integers, integers are not floats, IEEE identity for floats
    with -0.0 apart from 0.0 and NaN equal to itself, objects by identity."""
    assert Gnd(1) != Gnd(1.0)
    assert Gnd(1.0) == Gnd(1.0)
    assert Gnd(0.0) != Gnd(-0.0)
    nan = float("nan")
    assert Gnd(nan) == Gnd(nan)
    assert Gnd(True) != Gnd(1)
    assert Gnd(1) == 1 and Gnd(1) != 1.0
    assert unify(Gnd(1), Gnd(1.0)) is None
    assert unify(Gnd(nan), Gnd(nan)) == {}


def test_boxes_intern_per_object_identity():
    """One live object always crosses as one box, so stored and queried
    meet in the same reference; a dead object costs nothing after."""
    from petta.atoms import boxed

    thing = object()
    assert boxed(thing) is boxed(thing)
    assert boxed(thing).value is thing


def test_deep_terms_cross_and_print():
    """Depth is data: the codec and the printer take 5000 levels without
    meeting Python's recursion ceiling."""
    from petta.atoms import from_wire

    atom = Gnd(1)
    for _ in range(5000):
        atom = expr(S.wrap, atom)
    assert from_wire(atom.to_wire()) == atom
    assert str(atom).startswith("(wrap (wrap")
    assert variables(atom) == []


def test_malformed_wire_is_refused():
    from petta.atoms import from_wire

    for bad in (["b", "garbage"], ["n", "123"], ["s", 123], ["e", 5], ["zz", 1]):
        with pytest.raises(ValueError):
            from_wire(bad)


def test_atom_from_wire_rejects_undefined_truth():
    with pytest.raises(ValueError, match="valid only as a complete evaluation answer"):
        atom_from_wire(["u", ["s", "answer"], "delayed_goal"])


def test_anonymous_variable_is_fresh_per_occurrence():
    assert unify(S.pair(V._, V._), S.pair(S.a, S.b)) == {}
    assert unify(S.pair(V._, V._), S.pair(S.a, S.a)) == {}
