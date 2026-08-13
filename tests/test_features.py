"""Purpose: the feature surface added by the review round, engine-backed:
standing queries, first-class custom matchers, Python types declared into
spaces with field accessors, host values named in source, persistence,
typed rows, and the fast Python soft-scorer held equal to the MeTTa one by
differential fuzz.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, expr
from petta.atoms import Expr, Gnd, Sym, Var

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


# ----------------------------------------------------------- subscriptions


def test_subscription_callback_fires_inside_the_write(m):
    seen = []
    sub = m.subscribe(S.order(V.id), lambda e: seen.append(e))
    try:
        m.add(S.order(1), S.other(9), S.order(2))
        assert [e.bindings["id"] for e in seen] == [1, 2]
        assert seen[0].action == "add" and seen[0].space == m.space_name
    finally:
        sub.cancel()
    m.add(S.order(3))
    assert len(seen) == 2  # cancelled means cancelled


def test_subscription_queue_mode_drains(m):
    sub = m.subscribe(S.msg(V.body), on="both")
    try:
        m.add(S.msg(S.hello))
        m.remove(S.msg(S.hello))
        events = sub.drain()
        assert [e.action for e in events] == ["add", "remove"]
        assert sub.drain() == []
    finally:
        sub.cancel()


def test_subscription_fires_for_engine_side_writes(m):
    """add-atom from RUNNING MeTTa reaches the standing query too: the
    write funnel is the engine's own."""
    seen = []
    sub = m.subscribe(S.log(V.x), lambda e: seen.append(e.bindings["x"]))
    try:
        m.run("!(add-atom (context-space) (log 42))")
        assert seen == [42]
    finally:
        sub.cancel()


# ---------------------------------------------------------------- matchers


def test_custom_matcher_scores_and_generates(m):
    from petta import matching

    lexicon = ["class", "clause", "close"]

    def score(query, candidate):
        common = len(set(str(query)) & set(matching.text_of(candidate)))
        return common / max(len(set(str(query))), 1)

    def generate(query):
        ranked = sorted(lexicon, key=lambda w: -score(query, w))
        return ((w, score(query, w)) for w in ranked)

    matching.matcher(m, "letters-like", score=score, generate=generate, threshold=0.5)
    (answers,) = m.run('!(collapse (letters-like "clase" $w))')
    assert len(answers[0]) >= 1
    scored = m.run('!(letters-like "clase" "class")')
    assert float(scored[0][0][0]) > 0.5


def test_fuzzy_matcher_is_difflib(m):
    from petta import matching

    matching.install_fuzzy(m, name="fz-match")
    (answer,) = m.run('!(fz-match "kitten" "sitting")')[0]
    import difflib

    expected = difflib.SequenceMatcher(None, "kitten", "sitting").ratio()
    assert float(answer[0]) == pytest.approx(expected)
    # Score-only matcher says so when asked to generate.
    from petta.errors import EngineError

    with pytest.raises(EngineError):
        m.run("!(fz-match cat $unbound)")


def test_embedding_store_is_a_semantic_matcher(m):
    numpy = pytest.importorskip("numpy")
    from petta.arrays import EmbeddingStore

    store = EmbeddingStore(m, name="sem", mirror=False)
    store.add(S.dog, numpy.array([1.0, 0.0]))
    store.add(S.cat, numpy.array([0.9, 0.4]))
    store.add(S.car, numpy.array([0.0, 1.0]))
    store.matcher(name="sem-match", threshold=0.0)
    # Generation, best first, then the measure algebra right on top.
    m.run("!(import! (context-space) (library lib_measure))")
    (best,) = m.run("!(ws-best (collapse (sem-match dog $k)))")[0]
    assert best == S.dog
    scored = m.run("!(sem-match dog cat)")
    assert 0.8 < float(scored[0][0][0]) <= 1.0


def test_faiss_and_argsort_rank_identically(m):
    numpy = pytest.importorskip("numpy")
    pytest.importorskip("faiss")
    from petta.arrays import EmbeddingStore

    plain = EmbeddingStore(m, name="rk-a", mirror=False, backend="argsort")
    accel = EmbeddingStore(m, name="rk-b", mirror=False, backend="faiss")
    rng = numpy.random.default_rng(7)
    for i in range(50):
        vector = rng.normal(size=8).astype(numpy.float32)
        plain.add(Sym(f"k{i}"), vector)
        accel.add(Sym(f"k{i}"), vector)
    query = rng.normal(size=8).astype(numpy.float32)
    slow = [(str(k), s) for k, s in plain.ranked(query, 10)]
    fast = [(str(k), s) for k, s in accel.ranked(query, 10)]
    assert [k for k, _ in slow] == [k for k, _ in fast]
    for (_, a), (_, b) in zip(slow, fast):
        assert a == pytest.approx(b, abs=1e-5)


# ------------------------------------------------------------ typed Python


def test_type_declares_class_with_accessors(m):
    import dataclasses

    from petta import convert

    @m.type
    @dataclasses.dataclass
    class Song:
        title: str
        year: int

    m.add(convert.project(Song("Hallelujah", 1984)).atom)
    assert m.run("!(match (context-space) (Song $t $y) $t)") == [["Hallelujah"]]
    assert m.run('!(Song-year (Song "Hallelujah" 1984))') == [[1984]]
    # And back into Python, typed rows in one call.
    rows = m.query(V.s)
    songs = [
        s
        for s in rows.build("s", Song)
        if isinstance(s, Song)
    ]
    assert songs == [Song("Hallelujah", 1984)]


def test_type_declares_enum_members(m):
    import enum

    @m.type
    class Mood(enum.Enum):
        Calm = 1
        Storm = 2

    assert expr(S[":"], S.Calm, S.Mood) in m


# ----------------------------------------------------- host values in source


def test_run_using_names_host_values(m):
    from petta.integrate import install_reflection_ops

    install_reflection_ops(m)

    class Graph:
        nodes = 3

    graph = Graph()
    (answer,) = m.run("!(py-attr graph nodes)", using={"graph": graph})[0]
    assert answer == 3


def test_run_using_carries_identity(m):
    thing = object()
    m.run("!(add-atom (context-space) (held it))", using={"it": thing})
    rows = m.query(S.held(V.x))
    assert rows[0].x.value is thing


# ------------------------------------------------------------- persistence


def test_save_and_load_round_trip(metta, tmp_path):
    with metta.fresh_space() as space:
        space.run("(= (greet $x) (hello $x)) (fact one) (fact two)")
        path = tmp_path / "kb.metta"
        count = space.save(str(path))
        assert count == 3
    with metta.fresh_space() as reborn:
        reborn.load(str(path))
        assert len(reborn.query(S.fact(V.x))) == 2
        assert reborn.run("!(greet world)") == [[expr(S.hello, S.world)]]


def test_save_refuses_live_objects(m):
    from petta import val

    m.add(S.holds(val(object())))
    with pytest.raises(ValueError):
        m.save("/dev/null")


# ------------------------------------------------- soft scorer differential

_soft_installed = False


def _soft_space(metta):
    global _soft_installed
    if not _soft_installed:
        metta.run(
            "!(import! &self (library lib_measure))\n"
            "!(import! &self (library lib_soft))"
        )
        metta.add(expr(S.similar, S.lynx, S.puma, 0.8))
        metta.add(expr(S.similar, S.heron, S.stork, 0.7))
        _soft_installed = True
    return metta


@st.composite
def terms(draw, depth: int = 0):
    if depth >= 2 or draw(st.booleans()):
        leaf = draw(st.sampled_from(("sym", "num", "var")))
        if leaf == "sym":
            return Sym(draw(st.sampled_from(("lynx", "puma", "heron", "stork", "finch"))))
        if leaf == "num":
            return Gnd(draw(st.integers(0, 3)))
        return Var(draw(st.sampled_from(("p", "q"))))
    size = draw(st.integers(1, 3))
    return Expr([draw(terms(depth + 1)) for _ in range(size)])


@settings(max_examples=50, deadline=None)
@given(pattern=terms(), atom=terms())
def test_python_soft_score_equals_metta_soft_score(metta, pattern, atom):
    """The fast Python scorer and the pure MeTTa equations answer the same
    degree for the same pair, similarity facts included."""
    import petta_soft as soft

    space = _soft_space(metta)
    # The MeTTa side binds pattern variables; ground the comparison by
    # scoring only patterns whose variables the engine can bind freshly.
    engine = space.eval(expr(S["soft-score"], pattern, atom))
    assert len(engine) == 1
    table = {("lynx", "puma"): 0.8, ("heron", "stork"): 0.7}
    assert float(engine[0].value) == pytest.approx(
        soft.score(pattern, atom, table)
    )


# ----------------------------------------------------------------- measure


def test_measure_helpers_round_trip(m):
    from petta import measure

    measure.install(m)
    weighted = measure.ws((0.25, S.a), (0.75, S.b))
    (best,) = m.eval(expr(S["ws-best"], weighted))
    assert best == S.b
    (normalized,) = m.eval(expr(S["ws-normalize"], measure.ws((2.0, S.x), (6.0, S.y))))
    assert measure.pairs(normalized) == [(0.25, S.x), (0.75, S.y)]


def test_rows_table_is_the_dataframe_shape(m):
    m.add(S.Age(S.Tom, 62), S.Age(S.Bob, 40))
    rows = m.query(S.Age(V.who, V.n))
    table = rows.table()
    assert table == {"who": ["Tom", "Bob"], "n": [62, 40]} or table == {
        "who": ["Bob", "Tom"],
        "n": [40, 62],
    }


def test_add_table_reads_any_tabular_source(m):
    added = m.add_table("edge", {"src": [S.a, S.b], "dst": [S.b, S.c]})
    assert added == 2
    assert len(m.query(S.edge(V.x, V.y))) == 2

    polars = pytest.importorskip("polars")
    frame = polars.DataFrame({"name": ["ada", "bob"], "age": [36, 41]})
    assert m.add_table("person", frame) == 2
    rows = m.query(S.person(V.name, V.age))
    assert {(r["name"], r.age) for r in rows} == {("ada", 36), ("bob", 41)}
    with pytest.raises(TypeError):
        m.add_table("bad", 7)


def test_add_table_refuses_ragged_columns(m):
    with pytest.raises(ValueError):
        m.add_table("edge", {"src": [S.a, S.b, S.c], "dst": [S.b]})
    assert m.query(S.edge(V.x, V.y)) == []


def test_value_answers_the_one_answer(m):
    from petta.errors import EngineError

    assert m.value("(+ 1 2)") == 3 and isinstance(m.value("(+ 1 2)"), int)
    m.run("(= (fact $n) (if (> $n 0) (* $n (fact (- $n 1))) 1))")
    assert m.value(S.fact(5)) == 120
    with pytest.raises(EngineError):
        m.value("(superpose (1 2))")     # two answers is not a value
    with pytest.raises(EngineError):
        m.run("(= (nothing) (empty))")
        m.value(S.nothing())             # no answer is not a value either


def test_rows_first_and_one(m):
    m.add(S.city(S.perth), S.city(S.sydney))
    assert m.query(S.town(V.x)).first() is None
    assert m.query(S.city(V.x)).first() is not None
    with pytest.raises(ValueError):
        m.query(S.city(V.x)).one()       # two rows
    m.remove(S.city(S.perth))
    assert str(m.query(S.city(V.x)).one().x) == "sydney"


def test_space_iterates_and_subtracts(m):
    m.add(S.a(1), S.b(2))
    assert {str(a.head) for a in m} == {"a", "b"}
    m -= S.a(1)
    assert [str(a.head) for a in m] == ["b"]


def test_atoms_destructure_with_match_statements(m):
    m.add(S.likes(S.cat, 9))
    (atom,) = m.query(V.a).column("a")
    match atom:
        case Expr([Sym("likes"), Sym(who), Gnd(count)]):
            assert who == "cat" and count == 9
        case _:
            pytest.fail("the class pattern did not destructure")
    # An expression is a Sequence, so the bare sequence pattern works too.
    match S.likes(S.dog):
        case [Sym("likes"), pet]:
            assert pet == S.dog
        case _:
            pytest.fail("the sequence pattern did not destructure")
    match Var("x"):
        case Var(name):
            assert name == "x"


# ----------------------------------------------- contexts: bridges, remotes


def test_bridge_rules_connect_spaces(metta):
    from petta import bridge

    src = metta.fresh_space()
    dst = metta.fresh_space()
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


def test_remote_spaces_serve_attach_and_join(metta, tmp_path):
    """The other engine is a PROCESS, as deployment means it: a subprocess
    serves one space, this engine attaches it, and one local match joins
    remote rows with local facts across the wire."""
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    from petta import remote
    from petta.errors import PettaError

    script = Path(__file__).parent / "data" / "remote_server.py"
    child = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
    )
    local = metta.fresh_space()
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
            "!(collapse (match (context-space) (vip $id)"
            " (match &hq (users $id $n) $n)))"
        )
        assert group == [expr("Ada")]
        # Writes cross too, and the remote engine answers them back.
        local.run('!(add-atom &hq (users 3 "Cy"))')
        assert local.run("!(match &hq (users 3 $n) $n)") == [["Cy"]]
        local.run('!(remove-atom &hq (users 3 "Cy"))')
        assert local.run("!(collapse (match &hq (users 3 $n) $n))") == [[expr()]]
        # A space outside the allowlist is refused with the remote's words.
        stray = remote.RemoteSpace(remote.connect(info["url"]), "&self")
        with pytest.raises(PettaError):
            list(stray.match(S.anything(V.x)))
        local.unregister_space("&hq")
    finally:
        child.terminate()
        child.wait(timeout=10)
        local.drop()
