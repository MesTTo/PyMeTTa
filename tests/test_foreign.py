"""Purpose: the parts of the Python space seam that are specific rather than
general: concrete answers a general property cannot state, the capability and
refusal MODEL, registration, and the bound's mechanics.

The engine's general expectations of any space moved to
petta.testing.SpaceComplianceSuite and are exercised in
test_compliance_suite.py against three providers, including this file's
ListSpace, and in test_compliance_duckdb.py against a SQL backend. They used
to be restated here per test against one provider, which meant the engine's
expectations lived in two places and only one of them was shipped to a
provider author.
Guarantees:
  - capabilities derive from implemented narrow protocols, and declining an
    operation reads differently from not having it
    [tested test_capabilities_follow_implemented_methods,
    test_declining_and_not_implementing_read_differently]
  - registration changes Python state only after the engine accepts the same
    change [tested test_provider_registration_is_transactional]
  - the caller's bound reaches a provider that claimed exact and no other
    [tested test_a_bound_is_withheld_from_a_provider_that_claimed_nothing]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from collections.abc import Iterator
from typing import Any, ClassVar

import pytest

import petta.foreign as foreign_module
from petta import (
    Atom,
    Expression,
    MeTTa,
    PettaError,
    S,
    V,
    Variable,
    parse,
    unify,
)
from petta.foreign import (
    Adder,
    Clearer,
    Enumerable,
    Matcher,
    Remover,
    SpaceProvider,
    register_provider,
    unregister_provider,
)


class ListSpace(SpaceProvider):
    """The simplest honest provider: a Python list of atoms.

    test_compliance_suite.py runs the shipped SpaceComplianceSuite against
    this, so the engine's general expectations of a space are checked here
    once rather than restated per test.
    """

    def __init__(self, atoms=()):  # noqa: D107  -- the test double construction contract is local to its containing scenario
        self.stored = list(atoms)

    def match(self, _pattern):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(self.stored)

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(self.stored)

    def add(self, atom):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.stored.append(atom)

    def remove(self, atom):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        # One occurrence: the seam's own "remove one", which a provider
        # copied from here would otherwise get wrong.
        for index, held in enumerate(self.stored):
            if held == atom:
                del self.stored[index]
                return True
        return False


@pytest.fixture()
def listspace(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = ListSpace([S.edge(S.a, S.b), S.edge(S.b, S.c), S.other(1)])
    name = f"&list{id(provider) % 10000}"
    metta._register_space(provider, name)
    yield name, provider, metta
    metta._unregister_space(name)


# What the SpaceComplianceSuite already checks, over three providers rather
# than this one, is not restated here: an atom the provider holds is matchable,
# an open pattern answers every atom of its shape, a bound position filters
# what the provider over-approximated, enumeration answers what it holds, and
# an undeclared write refuses. What stays is the concrete answer, which says
# more than the general property, and everything the suite deliberately leaves
# alone: registration, the refusal MODEL, and the bound's mechanics.


def test_match_answers_exactly_what_the_pattern_names(listspace):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, _provider, m = listspace
    r = m.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
    assert r == [[Expression(Expression(S.a, S.b), Expression(S.b, S.c))]]
    # The provider yields (other 1) too, and unification is the engine's.
    assert m.run(f"!(match {name} (edge a $y) $y)") == [[S.b]]


def test_conjunction_routes_through_the_provider(listspace):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, provider, m = listspace
    r = m.run(f"!(collapse (match {name} (, (edge $x $y) (edge $y $z)) ($x $z)))")
    assert r == [[Expression(Expression(S.a, S.c))]]


def test_python_query_api_over_foreign_space(listspace):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, provider, m = listspace
    rows = m._at(name).query(S.edge(V.x, V.y), S.edge(V.y, V.z))
    assert [(r.x, r.z) for r in rows] == [(S.a, S.c)]


def test_writes_reach_the_provider(listspace):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, provider, m = listspace
    m.run(f"!(add-atom {name} (edge c d))")
    assert S.edge(S.c, S.d) in provider.stored
    m.run(f"!(remove-atom {name} (other 1))")
    assert S.other(1) not in provider.stored


def test_mixed_native_and_foreign_join(listspace):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, provider, m = listspace
    native = m._new_space()
    native.add(S.blessed(S.a))
    r = native.run(
        f"!(collapse (match {name} (edge $x $y) "
        f"(match (context-space) (blessed $x) ($x reaches $y))))"
    )
    assert r == [[Expression(Expression(S.a, S.reaches, S.b))]]


def test_read_only_provider_errors_loudly(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class ReadOnly(SpaceProvider):
        def atoms(self):
            return iter([S.fact(1)])

    name = "&readonly1"
    metta._register_space(ReadOnly(), name)
    try:
        with pytest.raises(PettaError) as excinfo:
            metta.run(f"!(add-atom {name} (fact 2))")
        assert "does not implement add" in str(excinfo.value)
        assert excinfo.value.capability == "add"
    finally:
        metta._unregister_space(name)


def test_capabilities_follow_implemented_methods():
    """Five capabilities are read off the methods, and subscribe is not.

    subscribe is a promise about the SPACE, so a provider that implements
    every write method and declares no delivery does not get it: that
    inference is exactly the one that made a remote space claim events it
    could not deliver. Once the promise is made, the write protocols narrow
    which EDGE it covers, because a store with no remove never emits a
    removal and a watcher for one would wait forever.
    """
    class ReadOnly(SpaceProvider):
        def atoms(self) -> Iterator[Any]:
            return iter(())

    class AddOnly(SpaceProvider):
        def add(self, atom) -> None:
            pass

    class AnnouncingAddOnly(AddOnly):
        def delivers(self) -> tuple[str, str]:
            """Every write, once, in write order."""
            return ("per-write-exactly", "ordered")

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
    for on in ("add", "remove", "both"):
        assert not add_only.can_run("subscribe", on=on), f"undeclared on={on}"

    announcing = AnnouncingAddOnly()
    assert announcing.can_run("subscribe", on="add")
    assert not announcing.can_run("subscribe", on="remove")
    assert not announcing.can_run("subscribe", on="both")


def test_stale_static_capability_declaration_is_refused():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="stale static declaration"):

        class StaleProvider(SpaceProvider):
            capabilities: ClassVar = {"add": True}


def test_provider_can_decline_one_request(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
    metta._register_space(provider, name)
    try:
        metta._at(name).add(S.allowed(1))
        with pytest.raises(PettaError, match="declines this add request"):
            metta._at(name).add(S.denied(1))
        assert provider.stored == [S.allowed(1)]
    finally:
        metta._unregister_space(name)


# The worked SQL instance lives whole in examples/integration/duckdb_space.py,
# which verifies itself in the suite; here stays the provider protocol.


def test_provider_collision_is_refused(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Empty(SpaceProvider):
        def atoms(self):
            return iter(())

    first = Empty()
    metta._register_space(first, "&col")
    try:
        with pytest.raises(ValueError):
            metta._register_space(Empty(), "&col")
        # The same provider again is idempotent, not a collision.
        metta._register_space(first, "&col")
    finally:
        metta._unregister_space("&col")


def test_provider_registration_is_transactional():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Empty(SpaceProvider):
        def atoms(self):
            return iter(())

    class Runtime:
        fail = False

        def must(self, _goal, **_inputs):
            if self.fail:
                msg = "injected provider boundary failure"
                raise RuntimeError(msg)
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


# The capability model carried a boolean and no reason, so _require_provider
# had to guess the wording from the capability name and got it wrong: a
# provider that IMPLEMENTS add and declines it was told it "does not implement
# add", and the sentence saying what to do instead, which the provider had
# already written, ran nowhere.
def test_a_provider_states_its_own_refusal(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Curated(SpaceProvider):
        def atoms(self):
            return iter(())

        def add(self, _atom):
            msg = "declined before this runs"
            raise AssertionError(msg)

        def can_run(self, capability, /, **request):
            if capability == "add":
                return False
            return super().can_run(capability, **request)

        def refusal(self, capability, /, **_request):
            if capability == "add":
                return "this space is curated; write to it with the loader"
            return None

    name = "&curated-refusal-test"
    metta._register_space(Curated(), name)
    try:
        with pytest.raises(PettaError, match="curated; write to it with the loader"):
            metta._at(name).add(S.f(S.a))
    finally:
        metta._unregister_space(name)


# "does not implement" is wrong for a provider that implements and declines,
# and the model already draws that distinction: the base class's own can_run
# answers "is it there at all" independently of the subclass's policy.
def test_declining_and_not_implementing_read_differently(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Declines(SpaceProvider):
        def atoms(self):
            return iter(())

        def add(self, _atom):
            msg = "declined before this runs"
            raise AssertionError(msg)

        def can_run(self, capability, /, **request):
            return False if capability == "add" else super().can_run(capability, **request)

    class Absent(SpaceProvider):
        def atoms(self):
            return iter(())

    metta._register_space(Declines(), "&declines-add-test")
    metta._register_space(Absent(), "&absent-add-test")
    try:
        with pytest.raises(PettaError, match="declines this add request"):
            metta._at("&declines-add-test").add(S.f(S.a))
        with pytest.raises(PettaError, match="does not implement add"):
            metta._at("&absent-add-test").add(S.f(S.a))
    finally:
        metta._unregister_space("&declines-add-test")
        metta._unregister_space("&absent-add-test")


# The declared capability was enforced where the operation is NAMED and
# bypassed where it is USED: foreign_match checked only "match", then fell
# through to atoms() for an Enumerable provider, so a provider allowing match
# and declining enumerate had atoms() called anyway.
def test_a_declined_enumerate_is_not_reached_through_match(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class NoEnumerate(SpaceProvider):
        called = False

        def atoms(self):
            NoEnumerate.called = True
            return iter(())

        def can_run(self, capability, /, **request):
            if capability == "enumerate":
                return False
            return super().can_run(capability, **request)

    name = "&no-enumerate-test"
    metta._register_space(NoEnumerate(), name)
    try:
        with pytest.raises(PettaError, match="declines this enumerate request"):
            metta.run(f"!(match {name} (edge $a $b) $a)")
        assert not NoEnumerate.called
    finally:
        metta._unregister_space(name)


# A provider backing a space with a database or a service can bound its own
# query, but only if it is told the bound. Two things a reader might expect to
# be missing here are already in place and needed nothing: the bound parts of a
# pattern reach the provider, including bindings an enclosing join has made,
# and the engine stops pulling as soon as it has enough answers. What was
# absent is telling the BACKEND a count before it starts work.
class _Countable(SpaceProvider):
    """Records what it was asked for and how much it produced."""

    def __init__(self, atoms: int) -> None:
        self.atoms_held = atoms
        self.asked: list[int | None] = []
        self.produced = 0

    def _yield_up_to(self, stop: int):
        for index in range(stop):
            self.produced += 1
            yield S.fact(S[f"a{index}"], index)


class _Bounded(_Countable):
    """Its match is exact, so N candidates are N answers and it may truncate.

    The claim used to live in this docstring and nothing tested it, which is
    the trap the classification closes: the engine now hands the bound to a
    provider that DECLARED exact, and check_space_provider tests the claim
    against this provider's own output.
    """

    def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        self.asked.append(limit)
        yield from self._yield_up_to(
            self.atoms_held if limit is None else min(self.atoms_held, limit)
        )

    def pushdown(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        return "exact"


class _Unbounded(_Countable):
    """Written before the option existed; must be called exactly as it was."""

    def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        yield from self._yield_up_to(self.atoms_held)


@pytest.mark.parametrize("limit", [1, 3, 10])
def test_a_bound_reaches_a_provider_that_takes_one(metta, limit):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _Bounded(500)
    metta._register_space(provider, "&bounded-test")
    try:
        rows = MeTTa().space("&bounded-test").query(S.fact(V.k, V.v), limit=limit)
        assert len(rows) == limit
        assert provider.asked == [limit]
        # It stopped at the bound rather than at the engine's cut, which is
        # the whole point: the backend did not produce what nobody wanted.
        assert provider.produced == limit
    finally:
        metta._unregister_space("&bounded-test")


def test_a_provider_without_the_keyword_is_called_as_before(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _Unbounded(500)
    metta._register_space(provider, "&unbounded-test")
    try:
        rows = MeTTa().space("&unbounded-test").query(S.fact(V.k, V.v), limit=3)
        assert len(rows) == 3
        # One past the bound, which is what a lazy pull costs, and nothing
        # like the 500 it holds.
        assert provider.produced == 4
    finally:
        metta._unregister_space("&unbounded-test")


class _UnclaimedBounded(_Countable):
    """Takes a limit keyword and claims nothing. It must not be given one.

    This is the provider the classification exists to protect against: it
    would truncate at whatever it is told, and nothing about it says its
    candidates are its answers. Withholding the number is what stops it
    under-answering, which is the one thing the seam's contract forbids.
    """

    def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        self.asked.append(limit)
        yield from self._yield_up_to(
            self.atoms_held if limit is None else min(self.atoms_held, limit)
        )


def test_a_bound_is_withheld_from_a_provider_that_claimed_nothing(metta):
    """Same signature as _Bounded, no claim, so no number.

    The provider is called through the unbounded path exactly as it was
    before the option existed, and the engine's own bound still answers 3.
    """
    provider = _UnclaimedBounded(500)
    metta._register_space(provider, "&unclaimed-test")
    try:
        rows = MeTTa().space("&unclaimed-test").query(S.fact(V.k, V.v), limit=3)
        assert len(rows) == 3
        assert provider.asked == [None]
    finally:
        metta._unregister_space("&unclaimed-test")


def test_a_metta_take_pushes_its_bound_to_the_provider(metta):
    """`take` is the MeTTa-level bound, and it reaches the SAME seam
    m.query(limit=) reaches rather than a second one beside it.

    Until it existed the two halves were unjoined: BoundedMatcher.limit had
    the concept and only the Python query surface could set it, so a MeTTa
    program bounding its own answers enumerated the backend and discarded.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    provider = _Bounded(500)
    metta._register_space(provider, "&take-test")
    try:
        space = MeTTa().space("&take-test")
        answered = space.run(
            "!(collapse (take 3 (match &take-test (fact $k $v) (fact $k $v))))"
        )[-1]
        assert len(answered[0]) == 3
        assert provider.asked == [3]
        assert provider.produced == 3, (
            "the backend produced what nobody asked for; the bound did not "
            "reach it"
        )
    finally:
        metta._unregister_space("&take-test")


def test_a_take_over_a_join_keeps_its_bound_to_itself(metta):
    """Across a join the bound belongs to the JOINED rows.

    An outer match truncated at N loses the rows its later candidates would
    have joined to, so the pushdown is decided by shape and a conjunction does
    not get it. The answers are still bounded, by the engine, which is what
    makes the pushdown a pure optimisation on top of a correct bound.
    """
    provider = _Bounded(50)
    metta._register_space(provider, "&take-join")
    try:
        space = MeTTa().space("&take-join")
        answered = space.run(
            "!(collapse (take 2 (match &take-join "
            "(, (fact $k $v) (fact $k2 $v)) ($k $k2))))"
        )[-1]
        assert len(answered[0]) == 2
        assert provider.asked and set(provider.asked) == {None}, provider.asked
    finally:
        metta._unregister_space("&take-join")


def test_a_take_withholds_its_bound_from_a_provider_that_claimed_nothing(metta):
    """The exactness gate is upstream of `take` and stays upstream of it.

    A provider that takes a limit keyword and never claimed its candidates
    are its answers would truncate at whatever it is told, so it is not told.
    """
    provider = _UnclaimedBounded(500)
    metta._register_space(provider, "&take-unclaimed")
    try:
        space = MeTTa().space("&take-unclaimed")
        answered = space.run(
            "!(collapse (take 3 (match &take-unclaimed (fact $k $v) (fact $k $v))))"
        )[-1]
        assert len(answered[0]) == 3
        assert provider.asked == [None]
    finally:
        metta._unregister_space("&take-unclaimed")


def test_a_pushdown_class_that_is_neither_word_is_refused(metta):
    """A claim that is neither word is a mistake, not a value to fall back
    from: falling back would silently discard a real exact.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    class _Nonsense(_Countable):
        def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            yield from self._yield_up_to(self.atoms_held)

        def pushdown(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return "probably"

    provider = _Nonsense(5)
    metta._register_space(provider, "&nonsense-test")
    try:
        with pytest.raises(PettaError, match="answered 'probably'"):
            list(
                MeTTa()
                .space("&nonsense-test")
                .query(S.fact(V.k, V.v), limit=2)
            )
    finally:
        metta._unregister_space("&nonsense-test")


def test_a_python_providers_capabilities_reach_the_engine(metta):
    """The two halves of the seam had two capability models that never met.

    foreign.py derives the set from the narrow protocols a provider implements
    and enforces it well. The Prolog side reads seam:foreign_capability/2 and
    saw nothing at all, so foreign_provides/2 reported that every Python
    provider provides EVERYTHING: anything the engine decides from a
    declaration silently excluded exactly the providers most likely to be
    incomplete, and a sixth capability could never join the vocabulary.
    """

    class MatchOnly(SpaceProvider):
        def atoms(self):
            return iter([S.fact(1)])

    name = "&capability-projection-test"
    metta._register_space(MatchOnly(), name)
    try:
        declared = metta._rt.must(
            "findall(_C, seam:foreign_capability(S, _C), L)", S=name
        )["L"]
        assert sorted(str(c) for c in declared) == ["enumerate", "match"]
    finally:
        metta._unregister_space(name)
    # And they go with the provider.
    assert not metta._rt.must(
        "findall(_C, seam:foreign_capability(S, _C), L)", S=name
    )["L"]


def test_an_absent_capability_still_carries_the_providers_own_words(metta):
    """The projection made the ENGINE refuse first, which would have lost the
    message. The refusal is a seam now, so it is raised where the words are.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    class Curated(SpaceProvider):
        def atoms(self):
            return iter(())

        def refusal(self, capability, /, **_request):
            return "load this space with the importer" if capability == "add" else None

    name = "&refusal-seam-test"
    metta._register_space(Curated(), name)
    try:
        with pytest.raises(PettaError, match="load this space with the importer"):
            metta._at(name).add(S.f(S.a))
    finally:
        metta._unregister_space(name)


def test_a_prolog_only_provider_answers_a_bounded_query(metta, tmp_path):
    """One match hook, so a Prolog provider is reached whatever Python is doing.

    There used to be a /2 beside seam:foreign_match/3, chosen between with
    `clause(seam:foreign_match(_,_,_), _)`, which asks whether ANY provider
    anywhere declared the bounded form. The Python shim declares it
    unconditionally, so with Python in the process that guard was true for
    every space: a Prolog-only provider writing /2 had /3 called instead, the
    shim's clause failed its own ownership check, and the whole match answered
    nothing. Reproduced as `unbounded: 3, bounded: 0`.
    """
    source = tmp_path / "prolog_only_space.pl"
    source.write_text(
        ":- multifile seam:foreign_space/1.\n"
        ":- multifile seam:foreign_match/3.\n"
        ":- multifile seam:foreign_pushdown/3.\n"
        "seam:foreign_space('&prolog-only-test').\n"
        "seam:foreign_match('&prolog-only-test', P, _) :-\n"
        "    member(P, [[fact, 1], [fact, 2], [fact, 3]]).\n"
        "seam:foreign_pushdown('&prolog-only-test', _, exact).\n"
    )
    metta._rt.consult(str(source))
    space = metta._at("&prolog-only-test")
    assert len(space.query(S.fact(V.n))) == 3
    assert len(space.query(S.fact(V.n), limit=2)) == 2


def test_a_bound_is_not_pushed_past_a_join(metta):
    """Across a join the bound belongs to the joined rows. An outer match
    truncated at N would lose the rows its later candidates would join to,
    which is under-answering, the one thing the contract forbids.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    provider = _Bounded(20)
    metta._register_space(provider, "&join-bound-test")
    try:
        rows = MeTTa().space("&join-bound-test").query(
            S.fact(V.k, V.v), S.fact(V.k, V.w), limit=2
        )
        assert len(rows) == 2
        assert provider.asked and all(asked is None for asked in provider.asked)
    finally:
        metta._unregister_space("&join-bound-test")


def test_an_unbounded_query_asks_for_nothing_in_particular(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _Bounded(7)
    metta._register_space(provider, "&nolimit-test")
    try:
        rows = MeTTa().space("&nolimit-test").query(S.fact(V.k, V.v))
        assert len(rows) == 7
        assert provider.asked == [None]
    finally:
        metta._unregister_space("&nolimit-test")


def test_a_provider_ignoring_the_bound_is_still_bounded_by_the_engine(metta):
    """Honouring the bound is the provider's decision, so the engine may not
    depend on it. This one is told 2 and answers everything anyway.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    class Defiant(_Countable):
        def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            self.asked.append(limit)
            yield from self._yield_up_to(self.atoms_held)

        def pushdown(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return "exact"

    provider = Defiant(50)
    metta._register_space(provider, "&defiant-test")
    try:
        rows = MeTTa().space("&defiant-test").query(S.fact(V.k, V.v), limit=2)
        assert len(rows) == 2
        assert provider.asked == [2]
    finally:
        metta._unregister_space("&defiant-test")


class JoiningSpace(SpaceProvider):
    """A provider that answers a whole conjunction itself.

    The naive nested loop is the point: what a claim buys is not this
    provider's strategy but that the engine hands over the whole conjunction,
    so a backend with a real join can use it. MORK's worst-case-optimal join
    goes through the same seam and is exercised in test_mork_space.py.
    """

    def __init__(self) -> None:  # noqa: D107  -- the test double construction contract is local to its containing scenario
        self.rows: list[Atom] = []
        self.claims = 0

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(self.rows)

    def add(self, atom: Atom) -> None:  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.rows.append(atom)

    def plan(self, patterns):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.claims += 1
        found: list[list[Atom]] = []

        def solve(index: int, bindings: dict, chosen: list[Atom]) -> None:
            if index == len(patterns):
                found.append(chosen)
                return
            for stored in self.rows:
                more = unify(_substitute(patterns[index], bindings), stored)
                if more is not None:
                    solve(index + 1, {**bindings, **more}, [*chosen, stored])

        solve(0, {}, [])
        return list(patterns), [], iter(found)


def _substitute(atom: Atom, bindings: dict) -> Atom:
    if isinstance(atom, Variable):
        return bindings.get(atom.name, atom)
    if isinstance(atom, Expression):
        return Expression([_substitute(child, bindings) for child in atom.children])
    return atom


class DecliningPlanner(JoiningSpace):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    def plan(self, patterns):  # noqa: ARG002, D102  -- the test double preserves the protocol method signature its caller exercises; the test double method is documented by its containing scenario and protocol
        self.claims += 1


_JOIN_ATOMS = [
    S.edge(S.a, S.b),
    S.edge(S.b, S.c),
    S.tag(S.b, S.one),
    S.tag(S.c, S.two),
]


def _both_ways(metta, provider, name, *query):
    register_provider(metta.runtime, name, provider)
    try:
        space = metta._at(name)
        space.add(*_JOIN_ATOMS)
        claimed = sorted(str(row) for row in space.query(*query))
        with metta._new_space() as native:
            native.add(*_JOIN_ATOMS)
            split = sorted(str(row) for row in native.query(*query))
        return claimed, split
    finally:
        unregister_provider(metta.runtime, name)


def test_a_claimed_join_answers_what_the_engines_split_answers(metta):
    """A conjunction reaches the provider whole. The oracle is the engine's own
    split over a native space holding the same atoms, because a claim is the one
    place in this seam where a provider may not over-approximate: there is no
    cheap re-check for a join, so the differential stands in for one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    provider = JoiningSpace()
    claimed, split = _both_ways(
        metta, provider, "&py_join", S.edge(V.x, V.y), S.tag(V.y, V.t)
    )
    assert claimed == split
    assert provider.claims == 1


def test_declining_a_conjunction_falls_back_to_the_split(metta):
    """Returning None is what a provider without a join does, and it must leave
    behaviour exactly as it was: asked, declined, and answered correctly.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    provider = DecliningPlanner()
    claimed, split = _both_ways(
        metta, provider, "&py_nojoin", S.edge(V.x, V.y), S.tag(V.y, V.t)
    )
    assert claimed == split
    assert provider.claims == 1


def test_plan_is_a_capability_derived_from_the_protocol():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert JoiningSpace().can_run("plan") is True
    assert ListSpace().can_run("plan") is False


class _PlannedPairs(SpaceProvider):
    """Claims any two-pattern conjunction whole, declines everything else."""

    def atoms(self) -> Iterator[Atom]:
        yield from ()

    def match(self, pattern: Atom, *, limit: int | None = None) -> Iterator[Atom]:  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        return iter(())

    def pushdown(self, pattern: Atom) -> str:  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        return "inexact"

    def plan(self, patterns: list[Atom]):
        if len(patterns) == 2:
            return list(patterns), [], iter(())
        return None


def test_explain_reflects_the_plan(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Stored space: the one true line, and the guard renders.
    prepared = metta.prepare(
        parse("(xedge $a $b)"), parse("(xedge $b $c)"), where=parse("(> 2 1)")
    )
    stored = prepared.explain()
    assert "query over &self: (xedge $a $b), (xedge $b $c)" in stored
    assert "stored atoms: engine unification" in stored
    assert "guard (> 2 1): runs in the engine" in stored

    # Foreign space: per-pattern class with its origin, the conjunction
    # claim, and the bound rule, from the seam's own decisions.
    metta._register_space(_PlannedPairs(), "&xplan")
    sp = metta._at("&xplan")
    try:
        pair = sp.prepare(parse("(pe $a $b)"), parse("(pe $b $c)")).explain()
        assert "(pe $a $b)" in pair and "inexact" in pair
        assert "the provider's own pushdown method" in pair
        assert "conjunction: the provider claimed (pe $a $b), (pe $b $c)" in pair
        assert "the engine joins nothing further" in pair
        triple = sp.prepare(
            parse("(pe $a $b)"), parse("(pe $b $c)"), parse("(pe $c $d)")
        ).explain()
        assert "no provider claim; the engine joins left to right" in triple

        # A declared (handles ...) entry outranks the provider's method,
        # exact brings the bound line, and Refuse reports as a refusal.
        sp._at("&xplan").handles("(pe $f $t)", "Exact", det="nondet")
        sp._at("&xplan").handles("(xsecret $x)", "Refuse")
        declared = sp.prepare(parse("(pe $a $b)")).explain()
        assert "exact" in declared
        assert "declared: (handles" in declared and "Exact nondet" in declared
        assert "a bound reaches the provider only where the class is exact" in declared
        refused = sp.prepare(parse("(xsecret $x)")).explain()
        assert "REFUSED: the declared entry" in refused
        assert "answers Refuse" in refused
    finally:
        metta._unregister_space("&xplan")


def test_a_stream_explains_without_pulling_a_row(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.add(parse("(sedge only)"))
    with metta._stream(parse("(sedge $x)")) as cursor:
        text = cursor.explain()
        assert "query over &self: (sedge $x)" in text
        assert "stored atoms: engine unification" in text
        # explaining consumed nothing: the row is still there to pull
        assert [str(row[0]) for row in cursor] == ["only"]


def test_an_eager_foreign_match_pulls_each_candidate_once(metta):
    """The eager collapse door costs one provider yield per candidate.

    Filed from a wire measurement of 20,000 yields for 10,000 stored atoms
    through !(collapse (match ...)); re-measured 2026-08-20 on the same
    counter shape and the doubling no longer reproduces on either the
    enumerate or the match capability, so this pins the once-per-candidate
    cost against regression on both routes.
    """

    class CountingEnumerate(SpaceProvider):
        def __init__(self):
            self.yields = 0

        def atoms(self):
            for i in range(2000):
                self.yields += 1
                yield Expression(S.p, i)

    class CountingMatch(CountingEnumerate):
        def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            for i in range(2000):
                self.yields += 1
                yield Expression(S.p, i)

    for name, provider in (("&pull-enumerate", CountingEnumerate()),
                           ("&pull-match", CountingMatch())):
        with metta._new_space() as m:
            m._register_space(provider, name)
            groups = m.run(f"!(collapse (match {name} (p $x) $x))")
            answers = groups[0][0].children
            assert len(answers) == 2000
            assert provider.yields == 2000, (
                f"{type(provider).__name__} was pulled "
                f"{provider.yields} times for 2000 candidates"
            )
