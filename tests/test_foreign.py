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
"""

from collections.abc import Iterator
from typing import Any, ClassVar

import pytest

import petta.foreign as foreign_module
from petta import (
    Adder,
    Atom,
    Clearer,
    EngineError,
    Enumerable,
    Expr,
    Matcher,
    MeTTa,
    PettaError,
    Remover,
    S,
    V,
    Var,
    expr,
    unify,
)
from petta.foreign import SpaceProvider, register_provider, unregister_provider


class ListSpace(SpaceProvider):
    """The simplest honest provider: a Python list of atoms.

    test_compliance_suite.py runs the shipped SpaceComplianceSuite against
    this, so the engine's general expectations of a space are checked here
    once rather than restated per test.
    """

    def __init__(self, atoms=()):
        self.stored = list(atoms)

    def match(self, pattern):
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
    metta.register_space(provider, name)
    yield name, provider, metta
    metta.unregister_space(name)


# What the SpaceComplianceSuite already checks, over three providers rather
# than this one, is not restated here: an atom the provider holds is matchable,
# an open pattern answers every atom of its shape, a bound position filters
# what the provider over-approximated, enumeration answers what it holds, and
# an undeclared write refuses. What stays is the concrete answer, which says
# more than the general property, and everything the suite deliberately leaves
# alone: registration, the refusal MODEL, and the bound's mechanics.


def test_match_answers_exactly_what_the_pattern_names(listspace):
    name, _provider, m = listspace
    r = m.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
    assert r == [[expr(expr(S.a, S.b), expr(S.b, S.c))]]
    # The provider yields (other 1) too, and unification is the engine's.
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
    metta.register_space(ReadOnly(), name)
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
    metta.register_space(provider, name)
    try:
        metta.space(name).add(S.allowed(1))
        with pytest.raises(EngineError, match="declines this add request"):
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
    metta.register_space(first, "&col")
    try:
        with pytest.raises(ValueError):
            metta.register_space(Empty(), "&col")
        # The same provider again is idempotent, not a collision.
        metta.register_space(first, "&col")
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


# The capability model carried a boolean and no reason, so _require_provider
# had to guess the wording from the capability name and got it wrong: a
# provider that IMPLEMENTS add and declines it was told it "does not implement
# add", and the sentence saying what to do instead, which the provider had
# already written, ran nowhere.
def test_a_provider_states_its_own_refusal(metta):
    class Curated(SpaceProvider):
        def atoms(self):
            return iter(())

        def add(self, atom):
            raise AssertionError("declined before this runs")

        def can_run(self, capability, /, **request):
            if capability == "add":
                return False
            return super().can_run(capability, **request)

        def refusal(self, capability, /, **_request):
            if capability == "add":
                return "this space is curated; write to it with the loader"
            return None

    name = "&curated-refusal-test"
    metta.register_space(Curated(), name)
    try:
        with pytest.raises(PettaError, match="curated; write to it with the loader"):
            metta.space(name).add(S.f(S.a))
    finally:
        metta.unregister_space(name)


# "does not implement" is wrong for a provider that implements and declines,
# and the model already draws that distinction: the base class's own can_run
# answers "is it there at all" independently of the subclass's policy.
def test_declining_and_not_implementing_read_differently(metta):
    class Declines(SpaceProvider):
        def atoms(self):
            return iter(())

        def add(self, atom):
            raise AssertionError("declined before this runs")

        def can_run(self, capability, /, **request):
            return False if capability == "add" else super().can_run(capability, **request)

    class Absent(SpaceProvider):
        def atoms(self):
            return iter(())

    metta.register_space(Declines(), "&declines-add-test")
    metta.register_space(Absent(), "&absent-add-test")
    try:
        with pytest.raises(PettaError, match="declines this add request"):
            metta.space("&declines-add-test").add(S.f(S.a))
        with pytest.raises(PettaError, match="does not implement add"):
            metta.space("&absent-add-test").add(S.f(S.a))
    finally:
        metta.unregister_space("&declines-add-test")
        metta.unregister_space("&absent-add-test")


# The declared capability was enforced where the operation is NAMED and
# bypassed where it is USED: foreign_match checked only "match", then fell
# through to atoms() for an Enumerable provider, so a provider allowing match
# and declining enumerate had atoms() called anyway.
def test_a_declined_enumerate_is_not_reached_through_match(metta):
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
    metta.register_space(NoEnumerate(), name)
    try:
        with pytest.raises(PettaError, match="declines this enumerate request"):
            metta.run(f"!(match {name} (edge $a $b) $a)")
        assert not NoEnumerate.called
    finally:
        metta.unregister_space(name)


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

    def match(self, pattern, *, limit=None):
        self.asked.append(limit)
        yield from self._yield_up_to(
            self.atoms_held if limit is None else min(self.atoms_held, limit)
        )

    def pushdown(self, pattern):
        return "exact"


class _Unbounded(_Countable):
    """Written before the option existed; must be called exactly as it was."""

    def match(self, pattern):
        yield from self._yield_up_to(self.atoms_held)


@pytest.mark.parametrize("limit", [1, 3, 10])
def test_a_bound_reaches_a_provider_that_takes_one(metta, limit):
    provider = _Bounded(500)
    metta.register_space(provider, "&bounded-test")
    try:
        rows = MeTTa("&bounded-test").query(S.fact(V.k, V.v), limit=limit)
        assert len(rows) == limit
        assert provider.asked == [limit]
        # It stopped at the bound rather than at the engine's cut, which is
        # the whole point: the backend did not produce what nobody wanted.
        assert provider.produced == limit
    finally:
        metta.unregister_space("&bounded-test")


def test_a_provider_without_the_keyword_is_called_as_before(metta):
    provider = _Unbounded(500)
    metta.register_space(provider, "&unbounded-test")
    try:
        rows = MeTTa("&unbounded-test").query(S.fact(V.k, V.v), limit=3)
        assert len(rows) == 3
        # One past the bound, which is what a lazy pull costs, and nothing
        # like the 500 it holds.
        assert provider.produced == 4
    finally:
        metta.unregister_space("&unbounded-test")


class _UnclaimedBounded(_Countable):
    """Takes a limit keyword and claims nothing. It must not be given one.

    This is the provider the classification exists to protect against: it
    would truncate at whatever it is told, and nothing about it says its
    candidates are its answers. Withholding the number is what stops it
    under-answering, which is the one thing the seam's contract forbids.
    """

    def match(self, pattern, *, limit=None):
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
    metta.register_space(provider, "&unclaimed-test")
    try:
        rows = MeTTa("&unclaimed-test").query(S.fact(V.k, V.v), limit=3)
        assert len(rows) == 3
        assert provider.asked == [None]
    finally:
        metta.unregister_space("&unclaimed-test")


def test_a_metta_take_pushes_its_bound_to_the_provider(metta):
    """`take` is the MeTTa-level bound, and it reaches the SAME seam
    m.query(limit=) reaches rather than a second one beside it.

    Until it existed the two halves were unjoined: BoundedMatcher.limit had
    the concept and only the Python query surface could set it, so a MeTTa
    program bounding its own answers enumerated the backend and discarded.
    """
    provider = _Bounded(500)
    metta.register_space(provider, "&take-test")
    try:
        space = MeTTa("&take-test")
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
        metta.unregister_space("&take-test")


def test_a_take_over_a_join_keeps_its_bound_to_itself(metta):
    """Across a join the bound belongs to the JOINED rows.

    An outer match truncated at N loses the rows its later candidates would
    have joined to, so the pushdown is decided by shape and a conjunction does
    not get it. The answers are still bounded, by the engine, which is what
    makes the pushdown a pure optimisation on top of a correct bound.
    """
    provider = _Bounded(50)
    metta.register_space(provider, "&take-join")
    try:
        space = MeTTa("&take-join")
        answered = space.run(
            "!(collapse (take 2 (match &take-join "
            "(, (fact $k $v) (fact $k2 $v)) ($k $k2))))"
        )[-1]
        assert len(answered[0]) == 2
        assert provider.asked and set(provider.asked) == {None}, provider.asked
    finally:
        metta.unregister_space("&take-join")


def test_a_take_withholds_its_bound_from_a_provider_that_claimed_nothing(metta):
    """The exactness gate is upstream of `take` and stays upstream of it.

    A provider that takes a limit keyword and never claimed its candidates
    are its answers would truncate at whatever it is told, so it is not told.
    """
    provider = _UnclaimedBounded(500)
    metta.register_space(provider, "&take-unclaimed")
    try:
        space = MeTTa("&take-unclaimed")
        answered = space.run(
            "!(collapse (take 3 (match &take-unclaimed (fact $k $v) (fact $k $v))))"
        )[-1]
        assert len(answered[0]) == 3
        assert provider.asked == [None]
    finally:
        metta.unregister_space("&take-unclaimed")


def test_a_pushdown_class_that_is_neither_word_is_refused(metta):
    """A claim that is neither word is a mistake, not a value to fall back
    from: falling back would silently discard a real exact."""

    class _Nonsense(_Countable):
        def match(self, pattern):
            yield from self._yield_up_to(self.atoms_held)

        def pushdown(self, pattern):
            return "probably"

    provider = _Nonsense(5)
    metta.register_space(provider, "&nonsense-test")
    try:
        with pytest.raises(PettaError, match="answered 'probably'"):
            MeTTa("&nonsense-test").query(S.fact(V.k, V.v), limit=2)
    finally:
        metta.unregister_space("&nonsense-test")


def test_a_python_providers_capabilities_reach_the_engine(metta):
    """The two halves of the seam had two capability models that never met.

    foreign.py derives the set from the narrow protocols a provider implements
    and enforces it well. The Prolog side reads metta_foreign_capability/2 and
    saw nothing at all, so foreign_provides/2 reported that every Python
    provider provides EVERYTHING: anything the engine decides from a
    declaration silently excluded exactly the providers most likely to be
    incomplete, and a sixth capability could never join the vocabulary.
    """

    class MatchOnly(SpaceProvider):
        def atoms(self):
            return iter([S.fact(1)])

    name = "&capability-projection-test"
    metta.register_space(MatchOnly(), name)
    try:
        declared = metta._rt.must(
            "findall(_C, user:metta_foreign_capability(S, _C), L)", S=name
        )["L"]
        assert sorted(str(c) for c in declared) == ["enumerate", "match"]
    finally:
        metta.unregister_space(name)
    # And they go with the provider.
    assert not metta._rt.must(
        "findall(_C, user:metta_foreign_capability(S, _C), L)", S=name
    )["L"]


def test_an_absent_capability_still_carries_the_providers_own_words(metta):
    """The projection made the ENGINE refuse first, which would have lost the
    message. The refusal is a seam now, so it is raised where the words are."""

    class Curated(SpaceProvider):
        def atoms(self):
            return iter(())

        def refusal(self, capability, /, **_request):
            return "load this space with the importer" if capability == "add" else None

    name = "&refusal-seam-test"
    metta.register_space(Curated(), name)
    try:
        with pytest.raises(PettaError, match="load this space with the importer"):
            metta.space(name).add(S.f(S.a))
    finally:
        metta.unregister_space(name)


def test_a_prolog_only_provider_answers_a_bounded_query(metta, tmp_path):
    """One match hook, so a Prolog provider is reached whatever Python is doing.

    There used to be a /2 beside metta_foreign_match/3, chosen between with
    `clause(metta_foreign_match(_,_,_), _)`, which asks whether ANY provider
    anywhere declared the bounded form. The Python shim declares it
    unconditionally, so with Python in the process that guard was true for
    every space: a Prolog-only provider writing /2 had /3 called instead, the
    shim's clause failed its own ownership check, and the whole match answered
    nothing. Reproduced as `unbounded: 3, bounded: 0`.
    """
    source = tmp_path / "prolog_only_space.pl"
    source.write_text(
        ":- multifile metta_foreign_space/1.\n"
        ":- multifile metta_foreign_match/3.\n"
        ":- multifile metta_foreign_pushdown/3.\n"
        "metta_foreign_space('&prolog-only-test').\n"
        "metta_foreign_match('&prolog-only-test', P, _) :-\n"
        "    member(P, [[fact, 1], [fact, 2], [fact, 3]]).\n"
        "metta_foreign_pushdown('&prolog-only-test', _, exact).\n"
    )
    metta._rt.consult(str(source))
    space = metta.space("&prolog-only-test")
    assert len(space.query(S.fact(V.n))) == 3
    assert len(space.query(S.fact(V.n), limit=2)) == 2


def test_a_bound_is_not_pushed_past_a_join(metta):
    """Across a join the bound belongs to the joined rows. An outer match
    truncated at N would lose the rows its later candidates would join to,
    which is under-answering, the one thing the contract forbids."""
    provider = _Bounded(20)
    metta.register_space(provider, "&join-bound-test")
    try:
        rows = MeTTa("&join-bound-test").query(
            S.fact(V.k, V.v), S.fact(V.k, V.w), limit=2
        )
        assert len(rows) == 2
        assert provider.asked and all(asked is None for asked in provider.asked)
    finally:
        metta.unregister_space("&join-bound-test")


def test_an_unbounded_query_asks_for_nothing_in_particular(metta):
    provider = _Bounded(7)
    metta.register_space(provider, "&nolimit-test")
    try:
        rows = MeTTa("&nolimit-test").query(S.fact(V.k, V.v))
        assert len(rows) == 7
        assert provider.asked == [None]
    finally:
        metta.unregister_space("&nolimit-test")


def test_a_provider_ignoring_the_bound_is_still_bounded_by_the_engine(metta):
    """Honouring the bound is the provider's decision, so the engine may not
    depend on it. This one is told 2 and answers everything anyway."""

    class Defiant(_Countable):
        def match(self, pattern, *, limit=None):
            self.asked.append(limit)
            yield from self._yield_up_to(self.atoms_held)

        def pushdown(self, pattern):
            return "exact"

    provider = Defiant(50)
    metta.register_space(provider, "&defiant-test")
    try:
        rows = MeTTa("&defiant-test").query(S.fact(V.k, V.v), limit=2)
        assert len(rows) == 2
        assert provider.asked == [2]
    finally:
        metta.unregister_space("&defiant-test")


class JoiningSpace(SpaceProvider):
    """A provider that answers a whole conjunction itself.

    The naive nested loop is the point: what a claim buys is not this
    provider's strategy but that the engine hands over the whole conjunction,
    so a backend with a real join can use it. MORK's worst-case-optimal join
    goes through the same seam and is exercised in test_mork_space.py.
    """

    def __init__(self) -> None:
        self.rows: list[Atom] = []
        self.claims = 0

    def atoms(self):
        return iter(self.rows)

    def add(self, atom: Atom) -> None:
        self.rows.append(atom)

    def plan(self, patterns):
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
    if isinstance(atom, Var):
        return bindings.get(atom.name, atom)
    if isinstance(atom, Expr):
        return Expr([_substitute(child, bindings) for child in atom.children])
    return atom


class DecliningPlanner(JoiningSpace):
    def plan(self, patterns):
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
        space = metta.space(name)
        space.add(*_JOIN_ATOMS)
        claimed = sorted(str(row) for row in space.query(*query))
        with metta.fresh_space() as native:
            native.add(*_JOIN_ATOMS)
            split = sorted(str(row) for row in native.query(*query))
        return claimed, split
    finally:
        unregister_provider(metta.runtime, name)


def test_a_claimed_join_answers_what_the_engines_split_answers(metta):
    """A conjunction reaches the provider whole. The oracle is the engine's own
    split over a native space holding the same atoms, because a claim is the one
    place in this seam where a provider may not over-approximate: there is no
    cheap re-check for a join, so the differential stands in for one."""
    provider = JoiningSpace()
    claimed, split = _both_ways(
        metta, provider, "&py_join", S.edge(V.x, V.y), S.tag(V.y, V.t)
    )
    assert claimed == split
    assert provider.claims == 1


def test_declining_a_conjunction_falls_back_to_the_split(metta):
    """Returning None is what a provider without a join does, and it must leave
    behaviour exactly as it was: asked, declined, and answered correctly."""
    provider = DecliningPlanner()
    claimed, split = _both_ways(
        metta, provider, "&py_nojoin", S.edge(V.x, V.y), S.tag(V.y, V.t)
    )
    assert claimed == split
    assert provider.claims == 1


def test_plan_is_a_capability_derived_from_the_protocol():
    assert JoiningSpace().can_run("plan") is True
    assert ListSpace().can_run("plan") is False
