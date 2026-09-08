"""Purpose: hold generated doors and package registrations to their contracts.

Guarantees: catalog publication, registry replacement, generated protocols,
  and the projection gate are exercised through their observable boundaries
  [tested: this file; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Owns resources: each fixture withdraws its registrations and each engine
  context or cursor is closed by its test.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from metta import MeTTa, S, Space, V, seam
from metta.doors import (
    DOORS,
    AnswersAs,
    Body,
    Door,
    Kind,
    Owner,
    Provider,
    Receiver,
    Refusal,
    Signature,
    Sugar,
    Tier,
    namespace,
    publish,
    table,
    validate,
)
from metta.errors import EngineError, MettaError
from metta.vocabularies import ArgumentDelivery, Determinism, EffectClass, RefusalKind

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "extensions/python/tools"))
import doorgen  # noqa: E402  -- the generator is checked as a public build tool


@pytest.mark.parametrize("installed", (False, True))
def test_namespace_typing_preserves_available_provider_types(tmp_path, installed):
    """Missing optional packages permit core typing; present packages retain types."""
    pytest.importorskip("mypy")
    row = replace(
        _record(),
        body=Body("door_optional", "identity", Receiver.value),
        signatures=(Signature("receiver, value: int = 1", returns="Payload"),),
    )
    (tmp_path / "door_protocol.py").write_text(doorgen.namespace_types((row,)), encoding="utf-8")
    if installed:
        (tmp_path / "door_optional.py").write_text(
            '"""Purpose: supply the optional provider result type."""\n'
            "class Payload: pass\n", encoding="utf-8",
        )
    (tmp_path / "consumer.py").write_text(
        '"""Purpose: check available result types and reject a wrong argument."""\n'
        "from typing import reveal_type\n"
        "from door_protocol import DoorFixtureSync\n"
        "def use(door: DoorFixtureSync) -> None:\n"
        "    reveal_type(door.identity(1))\n"
        "    door.identity('wrong')\n", encoding="utf-8",
    )
    config = tmp_path / "mypy.ini"
    config.write_text("[mypy]\npython_version = 3.12\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(config),
         "--no-site-packages", "--no-incremental", "--warn-unused-ignores",
         "--cache-dir", str(tmp_path / "cache"), "consumer.py"],
        cwd=tmp_path, env=os.environ | {"MYPYPATH": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.count("error:") == 1, result.stdout
    assert "[arg-type]" in result.stdout
    expected = "door_optional.Payload" if installed else "Any"
    assert f'Revealed type is "{expected}"' in result.stdout


def _identity(receiver, value: int = 1) -> tuple[object, int]:
    return receiver, value


def _replacement(receiver, value: int = 1) -> tuple[object, int]:
    return receiver, value + 1


def _record(registrant: str = "door-fixture", accessor: str = "door_fixture") -> Door:
    return Door(
        owner=Owner.namespace, name="identity", kind=Kind.query,
        signatures=(Signature("receiver, value: int = 1", returns="tuple[object, int]"),),
        answers=AnswersAs.value, effect=EffectClass.pureStructural,
        determinism=Determinism.det, tiers=(Tier.sync,),
        body=Body(__name__, "_identity", Receiver.value),
        provider=Provider(registrant, accessor),
        docs="Return the receiver and the supplied number.",
        evidence=("extensions/python/tests/repository/test_door_rows.py::test_a_retained_namespace_observes_replacement_and_withdrawal",),
    )


@pytest.fixture
def registrations():
    """Withdraw every door registration made by this test."""
    names = set()

    def register(*rows):
        name = rows[0].provider.registrant
        names.add(name)
        return seam.door.register(name, doors=tuple(rows))

    try:
        yield register
    finally:
        for name in names:
            seam.door.unregister(name)


def test_door_rows_need_no_engine():
    """Door rows need no engine."""
    program = """
import importlib.abc
import sys
class RefuseEngine(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'janus_swi', 'metta._space', 'metta._engine'}:
            raise AssertionError('engine import: ' + fullname)
sys.meta_path.insert(0, RefuseEngine())
from metta.doors import DOORS, table, validate
assert len(validate(DOORS)) > 200
assert len(table(discover=False)) == len(DOORS)
print('engine-free')
"""
    completed = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "extensions/python")}, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "engine-free"


@pytest.mark.parametrize(("annotation", "delivery"), [
    ("Atom", ArgumentDelivery.atoms),
    ("Grounded | None", ArgumentDelivery.atoms),
    ("Optional[Symbol]", ArgumentDelivery.atoms),
    ("Union[Expression, Variable]", ArgumentDelivery.atoms),
    ("Annotated[Atom, 'marker']", ArgumentDelivery.atoms),
    ("Space", ArgumentDelivery.atoms),
    ("Atom | str", ArgumentDelivery.values),
    ("Callable[[Atom], bool]", ArgumentDelivery.values),
    ("Iterable[Atom]", ArgumentDelivery.values),
    ("Any", ArgumentDelivery.values),
])
def test_argument_delivery_follows_the_outer_projected_type(annotation, delivery):
    """Argument delivery follows the outer projected type."""
    arguments = Signature(f"item: {annotation}").arguments(__name__)
    assert arguments[0].delivery is delivery


def test_argument_delivery_reads_the_shared_projection_table(monkeypatch):
    """Argument delivery reads the shared projection table."""
    from metta import _projection

    original = _projection.TABLE["Number"]
    monkeypatch.setitem(_projection.TABLE, "Number", original._replace(delivery=ArgumentDelivery.atoms))
    assert Signature("item: int").arguments(__name__)[0].delivery is ArgumentDelivery.atoms


def test_every_door_projection_is_current():
    """Every door projection is current."""
    assert not doorgen.contract_findings()
    assert doorgen.main([]) == 0


def test_a_retained_namespace_observes_replacement_and_withdrawal(registrations):
    """A retained namespace observes replacement and withdrawal."""
    row = _record()
    registrations(row)
    receiver = object()
    accessor = namespace(receiver, "door_fixture")
    member = accessor.identity
    assert member(4) == (receiver, 4)
    assert tuple(inspect.signature(member).parameters) == ("value",)
    registrations(replace(row, body=Body(__name__, "_replacement", Receiver.value)))
    assert member(4) == (receiver, 5)
    assert accessor.identity(6) == (receiver, 7)
    assert seam.door.unregister("door-fixture")
    with pytest.raises(AttributeError, match="withdrawn"):
        member(4)
    with pytest.raises(AttributeError, match="no door"):
        _ = accessor.identity
    with pytest.raises(AttributeError, match="no door namespace"):
        namespace(receiver, "door_fixture")


def test_concurrent_door_claims_have_one_winner(registrations):
    """Concurrent door claims have one winner."""
    barrier = threading.Barrier(2)

    def claim(name):
        row = _record(name)
        barrier.wait()
        try:
            registrations(row)
        except ValueError as error:
            return str(error)
        return "won"

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(claim, ("door-fixture-one", "door-fixture-two")))
    assert results.count("won") == 1
    assert sum("already exists" in result for result in results) == 1


def test_door_registration_refuses_collisions_and_duplicate_points(registrations):
    """Door registration refuses collisions and duplicate points."""
    row = _record()
    registrations(row)
    with pytest.raises(ValueError, match="already exists"):
        registrations(replace(row, provider=Provider("door-other", "door_fixture")))
    with pytest.raises(ValueError, match="collides with a core door"):
        registrations(replace(row, provider=Provider("door-collision", "eval")))
    with pytest.raises(ValueError, match="public member"):
        registrations(replace(row, name="__class__"))
    with pytest.raises(TypeError, match="Kind"):
        registrations(replace(row, kind="invented"))
    ordinary = next(record for record in DOORS if record.key == "space:answers")
    with pytest.raises(ValueError, match="existing parameter point"):
        validate((*DOORS, replace(ordinary, name="another-answers")))
    with pytest.raises(ValueError, match="cyclic"):
        validate((*DOORS, replace(row, sugar_of=Sugar(row.key, ()))))
    assert namespace(object(), "door_fixture").identity(8)[1] == 8


def test_a_provider_body_is_checked_before_it_runs(registrations):
    """A provider body is checked before it runs."""
    row = _record()
    wrong = replace(row, signatures=(Signature("receiver, unknown: int = 1"),))
    registrations(wrong)
    with pytest.raises(TypeError, match="implementation signature differs"):
        namespace(object(), "door_fixture").identity()


def test_namespace_tiers_control_lookup_retained_calls_and_annotations(registrations):
    """Namespace tiers control lookup retained calls and annotations."""
    with MeTTa() as context:
        row = replace(_record(), tiers=(Tier.context,))
        registrations(row)
        accessor = context.door_fixture
        held = accessor.identity
        assert held(4) == (context, 4)
        assert dir(accessor) == ["identity"]
        with pytest.raises(AttributeError, match="no door namespace"):
            _ = context.self.door_fixture
        generated = doorgen.namespace_types((row,))
        assert "class DoorFixtureContext(Protocol):" in generated
        assert "class DoorFixtureSync(Protocol):" not in generated
        declarations = doorgen.class_block("MeTTa", (*DOORS, row))
        assert "        door_fixture: _door_namespaces.DoorFixtureContext" in declarations
        assert all("door_fixture:" not in line for line in doorgen.class_block("Space", (*DOORS, row)))
        registrations(replace(row, tiers=(Tier.sync,)))
        assert context.self.door_fixture.identity(5) == (context.self, 5)
        assert dir(accessor) == []
        with pytest.raises(AttributeError, match="withdrawn"):
            held(4)
        with pytest.raises(AttributeError, match="withdrawn"):
            _ = held.__signature__


@pytest.mark.parametrize("changes", [
    {"signatures": (Signature("receiver", declarations=["property"]),)},
    {"signatures": (Signature("receiver", returns=42),)},
    {"body": Body("fixture", "member", "space")},
    {"provider": Provider("door-fixture", "door_fixture", callable="yes")},
    {"sugar_of": Sugar("space:eval", [("answer", "first")])},
    {"sugar_of": Sugar("space:eval", (("answer", ["first"]),))},
    {"sugar_of": Sugar("space:eval", (("limit", float("nan")),))},
    {"refuses": (Refusal(RefusalKind.type, []),)},
    {"async_signature": "receiver"},
])
def test_door_registration_refuses_mutable_or_untyped_nested_fields(registrations, changes):
    """Door registration refuses mutable or untyped nested fields."""
    row = _record()
    registrations(row)
    with pytest.raises(TypeError):
        registrations(replace(row, **changes))
    assert namespace(object(), "door_fixture").identity(4)[1] == 4


def test_door_signatures_cannot_inject_another_declaration():
    """Door signatures cannot inject another declaration."""
    bad = Signature("x): ...\nprint('extra')\ndef another(x")
    with pytest.raises(TypeError, match="one function"):
        _ = bad.node


def test_namespaces_resolve_declared_python_spellings_and_refuse_alias_collisions(registrations):
    """Namespaces resolve declared python spellings and refuse alias collisions."""
    row = replace(_record(), name="local_name")
    registrations(row)
    assert namespace(object(), "door_fixture").local_name(4)[1] == 4
    with pytest.raises(ValueError, match="existing Python spelling"):
        registrations(row, replace(row, name="local-name"))
    assert "local_name" in dir(namespace(object(), "door_fixture"))


def test_a_failed_entry_point_can_be_retried(monkeypatch, registrations):
    """A failed entry point can be retried."""
    group = "metta.door-test"
    attempts = []

    class Entry:
        def load(self):
            attempts.append(1)
            if len(attempts) == 1:
                msg = "door entry failed to import"
                raise ImportError(msg)
            return lambda: registrations(_record())

    monkeypatch.setattr(seam, "advertised", lambda _group: {"retry-door": Entry()})
    try:
        with pytest.raises(ImportError, match="door entry failed to import"):
            seam.discover(group)
        assert seam.discover(group) == ("retry-door",)
        assert len(attempts) == 2
        assert namespace(object(), "door_fixture").identity(3)[1] == 3
    finally:
        seam._LOADED.discard(group)
        seam._LOADED_ENTRIES.discard((group, "retry-door"))


def test_concurrent_discovery_waits_for_complete_registration(monkeypatch, registrations):
    """Concurrent discovery waits for complete registration."""
    group = "metta.concurrent-door-test"
    entered, release, waiting = (threading.Event() for _ in range(3))
    calls = []

    class Changed(threading.Condition):
        def wait(self, timeout=None):
            waiting.set()
            return super().wait(timeout)

    class Entry:
        def load(self):
            def register():
                calls.append(1)
                entered.set()
                release.wait()
                registrations(_record())
            return register

    original = seam.advertised
    monkeypatch.setattr(seam, "advertised", lambda name: {"delayed": Entry()} if name == group else original(name))
    monkeypatch.setattr(seam, "_ENTRY_CHANGED", Changed(seam._LOCK))
    try:
        with ThreadPoolExecutor(2) as workers:
            first = workers.submit(seam.discover, group)
            entered.wait()
            second = workers.submit(seam.discover, group)
            try:
                waiting.wait()
                assert not second.done()
            finally:
                release.set()
            assert first.result() == second.result() == ("delayed",)
        assert calls == [1]
        assert namespace(object(), "door_fixture").identity(8)[1] == 8
    finally:
        release.set()
        seam._LOADED.discard(group)
        seam._LOADED_ENTRIES.discard((group, "delayed"))


def test_recursive_discovery_does_not_publish_an_incomplete_group(monkeypatch):
    """Recursive discovery does not publish an incomplete group."""
    group = "metta.recursive-door-test"
    calls = []

    class Entry:
        def load(self):
            calls.append(1)
            assert seam.discover(group) == ("recursive",)
            assert group not in seam._LOADED

    monkeypatch.setattr(seam, "advertised", lambda _group: {"recursive": Entry()})
    try:
        assert seam.discover(group) == ("recursive",)
        assert group in seam._LOADED
        assert calls == [1]
    finally:
        seam._LOADED.discard(group)
        seam._LOADED_ENTRIES.discard((group, "recursive"))


def test_a_discovery_wait_cycle_refuses_and_releases_its_entries(monkeypatch):
    """A discovery wait cycle refuses and releases its entries."""
    groups = ("metta.cycle-door-a", "metta.cycle-door-b")
    barrier = threading.Barrier(2)
    attempts = {}

    class Entry:
        def __init__(self, group):
            self.group = group

        def load(self):
            with seam._LOCK:
                first = self.group not in attempts
                attempts[self.group] = True
            if first:
                barrier.wait()
            seam.discover(groups[1] if self.group == groups[0] else groups[0])

    monkeypatch.setattr(seam, "advertised", lambda group: {"cycle": Entry(group)})
    try:
        with ThreadPoolExecutor(2) as workers:
            futures = [workers.submit(seam.discover, group) for group in groups]
            errors = [future.exception() for future in futures]
        assert any(isinstance(error, RuntimeError) and "cyclic entry-point discovery" in str(error) for error in errors)
        assert all(error is None or isinstance(error, RuntimeError) for error in errors)
        assert not seam._LOADING_ENTRIES
        assert not seam._WAITING_ENTRIES
        for group in groups:
            assert seam.discover(group) == ("cycle",)
    finally:
        for group in groups:
            seam._LOADED.discard(group)
            seam._LOADED_ENTRIES.discard((group, "cycle"))


def test_boot_publishes_complete_typed_door_rows():
    """Boot publishes complete typed door rows."""
    from metta._door_catalog import atoms

    with MeTTa() as context:
        catalog = context.space("&metta")
        expected = atoms(tuple(table().values()))
        for atom in expected:
            assert atom in catalog, atom
        records = [atom for atom in expected if atom.children and atom.children[0] == S.door]
        assert len(records) == len(table())
        assert S[":"](S.DoorDeclaration, S.Type) in catalog
        assert S[":"](S.query, S.DoorKind) in catalog
        assert context.run("!(match &metta (door eval evaluation $owner $args $answers $effect $det $sugar $binding $provider $body $refuses $tiers $docs $evidence $assumes $guarantees $fails) $owner)") == [[S.space]]


def test_door_catalog_publication_is_atomic_and_idempotent(registrations):
    """Door catalog publication is atomic and idempotent."""
    with MeTTa() as context:
        assert publish(context.runtime) == 0
        baseline = context.runtime.must("metta_py_door_snapshot(Wires)")["Wires"]
        malformed = [*baseline, S.door(S.bad).to_wire()]
        with pytest.raises(EngineError, match="does not fit its declared kind"):
            context.runtime.must("metta_py_publish_doors(Wires, Count)", Wires=malformed)
        assert context.runtime.must("metta_py_door_snapshot(Wires)")["Wires"] == baseline
        assert publish(context.runtime) == 0
        row = _record()
        registrations(row)
        try:
            # A row registered after boot is in the catalog at once: the seam's
            # listener publishes on every registry change, so no refresh is
            # asked for and a second publication has nothing left to change.
            assert any("door_fixture" in str(atom) for atom in context.space("&metta").atoms())
            assert publish(context.runtime) == 0
        finally:
            seam.door.unregister(row.provider.registrant)
        # The withdrawal reached the catalog the same way.
        assert not any("door_fixture" in str(atom) for atom in context.space("&metta").atoms())
        assert context.runtime.must("metta_py_door_snapshot(Wires)")["Wires"] == baseline


def test_nested_door_records_have_declared_types():
    """Nested door records have declared types."""
    from metta import Expression
    from metta._door_catalog import _contract, atoms

    with MeTTa() as context:
        catalog = context.space("&metta")
        records = tuple(table().values())
        arrows = {
            str(atom.children[1]): atom.children[2]
            for atom in atoms(records)
            if atom.head == S[":"] and isinstance(atom.children[2], Expression)
        }
        checked = set()

        def visit(atom):
            if not isinstance(atom, Expression) or not atom.children:
                return
            head = str(atom.head)
            if head == "door" or head.startswith("door-"):
                assert head in arrows, atom
                arrow = arrows[head]
                assert len(atom.children) == len(arrow.children) - 1, atom
                if head not in checked:
                    assert catalog.type(atom) == arrow.children[-1], atom
                    checked.add(head)
            for child in atom.children:
                visit(child)

        for record in records:
            visit(_contract(record))
        assert checked == {head for head in arrows if head == "door" or head.startswith("door-")}
        original = S.kind(S.arguments, S.symbol, S["one-of"](S["argument-delivery"]))
        assert original in catalog
        bad = S["door-argument"](S.value, S.Number, S["door-required"](), S.atomz, S["positional-only"])
        with pytest.raises(EngineError, match="argument-delivery"):
            catalog.add(bad)


def test_generated_space_protocols_preserve_storage_and_identity():
    """Generated space protocols preserve storage and identity."""
    import copy

    with MeTTa() as context:
        space = context.self
        assert bool(space) and bool(context)
        space += S.edge(1)
        space |= [S.edge(2), S.edge(2)]
        assert len(space) == 3 and len(context) == 3
        assert S.edge(1) in space
        assert list(space) == space.atoms()
        assert len(space[S.edge(V.x)]) == 3
        space -= S.edge(2)
        assert len(space) == 2
        del space[S.edge(V.x)]
        assert not space.atoms() and bool(space)
        context += S.kept(7)
        assert isinstance(context, MeTTa)
        with copy.copy(space) as cloned:
            assert cloned.atoms() == space.atoms()
            assert cloned != space


def test_inherited_atom_doors_remain_declared():
    """Inherited atom doors remain declared."""
    from metta.atoms import Grounded

    inherited = [row for row in DOORS if row.owner is Owner.space and row.inherited]
    assert len(inherited) == 16
    for row in inherited:
        assert hasattr(Space, row.python)
        assert row.body.resolve() is inspect.getattr_static(Space, row.python)
    with MeTTa() as context:
        space = context.self
        assert isinstance(space, Grounded)
        assert space.vars == ()
        assert space.alpha(space) == S["=alpha"](space, space)
        assert space.eq(space) == S["=="](space, space)
        assert space.ne(space) == S["not"](S["=="](space, space))
        for name, head in (("ge", ">="), ("gt", ">"), ("le", "<="), ("lt", "<")):
            assert getattr(space, name)(space) == S[head](space, space)
        assert space.alpha_eq(space)
        assert space.unify(V.x) == {V.x: space}
        assert space.subs({space: S.replaced}) == S.replaced
        assert space.map(lambda atom: S.replaced if atom is space else atom) == S.replaced
        for name in ("head", "args", "children"):
            with pytest.raises(TypeError, match="leaf atom"):
                getattr(space, name)
        with pytest.raises(AttributeError, match="value"):
            _ = space.value


def test_space_identity_doors_follow_the_handle_lifetime():
    """Space identity doors follow the handle lifetime."""
    with MeTTa() as context:
        space = context.space()
        try:
            assert space.self is space
            assert space.runtime is context.runtime
            assert space.to_wire() == ["p", str(space.name)]
            assert space.metatype == "Grounded"
            assert not space.dropped and not context.closed
            with space.metta as borrowed:
                assert borrowed.self == space
                assert borrowed.runtime is context.runtime
            assert not space.dropped
        finally:
            space.drop()
        assert space.dropped and bool(space)
        assert space.self is space
        assert space.runtime is context.runtime
        for name in ("name", "to_wire"):
            with pytest.raises(MettaError, match="dropped"):
                member = getattr(space, name)
                if callable(member):
                    member()
        borrowed = space.metta
        try:
            assert borrowed.self is space
            with pytest.raises(MettaError, match="dropped"):
                borrowed.eval(S.unit())
        finally:
            borrowed.close()


def test_the_interactive_door_reaches_the_owned_runtime(monkeypatch):
    """The interactive door reaches the owned runtime."""
    calls = []
    with MeTTa() as context:
        monkeypatch.setattr(context.runtime._janus, "prolog", lambda: calls.append("entered"))
        context.self.prolog()
        context.prolog()
    assert calls == ["entered", "entered"]


@pytest.mark.parametrize("name", ("pure", "reads", "writes", "io"))
def test_effect_sugars_are_their_declared_parameter_points(name):
    """Effect sugars are their declared parameter points."""
    from metta.ops import registered

    row = next(row for row in DOORS if row.key == f"space:{name}")
    assert row.sugar_of.base == "space:op"
    effect = EffectClass(dict(row.sugar_of.fixed)["effect"])
    operation = f"door-effect-{name}"
    with MeTTa() as context:
        try:
            getattr(context.self, name)(lambda value: value, name=operation)
            assert registered()[operation].effect is effect
            assert context.eval(S[operation](7)) == [7]
        finally:
            context.unregister_op(operation)


@dataclass
class _DoorRecord:
    id: int
    label: str


@pytest.mark.parametrize("lazy", (False, True))
def test_result_door_projections_preserve_fields_and_host_conversions(lazy):
    """Result door projections preserve fields and host conversions."""
    from metta.results import Answers, Rows

    with MeTTa() as context, ExitStack() as held:
        space = context.self
        space.add(S.door_record(1, "Ada"), S.door_record(2, "Bob"))

        def fresh(pattern=None):
            pattern = S.door_record(V.id, V.label) if pattern is None else pattern
            result = space.match(pattern) if lazy else space.match(pattern, into=Rows)
            if isinstance(result, Answers):
                held.enter_context(result)
            return result

        assert fresh().columns == ("id", "label")
        assert list(fresh().column("id")) == [1, 2]
        assert fresh().first().id == 1
        assert fresh(S.door_record(1, V.label)).one().label == "Ada"
        assert fresh().table() == {"id": [1, 2], "label": ["Ada", "Bob"]}
        assert fresh().to_dicts() == [{"id": 1, "label": "Ada"}, {"id": 2, "label": "Bob"}]
        assert fresh().into(_DoorRecord) == [_DoorRecord(1, "Ada"), _DoorRecord(2, "Bob")]
        assert fresh().pipe(lambda rows, offset: [row.id.value + offset for row in rows], 10) == [11, 12]
        clean = fresh()
        assert clean.raise_for_errors() is clean
        assert "Ada" in fresh().render("{rows:table}")
        assert "none unifies" in fresh(S.door_record(3, V.label)).why()
        assert fresh().explain().plan is not None
        assert hasattr(fresh().arrow(), "__arrow_c_stream__")
        space.add(S.door_constructed(S["_DoorRecord"](3, "Cid")))
        assert fresh(S.door_constructed(V.value)).build(_DoorRecord) == [_DoorRecord(3, "Cid")]
        if lazy:
            projected = fresh()
            assert list(projected.rows) == list(projected)
            assert projected.index(projected[1]) == 1
            cached = fresh()
            first = cached.first()
            cached.close()
            assert list(cached) == [first]

        def build(_source, projection, _view):
            return projection.table()

        seam.frame.register("door-contract-frame", module="types", accessor=lambda *_: None, build=build)
        try:
            assert fresh().to("types") == {"id": [1, 2], "label": ["Ada", "Bob"]}
        finally:
            seam.frame.unregister("door-contract-frame")


def test_remote_door_contracts_preserve_capability_refusals():
    """Remote door contracts preserve capability refusals."""
    from metta.remote import RemoteSpace

    remote = RemoteSpace(lambda _operation, _payload: {"atoms": []}, "&data")
    assert remote.delivers() is None
    assert "event" in remote.refusal("subscribe")
    assert remote.refusal("enumerate") is None


def test_remote_storage_doors_use_the_declared_operation_protocol():
    """Remote storage doors use the declared operation protocol."""
    from metta.remote import Gateway, RemoteSpace

    with MeTTa() as context:
        gateway = Gateway(context)
        try:
            remote = RemoteSpace(gateway, str(context.self.name))
            remote.add(S.remote_row(1))
            remote.add_many([S.remote_row(2), S.remote_row(2)])
            assert list(remote.atoms()) == [S.remote_row(1), S.remote_row(2), S.remote_row(2)]
            assert remote.remove(S.remote_row(2))
            assert not remote.remove(S.remote_row(3))
            assert list(remote.match(S.remote_row(V.x))) == [S.remote_row(1), S.remote_row(2)]
        finally:
            gateway.close()


def test_remote_generated_doors_release_their_cursor():
    """Remote generated doors release their cursor."""
    from metta.remote import RemoteSpace

    called = []

    def transport(operation, payload):
        called.append((operation, payload))
        if operation == "ask":
            return {"atoms": [S.row(1).to_wire()], "cursor": "held"}
        if operation == "next":
            return {"atoms": [S.row(2).to_wire()], "cursor": None}
        return {"stopped": True}

    remote = RemoteSpace(transport, "&data")
    with remote.stream(S.row(V.x), batch=1) as cursor:
        assert next(cursor) == S.row(1)
    assert [operation for operation, _ in called] == ["ask", "stop"]
    cursor.close()
    assert len(called) == 2
    called.clear()
    with remote.stream(S.row(V.x), batch=1) as cursor:
        assert list(cursor) == [S.row(1), S.row(2)]
    assert [operation for operation, _ in called] == ["ask", "next"]


def test_door_sync_detects_a_planted_change_in_each_projection(monkeypatch, capsys):
    """Door sync detects a planted change in each projection."""
    import aiogen
    import initstubgen
    import reference

    generated = dict.fromkeys(doorgen.projections(doorgen.all_rows()))
    generated[doorgen.CORE / "_schemas.py"] = doorgen.SCHEMA_END
    generated[doorgen.ROOT / "llms.txt"] = doorgen.SHEET_END
    generated.update({aiogen.AIO: aiogen.END, aiogen.INIT: aiogen.MODULE_END, initstubgen.STUB: None})
    generated.update(dict.fromkeys(page for page, source, _ in reference.sources() if source.endswith(('_space.py', 'results.py', 'remote.py', '__init__.py'))))
    real_read = Path.read_text
    for path in generated:
        original = real_read(path)
        if path.suffix == ".py" and path.name in {"_space.py", "results.py", "remote.py"}:
            marker = next(line for line in original.splitlines() if line.startswith(doorgen.END))
        else:
            marker = generated[path]
        planted = original.replace(marker, "    # planted projection change\n" + marker, 1) if marker else original + "\n# planted projection change\n"

        def read(candidate, *args, _path=path, _planted=planted, **kwargs):
            return _planted if candidate == _path else real_read(candidate, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "read_text", read)
            assert doorgen.main([]) == 1, path
        capsys.readouterr()
    assert doorgen.main([]) == 0


def test_contract_checks_detect_signature_and_evidence_drift():
    """Contract checks detect signature and evidence drift."""
    row = next(row for row in DOORS if row.key == "space:parse")
    bad_signature = replace(row, signatures=(Signature("self, invented: int"),))
    bad_evidence = replace(row, evidence=("extensions/python/tests/repository/test_door_rows.py::test_missing",))
    for changed, message in ((bad_signature, "signature differs"), (bad_evidence, "does not exist")):
        rows = tuple(changed if current.key == row.key else current for current in DOORS)
        assert any(message in finding for finding in doorgen.contract_findings(rows))


def test_documentation_parity_checks_the_evidence_snapshot():
    """Changing only a citation cannot silently change a row's evidence."""
    row = next(row for row in DOORS if row.key == "space:answers")
    changed = replace(row, docs=row.docs.replace(
        "2d4d4583c2d82e90bb21a7e8671842f126edd4f4", "unresolved-evidence",
    ))
    assert changed.docs != row.docs
    rows = tuple(changed if current.key == row.key else current for current in DOORS)
    assert any("documentation differs" in finding for finding in doorgen.contract_findings(rows))


def test_contract_checks_refuse_missing_coverage_and_unbacked_refusals():
    """Contract checks refuse missing coverage and unbacked refusals."""
    row = next(row for row in DOORS if row.key == "space:bind")
    wrong = Refusal(RefusalKind.type, "extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:capacity]")
    for changed, message in (
        (replace(row, evidence=()), "needs signatures, documentation, and evidence"),
        (replace(row, refuses=()), "local refusal 'type' has no declared witness"),
        (replace(row, refuses=(wrong,)), "witness must assert pytest.raises(TypeError)"),
    ):
        rows = tuple(changed if current.key == row.key else current for current in DOORS)
        assert any(message in finding for finding in doorgen.contract_findings(rows))
    with pytest.raises(ValueError, match="repeats a refusal kind"):
        validate((replace(row, refuses=(wrong, wrong)),))


def test_contract_checks_refuse_a_handwritten_public_parameter_point(monkeypatch):
    """Contract checks refuse a handwritten public parameter point."""
    path = doorgen.CORE / "_space.py"
    original = path.read_text()
    marker = doorgen.START + "Space"
    planted = original.replace(marker, "    def extra_answer_point(self, target):\n        return self.eval(target, answer='all')\n\n" + marker, 1)
    real_read = Path.read_text

    def read(candidate, *args, **kwargs):
        return planted if candidate == path else real_read(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    assert any("extra_answer_point: public implementation" in finding for finding in doorgen.contract_findings())


def test_contract_checks_require_an_inherited_slot_to_exist():
    """Contract checks require an inherited slot to exist."""
    row = next(row for row in DOORS if row.key == "space:value")
    missing = replace(row, body=Body("metta._atoms_core", "Grounded.missing_door_slot"))
    assert any("implementation" in finding and "is absent" in finding for finding in doorgen.contract_findings((missing,)))


def test_operation_rows_generate_the_complete_remote_wire_contract():
    """Operation rows generate the complete remote wire contract."""
    from metta import _schemas

    rows = [row.remote for row in DOORS if row.remote is not None]
    expected = [(row.operation, row.request, row.response, row.summary) for row in rows]
    assert list(_schemas._OPERATIONS) == expected
    assert len({row.operation for row in rows}) == 8
    assert {f"/{row.operation}" for row in rows} < set(_schemas._paths(secured=False))
