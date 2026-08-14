"""Purpose: the integration interface end to end: bulk module operations,
instance wrapping with the effect convention, protocol typing and printing,
py-field reasoning in both modes, the reflector registry, integrate() over
modules, and a real third-party library (networkx) integrated in a page.
Guarantees:
  - dropping a space invalidates its integration installation records [tested
    test_dropped_space_name_reinstalls_integrations]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import math
import types
from dataclasses import dataclass

import pytest

from petta import CastError, PettaError, S, Sym, V, expr, val
from petta import integrate as pi


def test_module_ops_bulk_registers_a_stdlib_module(metta):
    names = pi.module_ops(metta, math, ["sqrt", "floor", "gcd", "comb"])
    assert set(names) == {"sqrt", "floor", "gcd", "comb"}
    assert metta.run("!(sqrt 16.0)") == [[4.0]]
    assert metta.run("!(gcd 12 18)") == [[6]]
    assert metta.run("!(comb 5 2)") == [[10]]


def test_uninspectable_callable_errors_are_classified(metta):
    class Uninspectable:
        @property
        def __signature__(self):
            raise TypeError("unsupported callable type")

        def __call__(self, value):
            return value

    target = Uninspectable()
    module = types.SimpleNamespace(__name__="uninspectable", target=target)
    assert pi.module_ops(metta, module, ["target"]) == ["target"]
    assert metta.run("!(target 7)") == [[7]]
    with pytest.raises(PettaError, match=r"pass arities=\[\.\.\.\]") as caught:
        pi.wrap_callable(metta, "strict-target", target)
    assert isinstance(caught.value.__cause__, TypeError)


def test_wrap_callable_rejects_required_keyword_only_parameters(metta):
    def target(value, *, required):
        return value + required

    with pytest.raises(PettaError, match="required keyword-only parameter 'required'"):
        pi.wrap_callable(metta, "keyword-only", target)


def test_wrap_object_methods_with_effect_convention(metta):
    class Store:
        def __init__(self):
            self.items = []

        def put(self, x):
            self.items.append(x)  # returns None: the effect convention

        def size(self):
            return len(self.items)

    store = Store()
    pi.wrap_object(metta, "store", store, ["put", "size"])
    r = metta.run("!(store-put 42)\n!(store-put 43)\n!(store-size)")
    assert r == [[True], [True], [2]]
    assert store.items == [42, 43]
    # The instance is enumerable as a fact.
    rows = metta.query(S.wrapped(S.store, V.obj))
    assert rows and rows[0].obj == store


def test_register_object_type_makes_protocols_types(metta):
    class Quacks:
        def quack(self):
            return "quack"

    pi.register_object_type(lambda x: hasattr(x, "quack"), "Duck")
    space = metta.fresh_space()
    space.add(S.pet(val(Quacks())))
    (answers,) = space.run("!(collapse (get-type (match (context-space) (pet $p) $p)))")
    names = {str(a) for a in answers[0]}
    assert "Duck" in names and "Quacks" in names


def test_register_repr_protocol(metta):
    class Sized:
        def __len__(self):
            return 7

    pi.register_repr(lambda x: hasattr(x, "__len__") and type(x).__name__ == "Sized",
                     lambda x: f"<Sized of {len(x)}>")
    assert "Sized of 7" in repr(val(Sized()))


def test_protocol_and_reflector_registrations_can_be_removed(metta):
    class ExtensionTarget:
        pass

    target = ExtensionTarget()

    def type_predicate(value):
        return isinstance(value, ExtensionTarget)

    def repr_predicate(value):
        return isinstance(value, ExtensionTarget)

    def formatter(_value):
        return "<extension target>"

    def reflector(m, name, _value):
        return pi.facts(m, [S.reflected(Sym(name))])

    pi.register_object_type(type_predicate, "ExtensionTargetProtocol")
    pi.register_repr(repr_predicate, formatter)
    pi.register_reflector(type_predicate, reflector)
    try:
        assert metta.cast(target, "ExtensionTargetProtocol") is target
        assert str(val(target)) == "<extension target>"
        assert pi.reflect(metta, "registered", target) == 1
    finally:
        pi.unregister_reflector(type_predicate, reflector)
        pi.unregister_repr(repr_predicate, formatter)
        pi.unregister_object_type(type_predicate, "ExtensionTargetProtocol")

    with pytest.raises(CastError):
        metta.cast(target, "ExtensionTargetProtocol")
    assert str(val(target)) == "<ExtensionTarget>"
    with pytest.raises(PettaError, match="no reflector claims ExtensionTarget"):
        pi.reflect(metta, "removed", target)
    with pytest.raises(KeyError, match="ExtensionTargetProtocol"):
        pi.unregister_object_type(type_predicate, "ExtensionTargetProtocol")
    with pytest.raises(KeyError, match="protocol repr"):
        pi.unregister_repr(repr_predicate, formatter)
    with pytest.raises(KeyError, match="reflector"):
        pi.unregister_reflector(type_predicate, reflector)


def test_py_field_reasons_in_both_modes(metta):
    @dataclass
    class Config:
        depth: int
        name: str

    pi.install_reflection_ops(metta)
    space = metta.fresh_space()
    space.add(S.config(val(Config(3, "deep"))))
    # Bound mode: fetch one field.
    r = space.run(
        "!(match (context-space) (config $c) (py-field $c depth))"
    )
    (group,) = r
    (pair,) = group
    assert pair[0] == S.depth and int(pair[1].value) == 3
    # Unbound mode: enumerate every field, one answer each.
    r = space.run(
        "!(collapse (match (context-space) (config $c) (py-field $c $f)))"
    )
    names = {str(p[0]) for p in r[0][0]}
    assert names == {"depth", "name"}


def test_py_attr_and_bound_py_field_read_a_property_once(metta):
    class Counted:
        def __init__(self):
            self.reads = 0

        @property
        def item(self):
            self.reads += 1
            return self.reads

    pi.install_reflection_ops(metta)
    target = Counted()
    space = metta.fresh_space()
    try:
        space.add(S.target(val(target)))
        assert space.run(
            "!(match (context-space) (target $x) (py-attr $x item))"
        ) == [[1]]
        assert target.reads == 1
        (pair,) = space.run(
            "!(match (context-space) (target $x) (py-field $x item))"
        )[0]
        assert int(pair[1].value) == 2
        assert target.reads == 2
    finally:
        space.drop()


def test_integrate_module_protocol_and_idempotence(metta):
    calls = []
    fake = types.SimpleNamespace(
        __name__="fake_integration", install_petta=lambda m: calls.append(m)
    )

    name = pi.integrate(metta, fake)
    assert name == "fake_integration"
    pi.integrate(metta, fake)
    assert len(calls) == 1  # idempotent per process
    # Installation is per (space, name): a second space installs again.
    assert (metta.space_name, "fake_integration") in pi.installed()
    other = metta.fresh_space()
    try:
        pi.integrate(other, fake)
        assert len(calls) == 2
    finally:
        other.drop()


def test_dropped_space_name_reinstalls_integrations(metta):
    calls = []

    class Reinstallable:
        name = "space-reuse-probe"

        def install(self, target):
            calls.append(target.space_name)
            target.add(S.integration_marker(len(calls)))

    integration = Reinstallable()
    space_name = "&integration_reuse_probe"
    first = metta.space(space_name)
    first.clear()
    pi.integrate(first, integration)
    assert first.query(S.integration_marker(V.value)).one().value == 1

    first.drop()
    assert (space_name, integration.name) not in pi.installed()

    second = metta.space(space_name)
    try:
        pi.integrate(second, integration)
        assert second.query(S.integration_marker(V.value)).one().value == 2
        assert calls == [space_name, space_name]
    finally:
        second.drop()


def test_facts_bulk_load(metta):
    space = metta.fresh_space()
    count = pi.facts(space, [S.n(1), S.n(2), (S.pair, 1, 2)])
    assert count == 3
    assert space.count() == 3


def test_networkx_integrates_in_a_page(metta):
    """The acid test the interface exists for: a real library, deeply usable,
    with only public toolkit calls."""
    nx = pytest.importorskip("networkx")

    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("a", "c", weight=9.0)

    space = metta.fresh_space()
    # Structure as facts:
    pi.facts(space, (expr(S.nx_edge, S[u], S[v], d["weight"]) for u, v, d in graph.edges(data=True)))
    # Behaviour as an operation:
    def shortest_path(a, b):
        names = nx.shortest_path(graph, str(a), str(b), weight="weight")
        return expr(*(S[n] for n in names))

    space.register_op(shortest_path, name="nx-path", raw=False, typed=False)
    # And both compose with reasoning:
    assert space.run("!(nx-path a c)") == [[expr(S.a, S.b, S.c)]]
    rows = space.query(S.nx_edge(S.a, V.to, V.w))
    assert {(str(r.to), float(r.w)) for r in rows} == {("b", 1.0), ("c", 9.0)}


def test_the_routing_frame_metta_subsumes_dispatch(metta):
    """The express() frame, run rather than argued: an app is a space, every
    route is an equation, a request reduces through whichever route matches,
    and the catch-all equation is the 404. Clause order plus once is the
    dispatcher; nothing was built to make this work, which is the point."""
    app = metta.fresh_space()
    app.run(
        '(= (route home) (Page 200 "Welcome"))\n'
        '(= (route about) (Page 200 "About us"))\n'
        "(= (route $other) (NotFound 404 $other))\n"
        "(= (handle $request) (once (route $request)))"
    )
    assert app.run("!(handle home)") == [[expr(S.Page, 200, "Welcome")]]
    assert app.run("!(handle nowhere)") == [[expr(S.NotFound, 404, S.nowhere)]]
    # And a middleware chain is function composition, for free:
    app.run('(= (logged $req) (let $res (handle $req) (Logged $req $res)))')
    (group,) = app.run("!(logged about)")
    assert group == [expr(S.Logged, S.about, expr(S.Page, 200, "About us"))]
