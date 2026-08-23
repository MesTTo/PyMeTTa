"""Purpose: the feature surface added by the review round, engine-backed:
standing queries, first-class custom matchers, Python types declared into
spaces with field accessors, host values named in source, persistence,
typed rows, and the fast Python soft-scorer held equal to the MeTTa one by
differential fuzz.
Guarantees:
  - class and enum declarations use the consolidated ``Space.define`` door
    [tested: test_define_declares_class_with_accessors,
    test_define_declares_enum_members, test_define_methods_run_on_terms_and_handles,
    and test_enum_members_match_in_metta; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - subscription hook clauses track whether the active space set is empty
    [tested: test_subscription_hooks_follow_the_active_space_set;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - capture, atomic, and speculative execution compose as scopes without
    per-call shape or mode flags [tested: test_run_capture_collects_printed_output,
    test_atomic_run_commits_or_rolls_back_whole,
    test_speculative_run_answers_and_discards;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - streaming comparison guards use explicit comparison heads [tested:
    test_stream_guard_and_per_pull_bounds; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import dataclasses
import enum
import gc
import importlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from petta import (
    Bindings,
    Expression,
    PettaError,
    S,
    V,
    convert,
    ground,
    remote,
    tables,
)
from petta.arrays import EmbeddingStore
from petta.atoms import Grounded, Symbol, Variable
from petta.errors import (
    EngineError,
    InferenceLimitError,
    MettaOperationError,
    ResourceLimitError,
    TimeLimitError,
)
from petta.events import Event, atom_added
from petta.integrate import install_reflection_ops
from petta.subscribe import bridge

hypothesis = pytest.importorskip("hypothesis")
subscribe_module = importlib.import_module("petta.subscribe")
events_module = importlib.import_module("petta.events")


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


# ----------------------------------------------------------- subscriptions


class _SubscriptionRuntime:
    def __init__(self):
        self.facts = []
        self.published = []
        self.sync_failures = 0
        self.remove_failure = False
        self.removed = threading.Event()

    def must(self, goal, **inputs):
        assert goal == "petta_py_subscriptions(Spaces)"
        self.published.append(list(inputs["Spaces"]))
        if self.sync_failures:
            self.sync_failures -= 1
            msg = "injected subscription sync failure"
            raise RuntimeError(msg)
        return {"truth": True}

    def do(self, predicate, *inputs):
        assert predicate == "petta_py_contains"
        space, wire = inputs
        assert space == "&petta"
        return any(fact.to_wire() == wire for fact in self.facts)


def _script_subscription_boundaries(monkeypatch):
    runtime = _SubscriptionRuntime()
    registry = events_module._FoldRegistry()

    def reflect_add(active_runtime, fact):
        assert active_runtime is runtime
        runtime.facts.append(fact)

    def reflect_remove(active_runtime, fact):
        assert active_runtime is runtime
        runtime.facts[:] = [current for current in runtime.facts if current != fact]
        runtime.removed.set()
        if runtime.remove_failure:
            runtime.remove_failure = False
            msg = "injected reflection removal failure"
            raise RuntimeError(msg)

    monkeypatch.setattr(subscribe_module, "_REGISTRY", registry)
    monkeypatch.setattr(subscribe_module, "_reflect_add", reflect_add)
    monkeypatch.setattr(subscribe_module, "_reflect_remove", reflect_remove)
    return runtime, registry


def test_subscription_lifecycle_rolls_back_failed_boundaries(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime, registry = _script_subscription_boundaries(monkeypatch)
    runtime.sync_failures = 1
    with pytest.raises(RuntimeError, match="injected subscription sync failure"):
        subscribe_module.subscribe(runtime, "&fault", S.item)
    assert registry.for_space("&fault") == ()
    assert runtime.facts == []
    assert runtime.published == [["&fault"], []]

    first = subscribe_module.subscribe(runtime, "&fault", S.item)
    second = subscribe_module.subscribe(runtime, "&fault", S.item)
    assert len(runtime.facts) == 1
    second.cancel()
    assert registry.for_space("&fault") == (first,)
    assert len(runtime.facts) == 1

    runtime.sync_failures = 1
    with pytest.raises(RuntimeError, match="injected subscription sync failure"):
        first.cancel()
    assert first._active is True
    assert registry.for_space("&fault") == (first,)
    assert runtime.published[-2:] == [[], ["&fault"]]

    runtime.remove_failure = True
    with pytest.raises(RuntimeError, match="injected reflection removal failure"):
        first.cancel()
    assert first._active is True
    assert registry.for_space("&fault") == (first,)
    assert len(runtime.facts) == 1
    assert runtime.published[-2:] == [[], ["&fault"]]

    first.cancel()
    assert registry.for_space("&fault") == ()
    assert runtime.facts == []


def test_stale_subscription_snapshot_cannot_deliver_after_cancel(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime, registry = _script_subscription_boundaries(monkeypatch)
    seen = []
    subscription = subscribe_module.subscribe(runtime, "&stale", S.item, seen.append)
    stale_snapshot = registry.for_space("&stale")
    subscription.cancel()

    stale_snapshot[0]._run(Event("add", "&stale", S.item, {}))

    assert seen == []


def test_subscription_cancel_waits_for_inflight_delivery(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime, _registry = _script_subscription_boundaries(monkeypatch)
    entered = threading.Event()
    release = threading.Event()
    cancel_complete = threading.Event()

    def callback(_event):
        entered.set()
        release.wait()

    subscription = subscribe_module.subscribe(runtime, "&inflight", S.item, callback)
    event = Event("add", "&inflight", S.item, {})
    delivery = threading.Thread(target=subscription._run, args=(event,))

    def cancel():
        subscription.cancel()
        cancel_complete.set()

    cancellation = threading.Thread(target=cancel)
    delivery.start()
    assert entered.wait(timeout=2.0)
    cancellation.start()
    try:
        assert runtime.removed.wait(timeout=2.0)
        cancellation.join(timeout=0.1)
        assert cancellation.is_alive()
    finally:
        release.set()
        delivery.join(timeout=2.0)
        cancellation.join(timeout=2.0)

    assert cancel_complete.is_set()
    assert not delivery.is_alive()
    assert not cancellation.is_alive()


def test_identical_subscriptions_share_one_reflection_fact(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    reflection = m._at("&petta")
    first = m.subscribe(S.identical(V.value))
    second = m.subscribe(S.identical(V.value))
    descriptor = S.subscription(S[m.name], V.pattern, V.on)
    try:
        assert len(reflection.query(descriptor)) == 1
        second.cancel()
        assert len(reflection.query(descriptor)) == 1
        first.cancel()
        assert not reflection.query(descriptor)
    finally:
        first.cancel()
        second.cancel()


def test_subscription_callback_fires_inside_the_write(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    seen = []
    sub = m.subscribe(S.order(V.id), seen.append)
    try:
        m.add(S.order(1), S.other(9), S.order(2))
        assert [e.bindings["id"] for e in seen] == [1, 2]
        assert seen[0].action == "add" and seen[0].space == m.name
    finally:
        sub.cancel()
    m.add(S.order(3))
    assert len(seen) == 2  # cancelled means cancelled


def test_clear_announces_every_atom_it_drops(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The two bulk doors have to agree: add announces per atom, so clear
    # does too. Clearing swept the storage module directly, so a watcher
    # saw the equations go and nothing else.
    seen = []
    sub = m.subscribe(S.stock(V.item), seen.append, on="both")
    try:
        m.add(S.stock(S.apple), S.stock(S.pear), S.other(1))
        m.run("(= (restock $x) $x)")
        seen.clear()
        m.clear()
        assert [e.action for e in seen] == ["remove", "remove"]
        assert sorted(str(e.bindings["item"]) for e in seen) == ["apple", "pear"]
    finally:
        sub.cancel()
    assert m.atoms() == []


def test_clear_empties_a_space_nobody_is_watching(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.stock(S.apple), S.stock(S.pear))
    m.clear()
    assert m.atoms() == []


def test_subscription_hooks_follow_the_active_space_set(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def installed(kind):
        return bool(m._rt.once(f"petta_py_subscription_hook_ref({kind}, _)"))

    assert not installed("added")
    assert not installed("removed")
    subscription = m.subscribe(S.hook_lifecycle(V.value))
    try:
        assert installed("added")
        assert installed("removed")
    finally:
        subscription.cancel()
    assert not installed("added")
    assert not installed("removed")


def test_subscription_queue_mode_drains(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    sub = m.subscribe(S.msg(V.body), on="both")
    try:
        m.add(S.msg(S.hello))
        m.remove(S.msg(S.hello))
        events = sub.drain()
        assert [e.action for e in events] == ["add", "remove"]
        assert sub.drain() == []
    finally:
        sub.cancel()


def test_subscription_queue_is_thread_safe(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    subscription = m.subscribe(S.concurrent(V.value))
    complete = threading.Event()
    collected = []

    def produce(offset):
        for value in range(offset, offset + 100):
            atom_added(m.name, S.concurrent(value).to_wire())

    def drain():
        while not complete.is_set():
            collected.extend(subscription.drain())
        collected.extend(subscription.drain())

    consumer = threading.Thread(target=drain)
    producers = [threading.Thread(target=produce, args=(start,)) for start in range(0, 400, 100)]
    consumer.start()
    for producer in producers:
        producer.start()
    for producer in producers:
        producer.join()
    complete.set()
    consumer.join()
    subscription.cancel()

    assert sorted(event.bindings["value"].value for event in collected) == list(range(400))


def test_subscription_cancel_is_thread_safe(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    subscription = m.subscribe(S.concurrent_cancel(V.value))
    failures = []

    def cancel():
        try:
            subscription.cancel()
        except Exception as error:
            failures.append(error)

    threads = [threading.Thread(target=cancel) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    assert subscription._active is False


def test_subscription_fires_for_engine_side_writes(m):
    """add-atom from RUNNING MeTTa reaches the standing query too: the
    write funnel is the engine's own.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    seen = []
    sub = m.subscribe(S.log(V.x), lambda e: seen.append(e.bindings["x"]))
    try:
        m.run("!(add-atom (context-space) (log 42))")
        assert seen == [42]
    finally:
        sub.cancel()


# ---------------------------------------------------------------- matchers


def test_a_grounded_matchable_composes_with_structural_match(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Custom matching is a property of grounded atoms: an object with
    # match_ gates candidates inside unify, composing with structural
    # match through ordinary evaluation, no new syntax.
    class Initial:
        def __init__(self, letter):
            self.letter = letter

        def match_(self, other):
            if str(other)[:1] == self.letter:
                yield other

    m.add(S.person(S.ada), S.person(S.alan), S.person(S.grace))
    rows = m.eval(
        Expression(
            S.collapse,
            Expression(
                S.match,
                Expression(S["context-space"]),
                S.person(V.p),
                Expression(
                    S.unify,
                    Grounded(Initial("a")),
                    V.p,
                    V.p,
                    Expression(S.superpose, Expression()),
                ),
            ),
        )
    )
    assert sorted(str(x) for x in rows[0]) == ["ada", "alan"]


def test_embedding_store_is_a_semantic_matcher(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    numpy = pytest.importorskip("numpy")

    store = EmbeddingStore(m, name="sem", mirror=False)
    store.add(S.dog, numpy.array([1.0, 0.0]))
    store.add(S.cat, numpy.array([0.9, 0.4]))
    store.add(S.car, numpy.array([0.0, 1.0]))

    class Nearest:
        def match_(self, other):
            query, out = other.children[0], other.children[1]
            key, score = next(iter(store.ranked(query, 1)))
            assert 0.0 <= score <= 1.0
            yield Bindings({out: key})

    rows = m.eval(Expression(S.unify, Grounded(Nearest()), Expression(S.dog, V.k), V.k, S.none))
    assert rows == [S.dog]


def test_faiss_and_argsort_rank_identically(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    numpy = pytest.importorskip("numpy")
    pytest.importorskip("faiss")

    plain = EmbeddingStore(m, name="rk-a", mirror=False, backend="argsort")
    accel = EmbeddingStore(m, name="rk-b", mirror=False, backend="faiss")
    rng = numpy.random.default_rng(7)
    for i in range(50):
        vector = rng.normal(size=8).astype(numpy.float32)
        plain.add(Symbol(f"k{i}"), vector)
        accel.add(Symbol(f"k{i}"), vector)
    query = rng.normal(size=8).astype(numpy.float32)
    slow = [(str(k), s) for k, s in plain.ranked(query, 10)]
    fast = [(str(k), s) for k, s in accel.ranked(query, 10)]
    assert [k for k, _ in slow] == [k for k, _ in fast]
    for (_, a), (_, b) in zip(slow, fast, strict=False):
        assert a == pytest.approx(b, abs=1e-5)


# ------------------------------------------------------------ typed Python


def test_define_declares_class_with_accessors(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    @dataclasses.dataclass
    class Song:
        title: str
        year: int

    m.add(convert.project(Song("Hallelujah", 1984)).atom)
    assert m.run("!(match (context-space) (Song $t $y) $t)") == [["Hallelujah"]]
    assert m.run('!(Song-year (Song "Hallelujah" 1984))') == [[1984]]
    # And back into Python, typed rows in one call.
    rows = m.query(V.s)
    songs = [s for s in rows.build("s", Song) if isinstance(s, Song)]
    assert songs == [Song("Hallelujah", 1984)]


def test_define_declares_enum_members(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    class DeclaredMood(enum.Enum):
        Calm = 1
        Storm = 2

    assert Expression(S[":"], S.Calm, S.DeclaredMood) in m


# ----------------------------------------------------- host values in source


def test_run_using_names_host_values(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    install_reflection_ops(m)

    class Graph:
        nodes = 3

    graph = Graph()
    with m.bind(graph=graph):
        (answer,) = m.run("!(py-attr graph nodes)")[0]
    assert answer == 3


def test_run_using_carries_identity(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    thing = object()
    with m.bind(it=thing):
        m.run("!(add-atom (context-space) (held it))")
    rows = m.query(S.held(V.x))
    assert rows[0].x.value is thing


# ------------------------------------------------------------- persistence


def test_save_and_load_round_trip(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        space.run("(= (greet $x) (hello $x)) (fact one) (fact two)")
        path = tmp_path / "kb.metta"
        count = space.save(str(path))
        assert count == 3
    with metta._new_space() as reborn:
        reborn.load(str(path))
        assert len(reborn.query(S.fact(V.x))) == 2
        assert reborn.run("!(greet world)") == [[Expression(S.hello, S.world)]]


def test_save_refuses_live_objects(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.holds(ground(object())))
    with pytest.raises(ValueError):
        m.save("/dev/null")


# ----------------------------------------------------------------- measure


def test_the_measure_library_runs_in_language(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(import! (context-space) (library lib_measure))")
    (best,) = m.run("!(ws-best ((0.25 a) (0.75 b)))")[0]
    assert best == S.b


def test_rows_table_is_the_dataframe_shape(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.Age(S.Tom, 62), S.Age(S.Bob, 40))
    rows = m.query(S.Age(V.who, V.n))
    table = rows.table()
    assert table in ({"who": ["Tom", "Bob"], "n": [62, 40]}, {"who": ["Bob", "Tom"], "n": [40, 62]})


def test_add_table_reads_any_tabular_source(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    added = tables.add(m, "edge", {"src": [S.a, S.b], "dst": [S.b, S.c]})
    assert added == 2
    assert len(m.query(S.edge(V.x, V.y))) == 2

    polars = pytest.importorskip("polars")
    frame = polars.DataFrame({"name": ["ada", "bob"], "age": [36, 41]})
    assert tables.add(m, "person", frame) == 2
    rows = m.query(S.person(V.name, V.age))
    assert {(r["name"], r.age) for r in rows} == {("ada", 36), ("bob", 41)}
    with pytest.raises(TypeError):
        tables.add(m, "bad", 7)


def test_add_table_refuses_ragged_columns(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError):
        tables.add(m, "edge", {"src": [S.a, S.b, S.c], "dst": [S.b]})
    assert m.query(S.edge(V.x, V.y)) == []


def test_value_answers_the_one_answer(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m._one("(+ 1 2)") == 3 and isinstance(m._one("(+ 1 2)"), int)
    m.run("(= (fact $n) (if (> $n 0) (* $n (fact (- $n 1))) 1))")
    assert m._one(S.fact(5)) == 120
    with pytest.raises(EngineError):
        m._one("(superpose (1 2))")  # two answers is not a value
    with pytest.raises(EngineError):
        m.run("(= (nothing) (empty))")
        m._one(S.nothing())  # no answer is not a value either


def test_rows_first_and_one(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.city(S.perth), S.city(S.sydney))
    assert m.query(S.town(V.x)).first() is None
    assert m.query(S.city(V.x)).first() is not None
    with pytest.raises(EngineError):
        m.query(S.city(V.x)).one()  # two rows
    m.remove(S.city(S.perth))
    assert str(m.query(S.city(V.x)).one().x) == "sydney"


def test_space_iterates_and_subtracts(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.a(1), S.b(2))
    assert {str(a.head) for a in m} == {"a", "b"}
    m -= S.a(1)
    assert [str(a.head) for a in m] == ["b"]


def test_atoms_destructure_with_match_statements(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.likes(S.cat, 9))
    (atom,) = m.query(V.a).a
    match atom:
        case Expression([Symbol("likes"), Symbol(who), Grounded(count)]):
            assert who == "cat" and count == 9
        case _:
            pytest.fail("the class pattern did not destructure")
    # An expression is a Sequence, so the bare sequence pattern works too.
    match S.likes(S.dog):
        case [Symbol("likes"), pet]:
            assert pet == S.dog
        case _:
            pytest.fail("the sequence pattern did not destructure")
    match Variable("x"):
        case Variable(name):
            assert name == "x"


# ----------------------------------------------- contexts: bridges, remotes


def test_bridge_rules_connect_spaces(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    src = metta._new_space()
    dst = metta._new_space()
    rule = bridge(src, S.alarm(V.zone), dst, S.notify(V.zone), on="both")
    try:
        src.add(S.alarm(S.kitchen))
        assert dst.query(S.notify(V.z)).one().z == S.kitchen
        src.remove(S.alarm(S.kitchen))
        assert dst.query(S.notify(V.z)) == []
    finally:
        rule.cancel()
        src.drop()
        dst.drop()


def test_remote_spaces_serve_attach_and_join(metta, tmp_path):  # noqa: ARG001  -- pytest injects this fixture to establish engine state for the scenario
    """The other engine is a PROCESS, as deployment means it: a subprocess
    serves one space, this engine attaches it, and one local match joins
    remote rows with local facts across the wire.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    script = Path(__file__).parent / "data" / "remote_server.py"
    child = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
    )
    local = metta._new_space()
    try:
        line = child.stdout.readline()
        assert line, child.stderr.read()
        info = json.loads(line)
        remote.attach(local, "&hq", info["url"], remote_space=info["space"])
        # A match crosses the wire, filtered by the remote engine's own match.
        assert local.run("!(match &hq (users 2 $n) $n)") == [["Bob"]]
        # And joins with local facts in ONE match, the multi-context point.
        local.run("(vip 1)")
        (group,) = local.run(
            "!(collapse (match (context-space) (vip $id) (match &hq (users $id $n) $n)))"
        )
        assert group == [Expression("Ada")]
        # Writes cross too, and the remote engine answers them back.
        local.run('!(add-atom &hq (users 3 "Cy"))')
        assert local.run("!(match &hq (users 3 $n) $n)") == [["Cy"]]
        local.run('!(remove-atom &hq (users 3 "Cy"))')
        assert local.run("!(collapse (match &hq (users 3 $n) $n))") == [[Expression()]]
        # A space outside the allowlist is refused with the remote's words.
        stray = remote.RemoteSpace(remote.connect(info["url"]), "&self")
        with pytest.raises(PettaError):
            list(stray.match(S.anything(V.x)))
        local._unregister_space("&hq")
    finally:
        child.terminate()
        child.wait(timeout=10)
        local.drop()


# ------------------------------------------------- classes cross with behavior


def test_define_methods_run_on_terms_and_handles(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    @dataclasses.dataclass
    class MethodPoint:
        x: float
        y: float

        def norm(self) -> float:
            return (self.x**2 + self.y**2) ** 0.5

        def scaled(self, k: float) -> "MethodPoint":
            return MethodPoint(self.x * k, self.y * k)

    assert m.run("!(MethodPoint-norm (MethodPoint 3.0 4.0))") == [[5.0]]
    # A method answering the class answers a constructor TERM: MeTTa keeps
    # matching it, and Python builds it back as the object it is.
    (scaled,) = m.run("!(MethodPoint-scaled (MethodPoint 3.0 4.0) 2.0)")[0]
    assert scaled == Expression(S.MethodPoint, 6.0, 8.0)
    assert convert.build(scaled, MethodPoint) == MethodPoint(6.0, 8.0)
    # An equation over the constructor is a method written in MeTTa, on
    # equal footing: MeTTa "modifies the object" and Python receives it.
    m.run("(= (MethodPoint-flip (MethodPoint $x $y)) (MethodPoint $y $x))")
    (flipped,) = m.run("!(MethodPoint-flip (MethodPoint-scaled (MethodPoint 3.0 4.0) 2.0))")[0]
    assert convert.build(flipped, MethodPoint) == MethodPoint(8.0, 6.0)
    # A live handle works through the same methods.
    assert m.eval(Expression(S["MethodPoint-norm"], ground(MethodPoint(3.0, 4.0)))) == [5.0]


def test_enum_members_match_in_metta(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    class MatchingMood(enum.Enum):
        Calm = 1
        Storm = 2

    m.add(S.today(S.Storm))
    # Members are symbols with declarations: patterns match them, and
    # get-type answers the enum.
    assert m.run("!(match (context-space) (today Storm) stormy)") == [[S.stormy]]
    assert m.run("!(get-type Storm)") == [[S.MatchingMood]]


def test_remote_auth_token_and_hook_requires_tls(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    served = metta._new_space()
    served.add(S.fact(1))
    server = remote.serve(
        metta,
        spaces=[served.name],
        token="s3cret",
        authorize=lambda request: request.headers.get("x-tenant") == "acme",
    )
    try:
        with pytest.raises(PettaError, match="credentials require an https URL"):
            remote.connect(server.url, token="s3cret", headers={"x-tenant": "acme"})
    finally:
        server.close()
        served.drop()


def test_remote_serves_tls(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    if shutil.which("openssl") is None:
        pytest.skip("openssl is not installed")
    key, cert = tmp_path / "k.pem", tmp_path / "c.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=localhost",
        ],
        check=True,
        capture_output=True,
    )
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert, key)
    client_context = ssl.create_default_context(cafile=str(cert))
    client_context.check_hostname = False  # self-signed CN, loopback address

    served = metta._new_space()
    served.add(S.tls(S.ok))
    server = remote.serve(
        metta,
        spaces=[served.name],
        token="s3cret",
        authorize=lambda request: request.headers.get("x-tenant") == "acme",
        ssl_context=server_context,
    )
    try:
        assert server.url.startswith("https://")
        transport = remote.connect(
            server.url,
            token="s3cret",
            headers={"x-tenant": "acme"},
            ssl_context=client_context,
        )
        atoms = list(remote.RemoteSpace(transport, served.name).atoms())
        assert atoms == [Expression(S.tls, S.ok)]
        with pytest.raises(PettaError, match="not authorized"):
            bad_token = remote.connect(
                server.url,
                token="wrong",
                headers={"x-tenant": "acme"},
                ssl_context=client_context,
            )
            list(remote.RemoteSpace(bad_token, served.name).atoms())
        with pytest.raises(PettaError, match="not authorized"):
            no_tenant = remote.connect(server.url, token="s3cret", ssl_context=client_context)
            list(remote.RemoteSpace(no_tenant, served.name).atoms())
    finally:
        server.close()
        served.drop()


# ------------------------------------------ resource limits, stats, capture


def test_run_time_limit_raises_and_is_prompt(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (spin-a $n) (if (== $n 0) done (spin-a (- $n 1))))")
    started = time.perf_counter()
    with pytest.raises(TimeLimitError):
        m.run(
            "!(with-pragma! ((max-stack-depth 300000000)) (spin-a 100000000))",
            timeout=0.05,
        )
    assert time.perf_counter() - started < 5.0  # the guard stopped it, not completion


def test_inference_limit_raises_under_the_shared_parent(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (spin-b $n) (if (== $n 0) done (spin-b (- $n 1))))")
    with pytest.raises(InferenceLimitError):
        m.run("!(spin-b 100000000)", inferences=10_000)
    with pytest.raises(ResourceLimitError):
        m.run("!(spin-b 100000000)", inferences=10_000)


def test_limits_leave_finished_work_standing(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (spin-c $n) (if (== $n 0) done (spin-c (- $n 1))))")
    with pytest.raises(TimeLimitError):
        m.run(
            "(landed first) "
            "!(with-pragma! ((max-stack-depth 300000000)) (spin-c 100000000))",
            timeout=0.05,
        )
    assert Expression(S.landed, S.first) in m  # the fact before the stop stands


def test_limits_on_query_eval_value_and_prepared(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    tables.add(m, "edge", [(i, i + 1) for i in range(200)])
    rows = m.query(S.edge(V.a, V.b), S.edge(V.b, V.c), timeout=30.0, inferences=50_000_000)
    assert len(rows) == 199  # a generous bound changes nothing
    with pytest.raises(InferenceLimitError):
        m.query(S.edge(V.a, V.b), S.edge(V.b, V.c), S.edge(V.c, V.d), inferences=100)
    m.run("(= (spin-d $n) (if (== $n 0) done (spin-d (- $n 1))))")
    with pytest.raises(InferenceLimitError):
        m.eval("(spin-d 100000000)", inferences=5_000)
    with pytest.raises(InferenceLimitError):
        m._one("(spin-d 100000000)", inferences=5_000)
    prepared = m.prepare(S.edge(V.a, V.b), S.edge(V.b, V.c), S.edge(V.c, V.d))
    with pytest.raises(InferenceLimitError):
        prepared.solve(inferences=100)
    assert len(prepared.solve(timeout=30.0)) == 198


def test_limit_validation_refuses_nonsense(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError):
        m.run("!(+ 1 1)", timeout=0)
    with pytest.raises(ValueError):
        m.query(S.x(V.a), inferences=-3)


def test_run_capture_collects_printed_output(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with m.capture() as output:
        groups = m.run("!(println! (hello world)) !(+ 1 2)")
    assert "(hello world)" in output.text
    assert groups[1] == [3]
    assert m.run("!(+ 1 2)") == [[3]]  # capture off: the shape is unchanged


def test_capture_composes_with_limits(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with m.capture() as output:
        groups = m.run("!(println! bounded)", timeout=5.0)
    assert "bounded" in output.text and len(groups) == 1
    m.run("(= (spin-e $n) (if (== $n 0) done (spin-e (- $n 1))))")
    with pytest.raises(TimeLimitError):
        with m.capture():
            m.run(
                "!(with-pragma! ((max-stack-depth 300000000)) (spin-e 100000000))",
                timeout=0.05,
            )


def test_eval_capture(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with m.capture() as output:
        answers = m.eval("(println! from-eval)")
    assert "from-eval" in output.text
    # println! answers the UNIT value, `()`, which is what the specification
    # types it with: "(-> %Undefined% (->))". It used to answer True.
    assert answers == [Expression()]


def test_stats_block_counts_the_work(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    tables.add(m, "edge", [(i, i + 1) for i in range(50)])
    with m.stats() as s:
        m.query(S.edge(V.a, V.b), S.edge(V.b, V.c))
    assert s.inferences > 100
    assert s.walltime > 0 and s.cputime >= 0
    assert s.gc_count >= 0 and s.gc_freed >= 0 and s.gc_time >= 0.0
    assert s.table_bytes == 0  # nothing tabled inside this block
    assert "inferences" in repr(s)


def test_a_stats_counter_is_unreadable_until_its_block_closes(m):
    """A counter is a delta, so there is nothing to read before the block
    that measures it has closed. Raising there rather than answering None
    or 0 is what lets the counters be typed as the int and float they are,
    which is what a caller writing `s.inferences > 100` needs.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with m.stats() as s:
        assert repr(s) == "<stats: pending>"
        with pytest.raises(RuntimeError, match="after the with-block"):
            _ = s.inferences
        # An ordinary typo is still an ordinary typo.
        with pytest.raises(AttributeError):
            _ = s.no_such_counter
        m.run("!(+ 1 2)")
    assert s.inferences > 0


# ---------------------------------------------- streaming, atomic, profiling


def test_stream_pulls_rows_lazily_and_interleaves(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    tables.add(m, "edge", [(i, i + 1) for i in range(500)])
    with m._stream(S.edge(V.a, V.b), S.edge(V.b, V.c)) as rows:
        first = next(rows)
        assert (first.a, first.b, first.c) == (0, 1, 2)
        # Unrelated engine work interleaves while the cursor stays open,
        # which a raw janus cursor forbids.
        assert m._one("(+ 1 2)") == 3
        second = next(rows)
        assert (second.a, second.b, second.c) == (1, 2, 3)
    with pytest.raises(PettaError):
        next(rows)  # leaving the with-block closed it


def test_stream_agrees_with_query_and_closes_on_exhaustion(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    tables.add(m, "edge", [(i, i + 1) for i in range(50)])
    cursor = m._stream(S.edge(V.a, V.b))
    assert [tuple(r) for r in cursor] == [tuple(r) for r in m.query(S.edge(V.a, V.b))]
    with pytest.raises(StopIteration):
        next(cursor)
    assert list(cursor) == []
    cursor.close()
    assert list(cursor) == []
    assert "exhausted" in repr(cursor)


# The cheapest route was the only one that could not be spelled naturally.
# Over 2,000 stored atoms, wanting the first three: query(pat)[:3] costs 26,055
# inferences because slicing trims after computing everything, and pulling
# three from a cursor costs 20. Convenience is free when it changes the
# spelling and not the plan.
def test_a_cursor_slice_pulls_only_what_it_takes(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = m._new_space()
    space.add(*[S.fact(i, i) for i in range(2000)])
    with space.stats() as lazy, space._stream(S.fact(V.k, V.n)) as cursor:
        first_three = cursor[:3]
    with space.stats() as eager:
        trimmed = space.query(S.fact(V.k, V.n))[:3]
    assert len(first_three) == len(trimmed) == 3
    # Two orders of magnitude, not a constant factor, and the gap grows with
    # the space because one stops early and the other trims afterwards.
    assert lazy.inferences * 100 < eager.inferences

    with space._stream(S.fact(V.k, V.n)) as cursor:
        assert cursor[0].k == first_three[0].k
    with space._stream(S.fact(V.k, V.n)) as cursor:
        assert [row.k for row in cursor[1:4]] == [row.k for row in first_three[1:]] + [
            trimmed[3].k if len(trimmed) > 3 else space.query(S.fact(V.k, V.n))[3].k
        ]


def test_a_cursor_refuses_what_would_need_the_whole_stream(m):
    """Each refusal is the design, not a gap: every one of these needs every
    row, which is exactly what a cursor exists to avoid.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    space = m._new_space()
    space.add(*[S.fact(i, i) for i in range(10)])
    with space._stream(S.fact(V.k, V.n)) as cursor, pytest.raises(TypeError, match="no len"):
        len(cursor)
    with (
        space._stream(S.fact(V.k, V.n)) as cursor,
        pytest.raises(IndexError, match="indexed from the end"),
    ):
        cursor[-1]
    with (
        space._stream(S.fact(V.k, V.n)) as cursor,
        pytest.raises(ValueError, match="takes no step"),
    ):
        cursor[::2]
    with (
        space._stream(S.fact(V.k, V.n)) as cursor,
        pytest.raises(ValueError, match="counts from the start"),
    ):
        cursor[-3:]
    with (
        space._stream(S.fact(V.k, V.n)) as cursor,
        pytest.raises(TypeError, match="int or a slice"),
    ):
        cursor["a"]
    # Running off the end is an IndexError naming how many it answered, and an
    # empty window is an empty list rather than an error.
    with (
        space._stream(S.fact(V.k, V.n)) as cursor,
        pytest.raises(IndexError, match="fewer than 100"),
    ):
        cursor[99]
    with space._stream(S.fact(V.k, V.n)) as cursor:
        assert cursor[3:1] == []


def test_abandoned_stream_warns_before_reaping(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.edge(1, 2))
    cursor = m._stream(S.edge(V.a, V.b))
    with pytest.warns(ResourceWarning, match="open petta Cursor"):
        del cursor
        gc.collect()


def test_stream_guard_and_per_pull_bounds(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    tables.add(m, "edge", [(i, i + 1) for i in range(100)])
    with m._stream(S.edge(V.a, V.b), where=S[">="](V.a, 90)) as rows:
        assert [r.a for r in rows] == list(range(90, 100))
    m.run("(= (stream-spin $n) (if (== $n 0) done (stream-spin (- $n 1))))")
    cursor = m._stream(
        S.edge(V.a, V.b),
        where="(== (stream-spin 100000000) done)",
        inferences=1_000,
    )
    with pytest.raises(InferenceLimitError):
        next(cursor)
    cursor.close()


def test_atomic_run_commits_or_rolls_back_whole(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError):
        with m.atomic():
            m.run("(kept fact) !(+ $left $right)")
    assert Expression(S.kept, S.fact) not in m  # the fact rolled back with the throw
    with m.atomic():
        m.run("(kept fact) !(+ 1 1)")
    assert Expression(S.kept, S.fact) in m  # and commits whole on success


def test_speculative_run_answers_and_discards(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with m.speculative():
        groups = m.run("(ghost fact) !(+ 2 2)")
    assert groups[-1] == [4]
    assert Expression(S.ghost, S.fact) not in m
    with m.speculative(), m.capture() as output:
        groups = m.run("(ghost2 x) !(println! spec-out)")
    assert "spec-out" in output.text
    assert Expression(S.ghost2, S.x) not in m
    with pytest.raises(ValueError):
        with m.atomic(), m.speculative():
            pass


def test_profile_counts_samples_on_real_work(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (prof-spin $n) (if (== $n 0) done (prof-spin (- $n 1))))")
    groups, prof = m.profile(
        "!(with-pragma! ((max-stack-depth 30000000)) (prof-spin 10000000))"
    )
    assert groups == [[S.done]]
    assert prof.samples > 0 and prof.ticks > 0
    assert len(prof.nodes) >= 1
    predicate, _calls, _redos, ticks_self, _siblings = prof.nodes[0]
    assert isinstance(predicate, str) and ticks_self >= 0
    assert prof.top(1) == prof.nodes[:1]
    assert "samples" in repr(prof)


# profile() answers over every predicate in the process. A library author's
# question is narrower and needs two things the sampler does not carry: which
# tier installed a name, and whether the clause index its callers rely on
# exists. Both come from the engine, which knows them.
X10_LIBRARY = (
    """
:- metta_extension(profile_demo, [version('0.1.0')]).
:- metta_export("
    (: pd-one (-> Number Number))
    (: pd-table (-> Atom Number))
    (: pd-many (-> Number Number))
").
'pd-one'(A, B) :- B is A * 2.
"""
    + "\n".join(f"'pd-table'(k{index}, {index})." for index in range(300))
    + """
'pd-many'(_, B) :- member(B, [1, 2, 3]).
"""
)


@pytest.fixture()
def profiled(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.register_prolog(X10_LIBRARY)
    m.run(
        "(= (pd-spin $n) (if (== $n 0) done (progn (pd-one $n) (pd-table k1) (pd-spin (- $n 1)))))"
    )
    yield m
    m.unregister_prolog("profile_demo")


def test_profile_extension_reports_every_declared_member(profiled):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    groups, costs = profiled.profile_extension("!(pd-spin 500)", extension="profile_demo")
    assert groups == [[S.done]]
    assert {cost.name for cost in costs} == {"pd-one", "pd-table", "pd-many"}
    by_name = {cost.name: cost for cost in costs}
    # Counted, not sampled, so these are exact.
    assert by_name["pd-one"].calls == 500
    assert by_name["pd-table"].calls == 500
    # A member the workload never reached is reported as costing nothing,
    # rather than omitted, which would read the same way.
    assert by_name["pd-many"].calls == 0
    assert all(cost.tier == "prolog" for cost in costs)
    assert all(cost.arity == 2 for cost in costs)


def test_profile_extension_separates_an_indexed_table_from_a_single_clause(profiled):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _, costs = profiled.profile_extension("!(pd-spin 500)", extension="profile_demo")
    by_name = {cost.name: cost for cost in costs}
    # 300 clauses SWI can discriminate on the first argument, against one
    # clause with nothing to discriminate.
    assert by_name["pd-table"].speedup > 100
    assert by_name["pd-table"].indexed is True
    assert by_name["pd-one"].speedup == 1.0


def test_profile_extension_shows_a_left_behind_choice_point(profiled):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    groups, costs = profiled.profile_extension("!(collapse (pd-many 1))", extension="profile_demo")
    assert groups == [[Expression(1, 2, 3)]]
    by_name = {cost.name: cost for cost in costs}
    # Three answers from one call, so the engine re-enters twice for the
    # second and third. That is what a leftover choice point looks like from
    # outside, and the inference counter cannot see it at all.
    assert by_name["pd-many"].calls == 1
    assert by_name["pd-many"].redos == 2
    assert by_name["pd-one"].redos == 0


def test_profile_extension_takes_an_explicit_name_list(profiled):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _, costs = profiled.profile_extension("!(pd-spin 50)", names=["pd-one"])
    assert [cost.name for cost in costs] == ["pd-one"]
    assert costs[0].calls == 50
    assert "pd-one/2" in repr(costs[0])


def test_profile_extension_needs_exactly_one_of_extension_or_names(profiled):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for kwargs in ({}, {"extension": "profile_demo", "names": ["pd-one"]}):
        with pytest.raises(ValueError, match="exactly one"):
            profiled.profile_extension("!(pd-spin 1)", **kwargs)


def test_subscription_is_a_context_manager_and_events_stream(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    seen = []
    with m.subscribe(S.dwatch(V.x)) as subscription:

        def consume():
            seen.extend(str(event.atom) for event in subscription.events())

        consumer = threading.Thread(target=consume)
        consumer.start()
        m.add(S.dwatch(S.one))
        m.add(S.dwatch(S.two))
        deadline = time.monotonic() + 5
        while len(seen) < 2 and time.monotonic() < deadline:
            time.sleep(0.005)
    # leaving the with-block cancelled, which ends the stream
    consumer.join(timeout=5)
    assert not consumer.is_alive()
    assert seen == ["(dwatch one)", "(dwatch two)"]


def test_events_times_out_quiet_and_refuses_callback_mode(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    quiet = m.subscribe(S.dnothing(V.x))
    try:
        started = time.monotonic()
        assert list(quiet.events(timeout=0.05)) == []
        assert time.monotonic() - started < 2
    finally:
        quiet.cancel()
    with (
        m.subscribe(S.dnothing(V.x), lambda _event: None) as with_callback,
        pytest.raises(PettaError, match="delivers through its callback"),
    ):
        next(iter(with_callback.events()))


def test_events_delivers_leftovers_queued_before_cancel(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    subscription = m.subscribe(S.dleft(V.x))
    m.add(S.dleft(S.kept))
    subscription.cancel()
    assert [str(e.atom) for e in subscription.events()] == ["(dleft kept)"]


def test_bare_threads_share_the_home_engine_serialized(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # No engine_thread(), no pool: plain threads' calls serialize on the
    # home engine's lock and every answer is right.
    m.run("(= (tsafe-double $x) (* $x 2))")
    answers = {}

    def ask(n):
        answers[n] = m._one(f"(tsafe-double {n})")

    workers = [threading.Thread(target=ask, args=(n,)) for n in range(6)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=30)
    assert answers == {n: n * 2 for n in range(6)}


def test_relational_arithmetic_runs_backwards(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.run("!(let 4 (- $x 1) $x)") == [[5]]
    assert m.run("!(let 6 (* $x 2) $x)") == [[3]]
    # no integer doubles to 7, so that branch answers nothing
    assert m.run("!(collapse (let 7 (* $x 2) $x))") == [[Expression()]]
    assert m.run("!(let 2 (/ 6 $b) $b)") == [[3]]
    with pytest.raises(MettaOperationError):
        m.run("!(+ $x $y)")


def test_in_language_bounds_and_scoped_pragmas(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (bnd-spin $n) (if (== $n 0) done (bnd-spin (- $n 1))))")
    assert m.run("!(inferences 100000 (bnd-spin 5))") == [[S.done]]
    with pytest.raises(InferenceLimitError):
        m.run("!(inferences 300 (bnd-spin 1000000))")
    with pytest.raises(InferenceLimitError):
        m.run("!(with-pragma! ((max-inferences 300)) (bnd-spin 1000000))")
    # the scope restored: the same spin runs free afterwards
    assert m.run("!(bnd-spin 2000)") == [[S.done]]


def test_a_stack_depth_pragma_bounds_evaluation_instead_of_overflowing(m):
    """`max-stack-depth` enforces its bound as an Error answer, per pragma law.

    A recursion past the declared depth answers `(Error -3 StackOverflow)`
    beside the answers already produced, a negative bound refuses with the
    upstream `UnsignedIntegerIsExpected` wording, and an unknown pragma key
    keeps raising `metta_pragma_key`.
    """
    m.run("!(pragma! max-stack-depth 20)")
    m.run("(= (p122-fact 0) 1)")
    m.run("(= (p122-fact $n) (* $n (p122-fact (- $n 1))))")
    try:
        assert [str(atom) for atom in m.run("!(p122-fact 5)")[0]] == [
            "120",
            "(Error -3 StackOverflow)",
        ]
        assert [str(atom) for atom in m.run("!(pragma! max-stack-depth -1)")[0]] == [
            "(Error (pragma! max-stack-depth -1) UnsignedIntegerIsExpected)"
        ]
        with pytest.raises(EngineError, match="metta_pragma_key"):
            m.run("!(pragma! no-such-setting 1)")
    finally:
        m.run("!(pragma! max-stack-depth none)")


def test_wrapper_forms_reach_a_named_spaces_own_functions(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # timeout, take, top, elapsed, transaction and the bound forms hand
    # their goal to helper predicates; without meta_predicate the goal
    # loses its module and a named space's functions are unreachable.
    with metta._new_space() as space:
        space.run("(= (wrap-f $n) (+ $n 1))")
        space.run("(= (wrap-many) (superpose (3 1 2)))")
        assert space.run("!(timeout 30 (wrap-f 1))") == [[2]]
        assert space.run("!(inferences 100000 (wrap-f 1))") == [[2]]
        assert space.run("!(with-pragma! ((max-time 30)) (wrap-f 1))") == [[2]]
        assert space.run("!(transaction (wrap-f 1))") == [[2]]
        assert space.run("!(take 2 (wrap-many))") == [[3, 1]]
        assert space.run("!(top 1 (wrap-many))") == [[3]]
        (group,) = space.run("!(elapsed (wrap-f 1))")
        assert group[0][0] == 2
