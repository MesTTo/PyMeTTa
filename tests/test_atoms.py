"""Purpose: unit tests for the atom model and wire encoding, engine-free.
Owns:
  - test_atom_identity_caches_are_thread_safe joins every cache worker
    before checking identity [tested test_atom_identity_caches_are_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import copy
import inspect
import json
import multiprocessing
import pickle
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from decimal import Decimal
from fractions import Fraction

import pytest

from petta import (
    Expression,
    Grounded,
    S,
    Symbol,
    V,
    Variable,
    _engine,
    ground,
    integrate,
    parse,
    unify,
    wire,
)
from petta import _atoms_core as _core
from petta.atoms import (
    _NAMESPACE_CACHE_MAX,
    _WIRE_CACHE_MAX,
    _WIRE_SYMS,
    _WIRE_VARS,
    Box,
    boxed,
    order_key,
    register_object_repr,
    unregister_object_repr,
)


def test_symbols_are_not_strings():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert S.foo == Symbol("foo")
    assert S.foo != "foo"
    assert Grounded("foo") == "foo"
    assert S.foo != Grounded("foo")


def test_object_repr_registrations_can_be_removed_exactly():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class RenderedByClass:
        pass

    class RenderedByProtocol:
        pass

    def class_formatter(_value):
        return "<class formatter>"

    def predicate(value):
        return isinstance(value, RenderedByProtocol)

    def protocol_formatter(_value):
        return "<protocol formatter>"

    register_object_repr(RenderedByClass, class_formatter)
    integrate.register_repr(predicate, protocol_formatter)
    try:
        assert str(ground(RenderedByClass())) == "<class formatter>"
        assert str(ground(RenderedByProtocol())) == "<protocol formatter>"
    finally:
        unregister_object_repr(RenderedByClass)
        integrate.unregister_repr(predicate, protocol_formatter)

    assert str(ground(RenderedByClass())) == "<RenderedByClass>"
    assert str(ground(RenderedByProtocol())) == "<RenderedByProtocol>"
    with pytest.raises(KeyError, match="RenderedByClass"):
        unregister_object_repr(RenderedByClass)
    with pytest.raises(KeyError, match="protocol repr"):
        integrate.unregister_repr(predicate, protocol_formatter)


def test_map_atoms_transforms_bottom_up_and_preserves_unchanged_nodes():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atom = S.outer(S.inner(S.before), S.keep)
    assert atom.map(lambda node: node) is atom

    mapped = atom.map(
        lambda node: S.after if node is S.before else node,
    )
    assert mapped == S.outer(S.inner(S.after), S.keep)


def test_map_atoms_handles_depth_as_data_and_validates_transform_results():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atom = S.leaf
    for _ in range(2_000):
        atom = Expression([atom])

    mapped = atom.map(lambda node: S.tip if node is S.leaf else node)
    for _ in range(2_000):
        assert isinstance(mapped, Expression)
        mapped = mapped[0]
    assert mapped is S.tip

    with pytest.raises(TypeError, match="transform must return an Atom"):
        S.leaf.map(lambda _node: None)


def test_grounded_primitives_compare_as_their_value():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert Grounded(3) == 3
    assert Grounded(3.5) == 3.5
    assert Grounded(True) == True  # noqa: E712, FBT003  -- the assertion probes bool equality without coercion; the boolean literal is atom or wire data at this site, not a behavior switch
    assert Grounded(True) != 1  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert Grounded(1) != True  # noqa: E712
    assert Grounded("s") == "s"


def test_grounded_hash_agrees_with_equality():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert hash(Grounded(3)) == hash(3)
    assert {Grounded(3), 3} == {3}
    strings = {"a"}
    assert Grounded("a") in strings


def test_numpy_scalars_are_engine_numbers(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    np = pytest.importorskip("numpy")
    cases = [np.int32(7), np.int64(2), np.float32(1.5), np.float64(3.5)]
    for scalar in cases:
        atom = Grounded(scalar)
        expected = int(scalar) if isinstance(scalar, np.integer) else float(scalar)
        assert type(atom.value) is type(expected)
        assert atom == scalar
        assert atom.to_wire() == ["n", expected]
        assert str(atom) == repr(expected)
        assert metta.eval(Expression(S["+"], atom, 1)) == [Grounded(expected + 1)]


def test_non_real_numpy_values_stay_opaque():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    np = pytest.importorskip("numpy")
    for value in (np.bool_(True), np.array([1.0])):  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        atom = Grounded(value)
        assert atom.value is value
        assert atom.to_wire()[0] == "o"


def test_numbers_tower_reals_normalize_and_non_reals_stay_opaque():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    real = Grounded(Fraction(3, 2))
    assert type(real.value) is float
    assert real.to_wire() == ["n", 1.5]

    decimal = Decimal("1.5")
    opaque = Grounded(decimal)
    assert opaque.value is decimal
    assert opaque.to_wire()[0] == "o"


def test_expr_is_a_sequence():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    e = Expression(S.a, 1, "s")
    assert len(e) == 3
    assert e[0] == S.a
    head, *args = e
    assert head == S.a and args == [Grounded(1), Grounded("s")]
    match e:
        case [h, *rest]:
            assert h == S.a and len(rest) == 2
        case _:
            msg = "sequence pattern did not match"
            raise AssertionError(msg)


def test_expr_sequence_index_and_count():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atom = Expression(S.f, S.a, S.b, S.a)
    assert atom.index(S.a) == 1
    assert atom.index(S.a, 2) == 3
    assert atom.count(S.a) == 2
    with pytest.raises(ValueError):
        atom.index(S.missing)


def test_expr_identity_equality():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    shared = Expression(S.node, S.leaf)
    atom = Expression(S.root, shared, shared)
    same = atom
    assert atom == same
    assert atom == Expression(S.root, shared, shared)


def test_symbol_application_builds_expressions():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert S.Parent(S.Tom, S.Bob) == Expression(S.Parent, S.Tom, S.Bob)
    assert S.f(1, "x") == Expression(S.f, 1, "x")


def test_atoms_are_immutable():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(AttributeError):
        S.foo.name = "bar"
    with pytest.raises(AttributeError):
        Expression(S.a).children = ()


@pytest.mark.parametrize(
    "atom",
    [S.foo, V.x, Grounded(3), Grounded("text"), Expression(S.f, S.a, Grounded(2))],
)
def test_atoms_copy_by_identity(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert copy.copy(atom) is atom
    assert copy.deepcopy(atom) is atom


@pytest.mark.parametrize(
    "atom",
    [S.foo, V.x, Grounded(3), Grounded("text"), Expression(S.f, S.a, Grounded(2))],
)
def test_atoms_pickle_by_value(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    restored = pickle.loads(pickle.dumps(atom))
    assert restored == atom
    assert type(restored) is type(atom)


def test_process_local_grounded_values_refuse_pickle():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    value = object()
    for identity_value in (Grounded(value), Box(value)):
        with pytest.raises(TypeError, match=r"process-local.*identity"):
            pickle.dumps(identity_value)


def test_atoms_cross_a_spawned_process_boundary():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atom = Expression(S.edge, S.Ada, Grounded(3))
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        restored = pool.submit(pickle.loads, pickle.dumps(atom)).result(timeout=15)
    assert restored == atom


def test_printing_is_source_spelling():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert str(S.foo) == "foo"
    assert str(V.x) == "$x"
    assert str(Grounded(True)) == "True"  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert str(Grounded('say "hi"')) == '"say \\"hi\\""'
    assert str(Expression(S.a, 1, Expression())) == "(a 1 ())"


def test_encode_python_values():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert wire.encode(3) == Grounded(3)
    assert wire.encode("s") == Grounded("s")
    assert wire.encode([1, 2]) == Expression(1, 2)
    assert wire.encode((S.a, S.b)) == Expression(S.a, S.b)
    assert wire.encode(S.a) is S.a


def test_the_type_fast_path_precedes_encode_and_survives_a_register():
    """Encode answers common types from a table keyed on the exact class,
    and every registration rebuilds that table.

    Measured 2026-08-19 over 800,000 calls, minimum of three instructions:u
    runs with the same loop calling nothing subtracted: 4,603 instructions
    per encode through the bare singledispatch against 2,309 with the table
    in front, 1.99x.

    The table is built by asking encode.dispatch, so it cannot answer
    differently from the registry it came from; the one private assertion
    here says exactly that, and everything else drives encode itself. What
    it guards is a table that keeps answering the old way after someone
    registers a codec, which would be a correctness bug traded for 2,294
    instructions.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    class Celsius:
        def __init__(self, degrees):
            self.degrees = degrees

    # Unregistered: carried whole, the generic rule.
    reading = Celsius(20)
    assert wire.encode(reading) == Grounded(reading)

    # A type ALREADY in the fast table. Re-registering it must take effect,
    # which is the half a stale table gets wrong.
    # Each replacement answers a bare symbol, so nothing here re-enters
    # encode while its own type is registered differently.
    original_int = wire.encode.registry[int]
    original_str = wire.encode.registry[str]
    try:
        wire.encode.register(int, lambda value: Symbol(f"counted-{value}"))
        assert wire.encode(7) == Symbol("counted-7")

        @wire.encode.register(Celsius)
        def _(value):
            return Symbol(f"celsius-{value.degrees}")

        assert wire.encode(Celsius(20)) == Symbol("celsius-20")

        @wire.encode.register
        def _(value: str) -> Symbol:
            return Symbol(f"text-{len(value)}")

        assert wire.encode("abcd") == Symbol("text-4")

        assert _core._ENCODE_FAST[int] is wire.encode.dispatch(int)
        assert _core._ENCODE_FAST[Celsius] is wire.encode.dispatch(Celsius)
        assert _core._ENCODE_FAST[str] is wire.encode.dispatch(str)
    finally:
        wire.encode.register(int, original_int)
        wire.encode.register(str, original_str)

    assert wire.encode(7) == Grounded(7)
    assert wire.encode("abcd") == Grounded("abcd")
    assert wire.encode(2.5) == Grounded(2.5)
    assert wire.encode(True) == Grounded(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert wire.encode([1, 2]) == Expression(1, 2)
    assert wire.encode((S.a,)) == Expression(S.a)
    assert wire.encode(S.a) is S.a
    assert wire.encode(V.x) is V.x
    shared = Expression(S.f, 1)
    assert wire.encode(shared) is shared


def test_encode_metta_hook():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y

        def __metta__(self):
            return S.Point(self.x, self.y)

    assert wire.encode(Point(1, 2)) == S.Point(1, 2)


def test_val_keeps_containers_whole_via_boxing():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    data = [1, 2, 3]
    encoded = ground(data).to_wire()
    assert encoded[0] == "o" and isinstance(encoded[1], Box) and encoded[1].value is data
    assert wire.from_wire(encoded).value is data


def test_every_object_crosses_boxed():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Uniformly boxed: which types janus rewrites is janus's decision, so no
    # object crosses bare, and unboxing is every consumer's first move.
    class Thing:
        pass

    thing = Thing()
    encoded = ground(thing).to_wire()
    assert encoded[0] == "o" and isinstance(encoded[1], Box) and encoded[1].value is thing
    assert wire.from_wire(encoded).value is thing
    already = ground(thing)
    assert ground(already.value).to_wire()[1].value is thing


def test_object_equality_is_identity():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a, b = object(), object()
    assert ground(a) == ground(a)
    assert ground(a) != ground(b)
    assert ground(a) == a


def test_wire_round_trip():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atoms = [
        S.foo,
        V.x,
        Grounded(1),
        Grounded(2.5),
        Grounded(True),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        Grounded("text"),
        Expression(S.a, Expression(S.b, V.y), 3, "s", False),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        Expression(),
    ]
    for a in atoms:
        assert wire.from_wire(a.to_wire()) == a


def test_expr_defers_its_wire_form_until_asked():
    """An expression builds its wire form on the first crossing, not before.

    Reads the private `_wire` slot, which is the only way to tell a slot
    that was never written from one written with an equal value. That one
    peek is the whole reason this test is not blackbox; everything else
    here goes through to_wire().
    """
    unset = object()
    atom = Expression(S.node, 1, Expression(S.inner, V.x), "text")

    # Construction writes nothing: the slot is absent, not None.
    assert getattr(atom, "_wire", unset) is unset
    assert getattr(atom.children[2], "_wire", unset) is unset

    encoded = atom.to_wire()
    assert encoded == [
        "e",
        [["s", "node"], ["n", 1], ["e", [["s", "inner"], ["v", "x"]]], ["g", "text"]],
    ]

    # Asking populated it, and asking again answers the very same list
    # rather than rebuilding one that compares equal.
    assert getattr(atom, "_wire", unset) is encoded
    assert atom.to_wire() is encoded
    assert wire.from_wire(encoded) == atom

    # A child expression stays deferred until it is crossed on its own.
    inner = atom.children[2]
    assert getattr(inner, "_wire", unset) is unset
    assert inner.to_wire() is inner.to_wire()

    # The empty expression is not a special case.
    empty = Expression()
    assert getattr(empty, "_wire", unset) is unset
    assert empty.to_wire() == ["e", []]
    assert empty.to_wire() is empty.to_wire()


def test_the_intern_cache_evicts_in_constant_time(monkeypatch):
    """Interning a fresh name costs the same at a bound of 512 and of 65,536.

    Eviction used to be `del cache[next(iter(cache))]`. A dict's iterator
    walks the entry array from the front, every eviction leaves a tombstone
    there, and the scan grows with the churn: measured 796 ns per miss at a
    bound of 512 against 2,496 ns at 65,536, 3.13x [measured 2026-08-19].
    That coupling is why the cache could not be made larger.

    Timed rather than asserted structurally, because which container
    delivers the property is an implementation detail and the cost is the
    claim. Minimum of three rounds per arm, and the threshold sits at 1.6x
    between the measured 3.13x defect and the 1.14x fix.

    Also checks the one invariant the O(1) form introduces: the key order
    that bounds the cache holds exactly the cache's keys. Two structures
    can drift, so their agreement is asserted rather than assumed.
    """
    churn = 30_000

    def nanoseconds_per_miss(bound, tag):
        monkeypatch.setattr(_core, "_WIRE_CACHE_MAX", bound)
        best = None
        for round_index in range(3):
            _core._wire_intern_clear()
            prefix = f"{tag}-{round_index}"
            for index in range(bound):
                wire.from_wire(["s", f"{prefix}-fill-{index}"])
            start = time.perf_counter()
            for index in range(churn):
                wire.from_wire(["s", f"{prefix}-churn-{index}"])
            elapsed = time.perf_counter() - start
            if best is None or elapsed < best:
                best = elapsed
        return best / churn * 1e9

    try:
        small = nanoseconds_per_miss(512, "small")
        large = nanoseconds_per_miss(65_536, "large")
        assert large < small * 1.6, (
            f"interning a fresh name costs {large:.0f} ns at a bound of 65,536 "
            f"against {small:.0f} ns at 512, {large / small:.2f}x: eviction is "
            f"growing with the cache"
        )
        assert len(_WIRE_SYMS) == len(_core._WIRE_SYM_ORDER) == 65_536
        assert set(_WIRE_SYMS) == set(_core._WIRE_SYM_ORDER)
    finally:
        _core._wire_intern_clear()

    assert not _WIRE_SYMS and not _core._WIRE_SYM_ORDER


def test_wire_intern_tables_are_bounded(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Driven at a patched bound rather than the shipped 65,536: the property
    # is that the table respects whatever bound it is given, and filling the
    # real one twice over would mint 131,000 atoms to say so.
    assert _WIRE_CACHE_MAX == 65_536
    monkeypatch.setattr(_core, "_WIRE_CACHE_MAX", 64)
    _core._wire_intern_clear()

    first_sym = wire.from_wire(["s", "evicted"])
    first_var = wire.from_wire(["v", "evicted"])
    for index in range(64 + 10):
        wire.from_wire(["s", f"symbol-{index}"])
        wire.from_wire(["v", f"variable-{index}"])

    assert len(_WIRE_SYMS) <= 64
    assert len(_WIRE_VARS) <= 64
    assert wire.from_wire(["s", "symbol-73"]) is wire.from_wire(["s", "symbol-73"])
    assert wire.from_wire(["v", "variable-73"]) is wire.from_wire(["v", "variable-73"])
    assert wire.from_wire(["s", "evicted"]) == first_sym
    assert wire.from_wire(["s", "evicted"]) is not first_sym
    assert wire.from_wire(["v", "evicted"]) == first_var
    assert wire.from_wire(["v", "evicted"]) is not first_var
    _core._wire_intern_clear()


def test_casting_protocol():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert int(Grounded(3)) == 3
    assert float(Grounded(3)) == 3.0
    assert int(Grounded(3.9)) == 3
    assert list(range(Grounded(3))) == [0, 1, 2]
    with pytest.raises(TypeError):
        int(Grounded("3"))
    with pytest.raises(TypeError):
        int(Grounded(True))  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    with pytest.raises(TypeError):
        int(S.three)


def test_variables_and_groundness():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert Expression(S.f, V.x, Expression(V.y, V.x)).vars == ("x", "y")
    assert not Expression(S.a, 1).vars
    assert V.x.vars


def test_alpha_eq():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a = Expression(S.f, V.x, V.y, V.x)
    b = Expression(S.f, V.p, V.q, V.p)
    c = Expression(S.f, V.p, V.q, V.q)
    assert a.alpha_eq(b)
    assert not a.alpha_eq(c)
    assert S.a.alpha_eq(S.a)
    assert not S.a.alpha_eq(S.b)


def test_unify():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    got = unify(S.Parent(V.x, S.Bob), S.Parent(S.Tom, S.Bob))
    assert got == {"x": S.Tom}
    assert unify(S.Parent(V.x, V.x), S.Parent(S.a, S.b)) is None
    assert unify(V.x, Expression(S.a)) == {"x": Expression(S.a)}


def test_ground_equality_is_the_engines():
    """Python-side equality carries the engine's own two relations. A raw
    operand answers the == operator over crossed values: booleans are not
    numbers, integers and floats compare by numeric value, signed zeros are
    equal, NaN is unequal to itself as IEEE reads it. Another ATOM answers
    unification instead: an integer atom never equals a float atom, signed
    zeros are two atoms, one NaN atom matches another the way the engine's
    matcher does, so a dict of atoms counts exactly what a space stores.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    nan = float("nan")
    assert Grounded(1) == 1 and Grounded(1) == 1.0
    assert Grounded(0.0) == -0.0
    assert Grounded(nan) != nan
    assert Grounded(1) != Grounded(1.0)
    assert Grounded(1.0) == Grounded(1.0)
    assert Grounded(0.0) != Grounded(-0.0)
    assert Grounded(nan) == Grounded(nan)
    assert Grounded(True) != Grounded(1)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert hash(Grounded(1)) == hash(1)
    assert hash(Grounded(nan)) == hash(Grounded(nan))
    assert unify(Grounded(1), Grounded(1.0)) is None
    assert unify(Grounded(nan), Grounded(nan)) == {}


def test_boxes_intern_per_object_identity():
    """One live object always crosses as one box, so stored and queried
    meet in the same reference; a dead object costs nothing after.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    thing = object()
    assert boxed(thing) is boxed(thing)
    assert boxed(thing).value is thing


def test_atom_identity_caches_are_thread_safe():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    thing = object()
    with ThreadPoolExecutor(max_workers=8) as workers:
        boxes = list(workers.map(boxed, [thing] * 64))
        symbols = list(workers.map(wire.from_wire, [["s", "threaded"]] * 64))

    assert all(box is boxes[0] for box in boxes)
    assert all(symbol is symbols[0] for symbol in symbols)


def test_namespace_cache_is_bounded():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for index in range(_NAMESPACE_CACHE_MAX + 50):
        S[f"namespace-{index}"]
    cache = object.__getattribute__(S, "_cache")
    assert len(cache) == _NAMESPACE_CACHE_MAX
    assert S["namespace-recent"] is S["namespace-recent"]


def test_namespace_completion_surfaces_engine_errors(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    monkeypatch.setattr(_engine, "started", lambda: True)

    def fail_runtime():
        msg = "completion engine failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(_engine, "runtime", fail_runtime)
    with pytest.raises(RuntimeError, match="completion engine failed"):
        S._ipython_key_completions_()


def test_deep_terms_cross_and_print():
    """Depth is data: the codec and the printer take 5000 levels without
    meeting Python's recursion ceiling.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    atom = Grounded(1)
    for _ in range(5000):
        atom = Expression(S.wrap, atom)
    assert wire.from_wire(atom.to_wire()) == atom
    assert str(atom).startswith("(wrap (wrap")
    assert atom.vars == ()


def test_malformed_wire_is_refused():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class IntSubclass(int):
        pass

    for bad in (
        ["b", "garbage"],
        ["n", "123"],
        ["n", True],
        ["n", IntSubclass(1)],
        ["s", 123],
        ["e", 5],
        ["zz", 1],
    ):
        with pytest.raises(ValueError):
            wire.from_wire(bad)


def test_atom_from_wire_rejects_undefined_truth():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="valid only as a complete evaluation answer"):
        wire.atom_from_wire(["u", ["s", "answer"], "delayed_goal"])


def test_anonymous_variable_is_fresh_per_occurrence():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert unify(S.pair(V._, V._), S.pair(S.a, S.b)) == {}
    assert unify(S.pair(V._, V._), S.pair(S.a, S.a)) == {}


# A KEY rather than __lt__, because `<` already means something: S.a < S.b
# builds the term (< a b), which is what the operators are for, so sorted()
# over atoms raised "(< a c) is a comparison TERM, not a truth value". The
# message is right and the order it refuses to invent exists in the language
# underneath.
def test_atoms_sort_in_prologs_standard_order():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atoms = [
        parse(source)
        for source in [
            "(edge b c)", '"text"', "a", "1", "$x", "(f a)", "2.5",
            "True", "()", "(edge a b)",
        ]
    ]
    assert [str(a) for a in sorted(atoms, key=order_key)] == [
        "$x",              # variables first
        "1", "2.5",        # then numbers, in value order
        "True", "a",       # then symbols, and True IS one despite being a
                           # Python int
        '"text"',          # then strings
        "()", "(f a)",     # then compounds, by arity first
        "(edge a b)", "(edge b c)",   # then functor, then argument by argument
    ]


def test_the_sort_key_is_total_over_mixed_atoms():
    """Every key must be comparable with every other, which a tuple key only
    is when the rank leads and the payloads at one rank share a type.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    atoms = [
        S.a, parse("1"), parse("2.5"), parse('"s"'), V.x, S.f(S.a),
        S.f(S.a, S.b), parse("()"), parse("True"), Grounded(object()),
    ]
    for left in atoms:
        for right in atoms:
            assert isinstance(order_key(left) < order_key(right), bool)


# The wire form IS a JSON document and it round-trips, preserving the variable
# NAME, which storage does not. It was simply not exported.
def test_an_atom_round_trips_through_json():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atom = S.edge(S.a, 1, V.x)
    text = json.dumps(atom.to_wire())
    assert text == '["e", [["s", "edge"], ["s", "a"], ["n", 1], ["v", "x"]]]'
    back = wire.atom_from_wire(json.loads(text))
    assert atom.alpha_eq(back)
    assert str(back) == "(edge a 1 $x)"


def test_slot_docstrings_reach_help():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # dict-form __slots__, data model 3.3.2.4: help() and inspect.getdoc
    # document the attribute in place (the descriptor's own __doc__ stays
    # None by CPython design).
    assert inspect.getdoc(Expression.children) == "the ordered child atoms, as a tuple"
    assert inspect.getdoc(Grounded.value) == "the ground Python value this atom carries"
    assert (
        inspect.getdoc(Symbol.name) == "the symbol's name, exactly as written in source"
    )
    assert inspect.getdoc(Variable.name) == "the variable's name without the $ sigil"


def test_pretty_lays_out_deep_terms_and_agrees_with_the_engine(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    source = (
        "(alpha (beta (gamma delta epsilon) (zeta eta theta)) "
        "(iota (kappa lambda mu) (nu xi omicron)) "
        "(pi (rho sigma tau) (upsilon phi chi)))"
    )
    term = parse(source)
    laid_out = repr(term)
    assert laid_out.startswith("(alpha\n  (beta")
    assert laid_out.count("\n") == 3
    # the engine's (pretty-atom ...) is the SAME layout, differentially
    assert metta._one(f"(pretty-atom {source})") == laid_out
    # a fitting term stays inline
    assert repr(parse("(f 1 2)")) == "(f 1 2)"
