"""Purpose: spaces implemented in Python: matching, enumeration, writes,
conjunctions, and mixing with native spaces, through a dict-backed provider
and through DuckDB with SQL pushdown.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from collections.abc import Iterator
from typing import Any, ClassVar

import pytest

import petta.foreign as foreign_module
from petta import (
    Adder,
    Clearer,
    EngineError,
    Enumerable,
    Matcher,
    Remover,
    S,
    V,
    expr,
)
from petta.foreign import SpaceProvider


class ListSpace(SpaceProvider):
    """The simplest honest provider: a Python list of atoms."""

    def __init__(self, atoms=()):
        self.stored = list(atoms)
        self.match_calls = 0

    def match(self, pattern):
        self.match_calls += 1
        return iter(self.stored)

    def atoms(self):
        return iter(self.stored)

    def add(self, atom):
        self.stored.append(atom)

    def remove(self, atom):
        if atom in self.stored:
            self.stored[:] = [a for a in self.stored if a != atom]
            return True
        return False


@pytest.fixture()
def listspace(metta):
    provider = ListSpace([S.edge(S.a, S.b), S.edge(S.b, S.c), S.other(1)])
    name = f"&list{id(provider) % 10000}"
    metta.register_space(name, provider)
    yield name, provider, metta
    metta.unregister_space(name)


def test_match_reaches_the_provider(listspace):
    name, provider, m = listspace
    r = m.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
    assert r == [[expr(expr(S.a, S.b), expr(S.b, S.c))]]
    assert provider.match_calls >= 1


def test_engine_unifies_over_approximate_candidates(listspace):
    # The provider returns everything; the pattern still selects correctly,
    # because unification is the engine's.
    name, provider, m = listspace
    assert m.run(f"!(match {name} (edge a $y) $y)") == [[S.b]]


def test_conjunction_routes_through_the_provider(listspace):
    name, provider, m = listspace
    r = m.run(f"!(collapse (match {name} (, (edge $x $y) (edge $y $z)) ($x $z)))")
    assert r == [[expr(expr(S.a, S.c))]]


def test_python_query_api_over_foreign_space(listspace):
    name, provider, m = listspace
    rows = m.space(name).query(S.edge(V.x, V.y), S.edge(V.y, V.z))
    assert [(r.x, r.z) for r in rows] == [(S.a, S.c)]


def test_writes_reach_the_provider(listspace):
    name, provider, m = listspace
    m.run(f"!(add-atom {name} (edge c d))")
    assert S.edge(S.c, S.d) in provider.stored
    m.run(f"!(remove-atom {name} (other 1))")
    assert S.other(1) not in provider.stored


def test_get_atoms_enumerates(listspace):
    name, provider, m = listspace
    space = m.space(name)
    assert len(space.atoms()) == 3
    assert space.count() == 3


def test_mixed_native_and_foreign_join(listspace):
    name, provider, m = listspace
    native = m.fresh_space()
    native.add(S.blessed(S.a))
    r = native.run(
        f"!(collapse (match {name} (edge $x $y) "
        f"(match (context-space) (blessed $x) ($x reaches $y))))"
    )
    assert r == [[expr(expr(S.a, S.reaches, S.b))]]


def test_read_only_provider_errors_loudly(metta):
    class ReadOnly(SpaceProvider):
        def atoms(self):
            return iter([S.fact(1)])

    name = "&readonly1"
    metta.register_space(name, ReadOnly())
    try:
        with pytest.raises(EngineError) as excinfo:
            metta.run(f"!(add-atom {name} (fact 2))")
        assert "does not implement add" in str(excinfo.value)
    finally:
        metta.unregister_space(name)


def test_capabilities_follow_implemented_methods():
    class ReadOnly(SpaceProvider):
        def atoms(self) -> Iterator[Any]:
            return iter(())

    class AddOnly(SpaceProvider):
        def add(self, atom) -> None:
            pass

    read_only = ReadOnly()
    assert isinstance(read_only, Enumerable)
    assert not isinstance(read_only, Matcher)
    assert read_only.can_run("match")
    assert read_only.can_run("enumerate")
    assert not read_only.can_run("add")
    assert not read_only.can_run("unknown")

    add_only = AddOnly()
    assert isinstance(add_only, Adder)
    assert not isinstance(add_only, (Clearer, Remover))
    assert add_only.can_run("subscribe", on="add")
    assert not add_only.can_run("subscribe", on="remove")
    assert not add_only.can_run("subscribe", on="both")


def test_stale_static_capability_declaration_is_refused():
    with pytest.raises(TypeError, match="stale static declaration"):

        class StaleProvider(SpaceProvider):
            capabilities: ClassVar = {"add": True}


def test_provider_can_decline_one_request(metta):
    class Selective(SpaceProvider):
        def __init__(self):
            self.stored = []

        def atoms(self):
            return iter(self.stored)

        def add(self, atom):
            self.stored.append(atom)

        def should_run(self, capability, /, **request):
            return capability != "add" or request["atom"] != S.denied(1)

    provider = Selective()
    name = "&selective-capability"
    metta.register_space(name, provider)
    try:
        metta.space(name).add(S.allowed(1))
        with pytest.raises(EngineError, match="declined this add request"):
            metta.space(name).add(S.denied(1))
        assert provider.stored == [S.allowed(1)]
    finally:
        metta.unregister_space(name)


# The worked SQL instance lives whole in examples/integration/duckdb_space.py,
# which verifies itself in the suite; here stays the provider protocol.


def test_provider_collision_is_refused(metta):
    class Empty(SpaceProvider):
        def atoms(self):
            return iter(())

    first = Empty()
    metta.register_space("&col", first)
    try:
        with pytest.raises(ValueError):
            metta.register_space("&col", Empty())
        # The same provider again is idempotent, not a collision.
        metta.register_space("&col", first)
    finally:
        metta.unregister_space("&col")


def test_provider_registration_is_transactional():
    class Empty(SpaceProvider):
        def atoms(self):
            return iter(())

    class Runtime:
        fail = False

        def must(self, _goal, **_inputs):
            if self.fail:
                raise RuntimeError("injected provider boundary failure")
            return {"truth": True}

    provider = Empty()
    name = f"&provider-transaction-test-{id(provider)}"
    runtime = Runtime()
    try:
        runtime.fail = True
        with pytest.raises(RuntimeError, match="injected provider boundary failure"):
            foreign_module.register_provider(runtime, name, provider)
        assert name not in foreign_module.PROVIDERS

        runtime.fail = False
        foreign_module.register_provider(runtime, name, provider)
        runtime.fail = True
        with pytest.raises(RuntimeError, match="injected provider boundary failure"):
            foreign_module.unregister_provider(runtime, name)
        assert foreign_module.PROVIDERS[name] is provider
    finally:
        runtime.fail = False
        foreign_module.unregister_provider(runtime, name)
