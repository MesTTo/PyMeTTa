"""Purpose: the MORK space through the python surface. &mork is
trueagi-io/MORK behind mork_ffi, hooked into the engine's own space
predicates, so adds, removes, queries, joins, subscriptions, count,
digest, and MM2 exec all run the ordinary metta surface with MORK as
the store. Writes queue inside MORK and every read flushes first, so
read-your-writes holds without an explicit flush. Skips whole when the
native library is not built.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from pathlib import Path

import pytest

from metta import S, V, ground, parse
from metta.errors import EngineError
from metta.foreign import SpaceProvider, register_provider

_MORKLIB = (
    Path(__file__).resolve().parents[4]
    / "extensions"
    / "mork"
    / "mork_ffi"
    / "target"
    / "release"
    / "libmork_ffi.so"
)
pytestmark = pytest.mark.skipif(
    not _MORKLIB.is_file(),
    reason="mork_ffi is not built; run sh build.sh at the repo root",
)


@pytest.fixture()
def mork(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._at("&mork")
    yield space
    space.clear()


def test_writes_queue_and_reads_see_them(mork):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    mork.add(S.friend(S.sam, S.tim), S.friend(S.sam, S.joe))
    rows = mork.match(S.friend(S.sam, V.x))
    assert sorted(str(row.x) for row in rows) == ["joe", "tim"]
    assert len(mork) == 2


def test_joins_are_the_engines_joins_over_mork_conjuncts(mork):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    mork.add(S.friend(S.sam, S.tim), S.friend(S.sam, S.joe), S.age(S.tim, 30))
    join = mork.match(S.friend(S.sam, V.x), S.age(V.x, V.n))
    assert [(row.x, row.n) for row in join] == [(S.tim, 30)]


def test_remove_and_atoms_enumeration(mork):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    mork.add(S.mk(S.a), S.mk(S.b))
    assert mork.remove(S.mk(S.a)) is True
    assert [str(atom) for atom in mork.atoms()] == ["(mk b)"]
    assert mork.remove(S.mk(S.missing)) is False


def test_subscriptions_see_mork_writes(mork):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    seen = []
    sub = mork.subscribe(S.watched(V.x), lambda e: seen.append(e))
    try:
        mork.add(S.watched(S.one), S.other(S.two))
        assert len(seen) == 1
        assert seen[0].bindings["x"] == S.one
    finally:
        sub.cancel()


def test_digest_names_mork_content_too(mork, metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    mork.add(S.dgm(1), S.dgm(2))
    first = mork.digest()
    assert len(first) == 64
    with metta._new_space() as native:
        native.add(S.dgm(2), S.dgm(1))
        assert native.digest() == first


def test_mork_holds_rules_not_only_facts(mork):
    """MORK declares the rules capability, so an equation stored in it is a
    program the engine can run rather than an inert atom. The same space
    stays a data source while it does: the rule and the fact sit together,
    which is the point of a space in MeTTa rather than a nuance of one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    mork.add(parse("(= (mork-doubled $x) (* 2 $x))"), S.seed(21))
    assert mork.eval("(mork-doubled 21)") == [ground(42)]
    assert [row.n for row in mork.match(S.seed(V.n))] == [21]


def test_mork_answers_the_whole_rule_set(mork):
    """Two equations for one function are two answers, the way they are in a
    native space. The bridge into MORK is one clause per function, so the
    nondeterminism has to come from the provider's match, not from clauses.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    mork.add(
        parse("(= (mork-colour) red)"),
        parse("(= (mork-colour) blue)"),
    )
    assert sorted(str(a) for a in mork.eval("(mork-colour)")) == ["blue", "red"]


def test_mork_answers_a_whole_conjunction_with_its_own_join(mork, metta):
    """A conjunction reaches MORK whole, so its worst-case-optimal join answers
    it instead of the engine splitting it one pattern at a time. The oracle is
    a native space holding the same atoms: whatever MORK claims, the engine's
    own split must answer too. A claim is the one place in the seam where a
    provider may not over-approximate, because there is no cheap re-check for a
    join, so this differential stands in for one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    atoms = [
        S.edge(S.a, S.b), S.edge(S.b, S.c), S.edge(S.a, S.c), S.edge(S.c, S.a),
        S.tag(S.b, S.one), S.tag(S.c, S.two),
    ]
    mork.add(*atoms)
    queries = [
        (S.edge(V.x, V.y), S.tag(V.y, V.t)),
        (S.edge(V.x, V.y), S.edge(V.y, V.z)),
        (S.edge(V.x, V.y), S.edge(V.y, V.z), S.edge(V.z, V.x)),
        (S.edge(V.x, V.y), S.tag(V.y, S.nothing)),
    ]
    with metta._new_space() as native:
        native.add(*atoms)
        for query in queries:
            claimed = sorted(str(row) for row in mork.match(*query))
            split = sorted(str(row) for row in native.match(*query))
            assert claimed == split, f"{query} diverged"


def test_a_named_mork_space_claims_its_own_joins(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._at("&mork:joins")
    try:
        space.add(S.friend(S.sam, S.tim), S.age(S.tim, 30))
        rows = space.match(S.friend(S.sam, V.x), S.age(V.x, V.n))
        assert [(row.x, row.n) for row in rows] == [(S.tim, 30)]
    finally:
        for atom in space.atoms():
            space.remove(atom)


def test_mm2_exec_transforms_inside_mork(mork, metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(import! &self (library lib_mm2))")
    mork.add(S.friend(S.sam, S.tim))
    metta.run(
        "!(~> (, (friend sam $x)) (O (- (friend sam $x)) (+ (enemy sam $x))))"
    )
    rows = mork.match(S.enemy(S.sam, V.x))
    assert [row.x for row in rows] == [S.tim]
    assert not mork.match(S.friend(S.sam, V.x))


def test_lib_mm2_requires_the_mork_seat_and_still_stores_and_reads(mork, metta):
    """The require door passes and the notation is unchanged.

    lib_mm2's first form is now a require of the mork seat, the named refusal
    for the half that may be missing. With the seat loaded, which this
    module's own skipif guarantees, it answers the unit and the five
    operators store and read exactly as before. The refusal side is
    tests/prolog/suites/seams/extensions.plt, where a seat's records can be
    staged to look like a tree that never ran build.sh.
    """
    metta.run("!(import! &self (library lib_mm2))")
    # The add operator is MeTTa's fullwidth plus, which is lib_mm2's own
    # spelling and not a lookalike for the arithmetic one.
    metta.run("!(＋ (owns sam cat))")  # noqa: RUF001
    assert [row.x for row in mork.match(S.owns(S.sam, V.x))] == [S.cat]


def test_a_python_provider_cannot_take_a_name_mork_owns(metta):
    """The D2 collision, in the flesh, on the two shipped providers.

    Every name beginning &mork is this backend's, so a Python provider
    registering one used to land in metta_py_foreign/1 beside MORK's own
    ownership test and the two resolved by clause order: an atom went to
    whichever store loaded first, silently. The engine holds the claim now,
    so the second one is refused naming both owners and the remedy.
    """
    class Empty(SpaceProvider):
        def atoms(self):
            return iter(())

    with pytest.raises(EngineError, match="mork already claims") as refusal:
        register_provider(metta.runtime, "&mork:taken", Empty())
    assert "python cannot claim space &mork:taken" in str(refusal.value)
    assert "metta_disclaim_space" in str(refusal.value)


@pytest.fixture()
def named_pair(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    alpha = metta._at("&mork:iso-alpha")
    beta = metta._at("&mork:iso-beta")
    yield alpha, beta
    for space in (alpha, beta):
        space.clear()


def test_named_mork_spaces_are_isolated(named_pair, mork):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    alpha, beta = named_pair
    alpha.add(S.only(S.alpha))
    beta.add(S.only(S.beta))
    assert [str(a) for a in alpha.atoms()] == ["(only alpha)"]
    assert [str(a) for a in beta.atoms()] == ["(only beta)"]
    assert not mork.match(S.only(V.x))  # the default space saw nothing


def test_bulk_add_lands_in_one_crossing(metta, named_pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    alpha, _ = named_pair
    stored = metta.runtime.once(
        "findall(_A, (between(1, 500, _I), _A = [bulked, _I]), _L),"
        " 'mork-add-atoms'('&mork:iso-alpha', _L, true),"
        " aggregate_all(count,"
        "   ('get-atoms'('&mork:iso-alpha', _P), _P = [bulked, _]), N)"
    )["N"]
    assert stored == 500
    assert len(alpha.match(S.bulked(V.i))) == 500


def test_hostile_strings_round_trip_or_refuse(metta):
    """Escaped writing keeps line-breaking strings whole through MORK's
    line protocol, and a NUL byte, which would die at the C boundary,
    refuses loudly instead of killing the process.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    space = metta._at("&mork:hostile")
    for text in ['a"b', "a\\b", "a\nb", "a\tb", "a\rb", "é字"]:
        atom = S.holds(ground(text))
        space.add(atom)
        stored = [a.children[1].value for a in space.atoms()]
        assert stored == [text]
        space.remove(atom)
    with pytest.raises(EngineError):
        space.add(S.holds(ground("a\x00b")))


@pytest.mark.parametrize("name", ['bad"quote', "bad(paren", "bad)paren", "bad name"])
def test_symbols_without_round_trip_text_refuse_at_every_mork_write(metta, name):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._at("&mork:unsafe-symbol")
    atom = S.holds(S[name])
    with pytest.raises(EngineError, match=r"symbol names.*MORK text boundary"):
        space.add(atom)
    with pytest.raises(EngineError, match=r"symbol names.*MORK text boundary"):
        space.remove(atom)
    with pytest.raises(EngineError, match=r"symbol names.*MORK text boundary"):
        list(space.match(S.holds(S[name])))


def test_mork_bulk_add_refuses_an_unsafe_symbol_before_any_write(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._at("&mork:unsafe-bulk")
    with pytest.raises(EngineError, match=r"symbol names.*MORK text boundary"):
        space.add(S.safe(S.one), S.unsafe(S["bad name"]))
    assert space.atoms() == []


try:
    from hypothesis import HealthCheck, given, settings
except ModuleNotFoundError:
    pass
else:
    from metta.testing import expressions

    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(expressions(max_leaves=6, ground=True))
    def test_generated_expressions_round_trip_through_mork(metta, atom):
        """MORK's own parser and printer agree with the engine's on
        whatever the strategy generates: what goes in comes back.
        """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
        space = metta._at("&mork:fuzz")
        try:
            space.add(atom)
            assert atom in list(space.atoms())
        finally:
            space.clear()


def test_clear_reclaims_named_mork_content(metta):
    """Clear is provider-owned reclamation, not an enumeration-only facade."""
    space = metta._at("&mork:clear-reclaims")
    space.add(S.kept(S.one), S.kept(S.two))
    space.clear()
    assert space.atoms() == []
    space.add(S.kept(S.new))
    assert [str(atom) for atom in space.atoms()] == ["(kept new)"]
    space.clear()


def test_a_recycled_mork_name_inherits_nothing(metta):
    """A dropped MORK life leaves neither provider data nor generated code."""
    name = "&mork:recycled-life"
    old = metta._at(name)
    old.add(parse("(= (past-life) inherited)"))
    assert old.eval("(past-life)") == [S.inherited]
    old.drop()

    recycled = metta._at(name)
    assert recycled.atoms() == []
    assert recycled.eval("(past-life)") == [parse("(past-life)")]
    recycled.drop()


@pytest.mark.parametrize("width", [62, 63, 100])
def test_join_width_uses_mork_only_within_its_representation(metta, width):
    """The width boundary preserves answers and never reaches MORK's abort."""
    space = metta._at(f"&mork:width-{width}")
    try:
        atoms = [S[f"r{i}"](S.one) for i in range(width)]
        patterns = [S[f"r{i}"](V.x) for i in range(width)]
        space.add(*atoms)
        rows = space.match(*patterns)
        assert len(rows) == 1
        assert rows.one().x == S.one
    finally:
        space.drop()


def test_mork_refuses_an_expression_beyond_its_arity_encoding(metta):
    """An arity-64 value raises an engine error instead of aborting Rust."""
    space = metta._at("&mork:too-wide-value")
    try:
        with pytest.raises(EngineError, match=r"at most 63 children"):
            space.add(S.wide(*[S.x for _ in range(63)]))
    finally:
        space.drop()
