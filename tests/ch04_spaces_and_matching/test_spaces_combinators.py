"""Purpose: the space combinators: union, readonly, mapped, overlay, each an
ordinary provider on the public seam, certified by the conformance kit where
it can write and probed at the seam's law where it cannot.
Guarantees:
  - overlay and mapped pass the full conformance kit, round-trip law
    included [tested test_overlay_passes_the_conformance_kit,
    test_mapped_passes_the_conformance_kit]
  - an object view joins stored atoms to live fields and writes with setattr
    [tested: test_a_query_joins_stored_atoms_with_live_object_fields;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - view presents dictionaries and zero-based sequences through kv and sets
    as member spaces, with every read reflecting the current Python value
    [tested: test_view_is_a_live_queryable_space; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - every combinator member consults the provider's capability and concrete
    request before a read or write reaches it
    [tested: test_combinators_forward_every_provider_policy_request;
    commit=f10b3766f72a01bc7c023eb27ff6732dfde7ccf6]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from dataclasses import dataclass

import pytest

from metta import MettaError, S, V, ground, parse, spaces, testing, view


@pytest.fixture()
def pair(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space(), metta._new_space()


def test_view_is_a_live_queryable_space():  # noqa: D103  -- pytest discovers this contract probe by name
    config = {"port": 80, "backup": 80}
    config_space = view(config)
    assert config_space[(S.kv, S.port, V.value)].value == [80]
    assert config_space[(S.kv, V.key, 80)].key == [S.port, S.backup]
    config["port"] = 443
    assert config_space[(S.kv, S.port, V.value)].value == [443]

    values = [S.ready, S.waiting, S.ready]
    sequence_space = view(values)
    assert sequence_space[(S.kv, V.i, S.ready)].i == [0, 2]
    values.append(S.ready)
    assert sequence_space[(S.kv, V.i, S.ready)].i == [0, 2, 3]

    members = {S.red, S.blue}
    member_space = view(members)
    assert set(member_space.match(V.member).member) == members
    members.add(S.green)
    assert set(member_space.match(V.member).member) == members

    with pytest.raises(TypeError, match="dict, set, or non-string sequence"):
        view("not a sequence view")


def test_union_reads_every_member_and_engine_matches(metta, pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    kb, rules = pair
    kb.add(S.edge(S.a, S.b))
    rules.add(S.edge(S.b, S.c), S.node(S.z))
    name = "&cmb-union"
    metta._register_space(spaces.union(kb, rules), name)
    try:
        atoms = sorted(str(a) for a in metta._at(name).atoms())
        assert atoms == ["(edge a b)", "(edge b c)", "(node z)"]
        got = metta.run(f"!(collapse (match {name} (edge $a $b) ($a $b)))")
        assert str(got[0][0]) == "((a b) (b c))"
        # Duplicates across members answer twice: a union of multisets.
        rules.add(S.edge(S.a, S.b))
        assert [str(a) for a in metta._at(name).atoms()].count("(edge a b)") == 2
    finally:
        metta._unregister_space(name)


def test_union_refuses_writes_through_the_engine(metta, pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    kb, rules = pair
    name = "&cmb-union-ro"
    metta._register_space(spaces.union(kb, rules), name)
    try:
        with pytest.raises(MettaError) as failure:
            metta._at(name).add(S.nope(1))
        assert failure.value.capability == "add"
        assert len(kb) == 0 and len(rules) == 0
    finally:
        metta._unregister_space(name)
    with pytest.raises(MettaError, match="at least one"):
        spaces.union()
    with pytest.raises(MettaError, match="carries no engine"):
        spaces.union("&by-name")


def test_readonly_strips_every_write(metta, pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    kb, _ = pair
    kb.add(S.fact(1))
    name = "&cmb-ro"
    metta._register_space(spaces.readonly(kb), name)
    try:
        assert [str(a) for a in metta._at(name).atoms()] == ["(fact 1)"]
        for source in (f"!(add-atom {name} (w 1))", f"!(remove-atom {name} (fact 1))"):
            with pytest.raises(MettaError):
                metta.run(source)
        assert len(kb) == 1  # nothing reached the inner space
    finally:
        metta._unregister_space(name)


def test_mapped_presents_and_writes_through_the_declaration(metta, pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    inner, _ = pair
    inner.add(parse("(triple a linked-to b)"), parse("(other junk here)"))
    view = spaces.mapped(inner, "(bridge (edge $a $b) (triple $a linked-to $b))")
    name = "&cmb-view"
    metta._register_space(view, name)
    try:
        vs = metta._at(name)
        # Atoms the declaration does not map are invisible here.
        assert [str(a) for a in vs.atoms()] == ["(edge a b)"]
        assert str(metta.run(f"!(collapse (match {name} (edge a $x) $x))")[0][0]) == "(b)"
        vs.add(S.edge(S.c, S.d))
        assert parse("(triple c linked-to d)") in inner
        assert vs.remove(S.edge(S.a, V.y)) is True
        assert parse("(triple a linked-to b)") not in inner
        assert parse("(other junk here)") in inner  # untouched underneath
        with pytest.raises(MettaError, match="shape"):
            vs.add(S.wrong(1))
    finally:
        metta._unregister_space(name)


def test_mapped_repeated_variable_pattern_stays_sound(metta, pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The private `_joined` walk refuses (loop $x $x) against a shape whose
    # positions the pattern's repetition constrains; soundness demands the
    # candidates still answer, and the engine re-unifies them.
    inner, _ = pair
    inner.add(parse("(pairof a a)"), parse("(pairof a b)"))
    view = spaces.mapped(inner, "(bridge (loop $x $y) (pairof $x $y))")
    name = "&cmb-fold"
    metta._register_space(view, name)
    try:
        got = metta.run(f"!(collapse (match {name} (loop $q $q) $q))")
        assert str(got[0][0]) == "(a)"
    finally:
        metta._unregister_space(name)


def test_mapped_refuses_a_malformed_declaration(pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    inner, _ = pair
    with pytest.raises(MettaError, match="bridge"):
        spaces.mapped(inner, "(not-a-bridge (a) (b))")


def test_overlay_routes_writes_to_front(metta, pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    front, back = pair
    back.add(S.base(1))
    name = "&cmb-overlay"
    metta._register_space(spaces.overlay(front, back), name)
    try:
        ov = metta._at(name)
        ov.add(S.hot(2))
        assert sorted(str(a) for a in ov.atoms()) == ["(base 1)", "(hot 2)"]
        assert [str(a) for a in front.atoms()] == ["(hot 2)"]
        # ChainMap's rule: a removal touches the front only, so an atom
        # the back holds keeps answering.
        assert ov.remove(S.base(1)) is False
        assert parse("(base 1)") in back
        ov.clear()
        assert len(front) == 0 and len(back) == 1
    finally:
        metta._unregister_space(name)


def test_overlay_passes_the_conformance_kit(metta, pair):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    front, back = pair
    report = testing.check_space_provider(
        spaces.overlay(front, back),
        atoms_to_store=[
            parse("(cmb-fact a b)"),
            parse("(cmb-fact a c)"),
            parse("(cmb-fact (f $x) $x)"),
        ],
    )
    assert any("over-approximation holds" in line for line in report)
    assert "round-trip: 3 stored atoms recovered intact" in report


def test_mapped_passes_the_conformance_kit(metta, pair):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    inner, _ = pair
    view = spaces.mapped(
        inner, "(bridge (cmb-fact $a $b) (stored-as $a $b))"
    )
    report = testing.check_space_provider(
        view,
        atoms_to_store=[
            parse("(cmb-fact a b)"),
            parse("(cmb-fact a c)"),
            parse("(cmb-fact (f $x) $x)"),
        ],
    )
    assert any("over-approximation holds" in line for line in report)
    assert "round-trip: 3 stored atoms recovered intact" in report


def test_combinators_compose(metta, pair):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # readonly(union(...)) and mapped over an overlay: combinators take
    # combinators, because everything is the one seam.
    kb, extra = pair
    kb.add(S.edge(S.a, S.b))
    extra.add(S.edge(S.b, S.c))
    stack = spaces.readonly(spaces.union(kb, extra))
    name = "&cmb-stack"
    metta._register_space(stack, name)
    try:
        got = metta.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
        assert str(got[0][0]) == "((a b) (b c))"
        with pytest.raises(MettaError):
            metta._at(name).add(S.w(1))
    finally:
        metta._unregister_space(name)


def test_a_query_joins_stored_atoms_with_live_object_fields(metta):
    """An object view unioned with a stored space joins atoms to live fields and writes with setattr."""
    @dataclass
    class Manager:
        age: int

    manager = Manager(31)
    field = S["py-field"]
    with metta._new_space() as stored:
        stored.add(S.manager(S.ada, ground(manager)), S.band(31, S.senior))
        view = spaces.object_view(manager)
        view_name = "&cmb-object-view"
        join_name = "&cmb-object-join"
        metta._register_space(view, view_name)
        metta._register_space(spaces.union(stored, view), join_name)
        try:
            joined = metta._at(join_name)
            rows = joined.match(
                S.manager(V.who, V.manager),
                field(V.manager, S.age, V.age),
                S.band(V.age, V.band),
            )
            assert rows.who == [S.ada]
            assert rows.age == [31]
            assert rows.band == [S.senior]

            manager.age = 32
            stored.add(S.band(32, S.current))
            assert joined.match(
                S.manager(S.ada, V.manager),
                field(V.manager, S.age, V.age),
                S.band(V.age, V.band),
            ).band == [S.current]

            metta._at(view_name).add(field(ground(manager), S.age, 33))
            assert manager.age == 33
            assert joined.match(
                S.manager(S.ada, V.manager),
                field(V.manager, S.age, V.age),
            ).age == [33]
        finally:
            metta._unregister_space(join_name)
            metta._unregister_space(view_name)


def test_diff_answers_the_multiset_difference(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as a, metta._new_space() as b:
        a.add(parse("(dfact one)"), parse("(dfact one)"), parse("(dfact two)"))
        a.run("(= (ddouble $x) (* $x 2))")
        b.add(parse("(dfact one)"), parse("(dfact three)"))
        only_a, only_b = spaces.diff(a, b)
        shown = [str(x) for x in only_a]
        # multiset: the SECOND copy of (dfact one) is a's alone, and the
        # equation is an atom like any other
        assert len(only_a) == 3
        assert shown.count("(dfact one)") == 1
        assert "(dfact two)" in shown
        assert any(x.startswith("(= (ddouble") for x in shown)
        assert [str(x) for x in only_b] == ["(dfact three)"]


def test_diff_counts_alpha_equivalent_atoms_as_the_same(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as a, metta._new_space() as b:
        a.add(parse("(dg $x)"))
        b.add(parse("(dg $y)"))
        assert spaces.diff(a, b) == ([], [])


def test_diff_takes_a_provider_side(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Bag:
        def atoms(self):
            yield parse("(dprov here)")

    with metta._new_space() as a:
        a.add(parse("(dprov here)"), parse("(dprov extra)"))
        only_a, only_b = spaces.diff(a, Bag())
        assert [str(x) for x in only_a] == ["(dprov extra)"]
        assert only_b == []


def test_a_member_without_the_method_refuses_with_the_framework_sentence(metta):
    """A combinator member speaks the capability refusal, not AttributeError.

    overlay(ReadOnly(), back).clear() died with AttributeError before, which
    names Python's lookup rather than the capability model; the engine's own
    path through a provider answers with the sentence that distinguishes
    "does not implement" from "declines this request", and the combinator
    seam speaks it now [measured 2026-09-01].
    """
    from metta.foreign import SpaceProvider

    class ReadOnly(SpaceProvider):
        def atoms(self):
            yield S.frozen(1)

    with metta._new_space() as back:
        combined = spaces.overlay(ReadOnly(), back)
        for operation, call in (
            ("clear", combined.clear),
            ("remove", lambda: combined.remove(S.frozen(1))),
            ("add", lambda: combined.add(S.fresh(1))),
        ):
            with pytest.raises(MettaError, match=f"does not implement {operation}"):
                call()
        # Reading still works: the provider implements exactly that.
        assert [str(a) for a in combined.atoms()] == ["(frozen 1)"]


def test_combinators_forward_every_provider_policy_request():
    """A composed provider keeps the same request-level boundary as the seam."""
    from metta.foreign import SpaceProvider

    class QueriesNotDumps(SpaceProvider):
        def __init__(self):
            self.requests = []
            self.enumerations = 0

        def atoms(self):
            self.enumerations += 1
            return iter([S.allowed(1)])

        def should_run(self, capability, /, **request):
            if capability == "enumerate":
                self.requests.append(request)
                return request.get("pattern") is not None
            return True

    queryable = QueriesNotDumps()
    query_view = spaces.union(queryable)
    with pytest.raises(MettaError, match="declines this enumerate request"):
        list(query_view.atoms())
    assert list(query_view.match(S.allowed(1))) == [S.allowed(1)]
    assert queryable.requests == [{}, {"pattern": S.allowed(1)}]
    assert queryable.enumerations == 1

    class Selective(SpaceProvider):
        def __init__(self):
            self.stored = [S.allowed(1)]
            self.reached = []

        def atoms(self):
            self.reached.append(("atoms", None))
            return iter(self.stored)

        def match(self, pattern):
            self.reached.append(("match", pattern))
            return iter(self.stored)

        def add(self, atom):
            self.reached.append(("add", atom))
            self.stored.append(atom)

        def remove(self, atom):
            self.reached.append(("remove", atom))
            return False

        def clear(self):
            self.reached.append(("clear", None))
            self.stored.clear()

        def should_run(self, capability, /, **request):
            if capability == "enumerate":
                return False
            if capability == "match":
                return request.get("pattern") != S.denied(2)
            if capability in ("add", "remove"):
                return request.get("atom") != S.denied(2)
            if capability == "clear":
                return False
            return True

    provider = Selective()
    combined = spaces.overlay(provider, spaces.union(provider))

    with pytest.raises(MettaError, match="declines this enumerate request"):
        list(combined.atoms())
    with pytest.raises(MettaError, match="declines this match request"):
        list(combined.match(S.denied(2)))
    with pytest.raises(MettaError, match="declines this add request"):
        combined.add(S.denied(2))
    with pytest.raises(MettaError, match="declines this remove request"):
        combined.remove(S.denied(2))
    with pytest.raises(MettaError, match="declines this clear request"):
        combined.clear()

    assert provider.reached == []

    assert list(combined.match(S.allowed(1))) == [S.allowed(1), S.allowed(1)]
    combined.add(S.allowed(3))
    combined.remove(S.allowed(3))
    assert provider.reached == [
        ("match", S.allowed(1)),
        ("match", S.allowed(1)),
        ("add", S.allowed(3)),
        ("remove", S.allowed(3)),
    ]
