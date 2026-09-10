"""Purpose: the engine's own space tests, pointed at somebody else's provider.

This pytest layer sits above `check_space_provider`, and the two divide the
work along a line worth keeping sharp.

`check_space_provider` is the PROVIDER AUTHOR's half. It runs in process, calls
the provider's methods directly, needs no engine, and asks whether the object
keeps its own promises: that a declared capability has a method, that match
over-approximates rather than under-approximating, that an `exact` pushdown
claim is true. Those are facts about their code.

This is OUR half. It registers the provider on a real engine and runs the
expectations the ENGINE places on a space: that a stored atom is matchable
through MeTTa, that a conjunction joins across it, that an undeclared write
refuses loudly instead of answering nothing, that a bound is honoured whatever
the provider does with it. Those are properties of the provider protocol, and
they are ours to keep true. An author gets them by subclassing rather than by
reading a summary of them, which is SQLAlchemy's dialect compliance suite,
"the primary target for new dialects", with about thirty external dialects on
the strength of it
[source: SQLAlchemy README.dialects.rst,
https://github.com/sqlalchemy/sqlalchemy/blob/main/README.dialects.rst,
read 2026-08-16].

So this suite deliberately does NOT re-run `check_space_provider`. Folding one
into the other would make a failure ambiguous about whose code was wrong, which
is the whole value of having two. Run both; they answer different questions.

The exclusion half is already here and is better than SQLAlchemy's, which needs
a parallel `SuiteRequirements` class: a MeTTa provider declares its
capabilities on itself through `can_run`, so this reads the provider rather
than a second declaration that can disagree with it.

Assumes:
  - the provider under test holds atoms before the suite runs, or supplies
    them through the `stored` fixture; the suite does not choose the data,
    because it cannot know what the backend can hold
Guarantees:
  - optional exact mutations return a fresh token and remove that occurrence
    while retaining equal predecessors [tested: TestMutableTokenRowsComply;
    commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
  - a capability the provider does not declare is skipped, not failed, and a
    provider declaring nothing FAILS rather than passing vacuously
    [tested test_a_provider_declaring_nothing_cannot_pass]
  - writes are exercised by removing an atom the provider already holds and
    adding it back, and clear only when a subclass opts in, so the suite
    cannot destroy the data of the backend it is run against, and cannot
    demand a shape the backend has no table for
    [tested test_the_suite_leaves_a_writable_provider_as_it_found_it,
    test_a_write_round_trip_leaves_the_provider_as_it_was]
  - token identities are distinct, stable across reads and complete for the
    stored bag [tested: TestTokenRowsComply,
    test_compliance_rejects_unstable_tokens; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
  - every capability a provider can declare is either exercised or reported as
    skipped by the end of a run, so one the suite has no case for is named
    rather than silently outside it. `add-many` and `rules` were two that
    were; the check used to compare this module's own copy of the capability
    list against foreign.CAPABILITIES, which stopped being a check once both
    derived from the same catalog row
    [tested: test_the_suite_covers_every_declarable_capability;
    commit=7f9c810e5f4a2023ad98de34e848667dd72bc4a7]
  - provider enumeration and countability are separate: every Enumerable is
    checked through atoms(), while len(space) is checked only for Sized
    providers [tested: test_declared_length_answers_the_provider_size;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - `rules` is checked on the provider's STORAGE and not only on the rule
    firing. The engine compiles an equation as it passes through add-atom, so
    a provider whose add() drops the atom still answers the call
    [measured 2026-08-17], and firing alone would pass for a provider holding
    nothing [tested test_a_declared_rule_space_holds_a_program]
  - the cross-space join witness carries the shared value and inspects the
    collapse result's children, so one joined row cannot look like no answer
    [tested: test_the_provider_joins_with_a_native_space;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Owns: one registered space name per test, unregistered in the fixture's
  teardown whatever the test did
Decides: which of the engine's expectations are general enough to hold of ANY
  provider's data; the rest skip rather than inventing atoms a backend may not
  be able to store
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import itertools
from collections.abc import Sized
from typing import Any

from metta._atoms.designation import _SpaceId
from metta._atoms.factories import Expression, Symbol, Variable, _atom_from_wire, _expr
from metta._declare.declarations import _register_space, _unregister_space
from metta._errors.errors import MettaError
from metta._faces.metta import MeTTa
from metta._faces.space import Space
from metta._lazy import optional as require_module
from metta.foreign import CAPABILITIES, Enumerable, foreign_add_token, foreign_remove_token

pytest = require_module(
    "pytest",
    "metta.testing.SpaceComplianceSuite is a pytest suite; install pytest to "
    "run it, or use check_space_provider(), which needs nothing",
)

MARKER = Symbol("metta-compliance-marker")

_NAMES = itertools.count()


def _same_shape(stored, atom):
    """The stored atoms sharing an atom's head and argument count."""
    return [
        other
        for other in stored
        if isinstance(other, Expression)
        and other.head == atom.head
        and len(other.args) == len(atom.args)
    ]


def open_pattern(atom: Any, ground_prefix: int = 0) -> Any:
    """An atom's shape with its arguments replaced by fresh variables.

    `ground_prefix` keeps that many leading arguments as they are, which is how
    the suite asks a question with a known answer: every atom matching
    `(edge a $c1)` has `a` in that position, whatever the backend is.
    """
    kept = list(atom.args[:ground_prefix])
    free = [Variable(f"c{index}") for index in range(ground_prefix, len(atom.args))]
    return Expression([atom.head, *kept, *free])


def shaped_atom(stored: list) -> Any:
    """The widest atom the shape-dependent tests can be written against, or None.

    An expression with a symbol head and at least one argument. A provider
    holding only scalars or bare symbols has nothing with a shape to ask about,
    and those tests skip rather than inventing data the backend could not
    answer.

    The widest one rather than the first one enumerated, because a provider
    answers its atoms in no particular order: "Result order within one
    directive's list is unspecified; result multiplicity is specified".
    Taking the first meant that a provider
    holding both a one-argument and a two-argument atom either exercised
    test_a_repeated_variable_selects_equal_positions or skipped it depending on
    which one came out first, and adding a single never-called predicate to
    engine/metta.pl is enough to flip that: a native space enumerates through
    current_predicate/1 and SWI iterates its predicate table in an order that
    moves when a name is interned [measured 2026-08-23 with an inert control
    clause, which reordered TestNativeInheritedSpaceComplies on its own]. So
    the check was one unrelated engine edit away from silently becoming a skip.
    Ties break on the printed form, so the choice is the same on every run.
    """
    shaped = [
        atom
        for atom in stored
        if isinstance(atom, Expression) and isinstance(atom.head, Symbol) and atom.args
    ]
    if not shaped:
        return None
    return min(shaped, key=lambda atom: (-len(atom.args), str(atom)))


class SpaceComplianceSuite:
    """The engine's space tests, run against your provider.

    Subclass it in your own test file and supply the provider:

        from metta.testing import SpaceComplianceSuite

        class TestDuckDBSpace(SpaceComplianceSuite):
            @pytest.fixture()
            def provider(self):
                return DuckDBSpace(connection)

    Every test reads `can_run` before it runs, so a provider that does not
    implement `add` skips the write tests rather than failing them. What was
    exercised and what was skipped is reported at the end, because a suite that
    silently skipped everything would let a provider declaring nothing pass;
    that case is a failure here.

    Override one test the way you would any inherited method, and say why:

        class TestMine(SpaceComplianceSuite):
            @pytest.mark.skip("this backend cannot store a symbol head")
            def test_a_stored_atom_matches_itself(self): ...

    `clear` is not exercised unless you set `destructive = True`, because the
    provider under test is usually pointed at real data.

    This suite asks whether YOUR provider satisfies the ENGINE. Whether your
    provider keeps its own promises is `check_space_provider`, which runs in
    process and needs no engine. Run both.
    """

    destructive = False

    def __init_subclass__(cls, **kwargs) -> None:
        """Refuse a collectible subclass with no provider fixture at CLASS
        DEFINITION time, where the import traceback points at the class,
        instead of at pytest collection where it points at the suite. A
        non-Test-named intermediate base may leave the fixture to its
        leaves, pytest's own collection contract.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        super().__init_subclass__(**kwargs)
        if cls.__name__.startswith("Test") and not any(
            "provider" in ancestor.__dict__
            for ancestor in cls.__mro__
            if ancestor not in (SpaceComplianceSuite, object)
        ):
            msg = (
                f"{cls.__name__} subclasses SpaceComplianceSuite without a "
                f"`provider` fixture; define one answering the provider "
                f"under test"
            )
            raise TypeError(
                msg
            )

    # ------------------------------------------------------------ fixtures

    @pytest.fixture()
    def provider(self):
        msg = (
            "a SpaceComplianceSuite subclass supplies a `provider` fixture "
            "answering the provider under test"
        )
        raise NotImplementedError(
            msg
        )

    @pytest.fixture()
    def stored(self, provider) -> list:
        """What the provider holds. Enumeration by default; override it for a
        provider that does not enumerate.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if not isinstance(provider, Enumerable):
            pytest.skip(
                "the provider does not enumerate, so override the `stored` "
                "fixture with the atoms it holds"
            )
        return list(provider.atoms())

    @pytest.fixture(scope="class")
    @staticmethod
    def exercised(request):
        """What ran and what did not, reported the way SQLAlchemy reports its
        requirements, and asserted: a provider declaring nothing would
        otherwise pass by skipping everything.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        record: dict[str, set[str]] = {"ran": set(), "skipped": set()}
        yield record
        reporter = request.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line("")
            reporter.write_line(f"{request.cls.__name__}: space compliance")
            for capability in CAPABILITIES:
                if capability in record["ran"]:
                    reporter.write_line(f"  {capability}: exercised")
                elif capability in record["skipped"]:
                    reporter.write_line(f"  {capability}: not declared, skipped")
        # The coverage claim is about a WHOLE run of the suite. A developer
        # narrowing to one case with `-k` deselects the rest, and their record
        # is short for that reason rather than because the suite has a hole,
        # so the claim is only made when every case of this class was
        # selected. `--dist loadfile` keeps a file on one worker, so the
        # record is one class's whole run.
        cases = sum(1 for name in dir(request.cls) if name.startswith("test_"))
        selected = sum(
            1 for item in request.session.items if getattr(item, "cls", None) is request.cls
        )
        if selected < cases:
            return
        refusal = SpaceComplianceSuite.coverage_refusal(record)
        if refusal is not None:
            raise AssertionError(refusal)

    @pytest.fixture()
    def space(self, provider, exercised):
        """The provider registered on a fresh engine, under its own name."""
        del exercised
        engine = MeTTa(Space()).space()
        name = _SpaceId(f"&compliance{next(_NAMES)}")
        _register_space(engine, provider, name)
        try:
            yield engine._at(name)
        finally:
            _unregister_space(engine, name)

    # ------------------------------------------------------------- helpers

    @staticmethod
    def coverage_refusal(record: dict[str, set[str]]) -> str | None:
        """What is wrong with a finished run's capability record, or None.

        Two things can be, and both are silence rather than a red test unless
        somebody looks: a provider that declares nothing skips every case and
        passes, and a capability the SUITE has no case for reaches neither set
        and is simply never mentioned. `add-many` and `rules` were the second
        kind for as long as nothing asked.
        """
        if not record["ran"]:
            return (
                "the compliance suite exercised no capability at all. A "
                "provider that declares nothing cannot pass this suite by "
                "skipping every test in it"
            )
        uncovered = sorted(set(CAPABILITIES) - record["ran"] - record["skipped"])
        if uncovered:
            return (
                f"the compliance suite has no case for {', '.join(uncovered)}: "
                f"a capability a provider can declare must be exercised or "
                f"reported as skipped, never left without a verdict"
            )
        return None

    def requires(self, provider, exercised, capability: str, **request: Any) -> None:
        """Read the provider's own declaration, and record either way.

        `request` is what `can_run` narrows a declaration by: `subscribe`
        takes `on=`, because a store with no remove never emits a removal and
        a watcher for one would wait forever.
        """
        if provider.can_run(capability, **request):
            exercised["ran"].add(capability)
            return
        exercised["skipped"].add(capability)
        pytest.skip(f"the provider does not declare {capability}")

    def restorable_or_skip(self, stored: list, needed: int = 1) -> list:
        """Atoms the provider holds EXACTLY ONCE.

        They are the only ones a round trip can restore: remove one of an
        identical pair and add it back and the bag is the same, but a provider
        that lost one would look identical to one that did not.
        """
        once = [atom for atom in stored if stored.count(atom) == 1]
        if len(once) < needed:
            pytest.skip(
                f"the provider holds fewer than {needed} atom(s) exactly once, "
                f"so removing and adding back would not restore what was there"
            )
        return once

    def restore_or_skip(self, provider, exercised, other: str) -> None:
        """A round trip needs both directions, and a provider with only one of
        them is skipped on the other rather than failed for not having it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if not provider.can_run(other):
            exercised["skipped"].add(other)
            pytest.skip(f"a round trip needs {other} as well")
        exercised["ran"].add(other)

    def shape_or_skip(self, stored: list):
        with_shape = shaped_atom(stored)
        if with_shape is None:
            pytest.skip("the provider holds no expression with arguments")
        return with_shape

    # --------------------------------------------------------------- tests

    def test_enumeration_answers_what_the_provider_holds(
        self, provider, exercised, space, stored
    ):
        """get-atoms reads the provider rather than a cache of it."""
        self.requires(provider, exercised, "enumerate")
        assert len(space.atoms()) == len(stored)

    def test_tokens_identify_each_stored_occurrence_stably(
        self, provider, exercised, space, stored
    ):
        """Identity reads preserve the stored bag and survive an unchanged read."""
        self.requires(provider, exercised, "tokens")
        tokens = space.blame(Variable("occurrence"))
        assert len(tokens) == len(stored)
        assert len(set(tokens)) == len(tokens)
        assert tokens == space.blame(Variable("occurrence"))

    @pytest.mark.parametrize("capability", ("add-token", "remove-token"))
    def test_exact_token_mutation_restores_the_occurrence_bag(
        self, provider, exercised, space, stored, capability
    ):
        """A returned identity selects the new copy and leaves equal old rows."""
        self.requires(provider, exercised, capability)
        other = "remove-token" if capability == "add-token" else "add-token"
        self.restore_or_skip(provider, exercised, other)
        self.restore_or_skip(provider, exercised, "tokens")
        if not stored:
            pytest.skip("a mutation round trip needs one already supported atom")
        atom = stored[0]
        before = space.blame(Variable("occurrence"))
        wire = foreign_add_token(space.name, atom.to_wire())
        token = _atom_from_wire(wire)
        try:
            assert token not in before, "add-token reused a live identity"
            assert set(space.blame(Variable("occurrence"))) == {*before, token}
        finally:
            assert foreign_remove_token(space.name, wire) is True
        assert foreign_remove_token(space.name, wire) is False
        assert space.blame(Variable("occurrence")) == before

    def test_declared_length_answers_the_provider_size(
        self, provider, space, stored
    ):
        """Sized is the provider's explicit countability declaration."""
        if not isinstance(provider, Sized):
            pytest.skip("the provider does not declare countability through __len__")
        assert len(space) == len(stored)

    def test_a_stored_atom_matches_itself(self, provider, exercised, space, stored):
        """Driven through the ENGINE rather than by calling match directly,
        which is the difference between this suite and check_space_provider:
        an atom the provider holds has to be reachable from MeTTa.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if not stored:
            pytest.skip("the provider holds no atoms to match")
        self.requires(provider, exercised, "match")
        for atom in stored[:8]:
            assert space.match(atom), (
                f"the provider holds {atom!r} and matching it answered nothing"
            )

    def test_an_open_pattern_answers_every_stored_atom_of_its_shape(
        self, provider, exercised, space, stored
    ):
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        same_shape = _same_shape(stored, atom)
        assert len(space.match(open_pattern(atom))) >= len(same_shape)

    def test_a_bound_position_selects_whatever_the_provider_yielded(
        self, provider, exercised, space, stored
    ):
        """The engine unifies, so a bound position filters even when the
        backend ignored it. This is the property that lets a provider
        over-approximate at all, and it is the engine's to keep.

        Checked in both directions, because one alone proves little: every
        atom of that shape with that leading value must come back, and every
        answer that comes back must rebuild into an atom the provider holds.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        pattern = open_pattern(atom, ground_prefix=1)
        rows = space.match(pattern)
        wanted = [
            other
            for other in _same_shape(stored, atom)
            if other.args[0] == atom.args[0]
        ]
        assert len(rows) >= len(wanted), (
            f"the provider holds {len(wanted)} atom(s) matching {pattern!r} "
            f"and the engine answered {len(rows)}"
        )
        held = {str(other) for other in stored}
        for row in rows:
            rebuilt = Expression([atom.head, atom.args[0], *row])
            assert str(rebuilt) in held, (
                f"{pattern!r} answered {rebuilt!r}, which the provider does "
                f"not hold, so the engine did not filter what it yielded"
            )

    def test_a_repeated_variable_selects_equal_positions(
        self, provider, exercised, space, stored
    ):
        """One variable in two positions answers only atoms whose two
        positions are equal, whatever the backend yielded. A backend filter
        that checks each position independently is the classic wrong
        filter, exact on all ground data and wrong the first time a
        pattern repeats a variable; the engine's own unification is what
        keeps it sound, and this is the query that proves it held.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        if len(atom.args) < 2:
            pytest.skip("the shape has one argument, so nothing can repeat")
        fold = Variable("pcfold")
        tail = open_pattern(atom).args[2:]
        pattern = Expression([atom.head, fold, fold, *tail])
        rows = space.match(pattern)
        wanted = [
            other
            for other in _same_shape(stored, atom)
            if str(other.args[0]) == str(other.args[1])
        ]
        assert len(rows) >= len(wanted), (
            f"the provider holds {len(wanted)} atom(s) with equal leading "
            f"positions and {pattern!r} answered {len(rows)}"
        )
        held = {str(other) for other in wanted}
        for row in rows:
            values = list(row)
            rebuilt = Expression([atom.head, values[0], values[0], *values[1:]])
            assert str(rebuilt) in held, (
                f"{pattern!r} answered {rebuilt!r}, which is not a held atom "
                f"with equal positions, so a repeated variable did not "
                f"constrain the answer"
            )

    def test_a_conjunction_over_the_provider_joins(
        self, provider, exercised, space, stored
    ):
        """A self-join on one shape, which any provider holding that shape can
        answer. The engine routes each conjunct through the provider.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        left = open_pattern(atom)
        assert space.match(left, Expression([atom.head, *left.args]))

    def test_a_claimed_join_answers_what_the_split_answers(
        self, provider, exercised, space, stored
    ):
        """A claim is the one part of this provider contract the engine cannot check.

        Everywhere else a provider may over-approximate, because the engine
        re-unifies each candidate it yields and that is cheap. Claiming a
        conjunction is different: verifying one row of a join means running the
        join, so the engine has to trust the claim on the hot path. That makes
        it exactly the thing a conformance kit should not trust.

        So the same conjunction is asked of the provider and of a native space
        holding the atoms the provider holds, and the answers must agree.
        """
        self.requires(provider, exercised, "plan")
        atom = self.shape_or_skip(stored)
        left = open_pattern(atom)
        right = Expression([atom.head, *left.args])
        claimed = sorted(str(row) for row in space.match(left, right))
        with space._new_space() as native:
            native.add(*stored)
            split = sorted(str(row) for row in native.match(left, right))
        assert claimed == split, (
            f"{type(provider).__name__} declares the plan capability and its "
            f"claim answered {claimed}, where the engine's own split over the "
            f"same atoms answered {split}. A claim is exact: a provider that "
            f"cannot answer a conjunction exactly must decline it, because the "
            f"engine plans only what you leave and never re-checks a row."
        )

    def test_a_write_round_trip_leaves_the_provider_as_it_was(
        self, provider, exercised, space, stored
    ):
        """Remove an atom the provider holds, then put it back.

        Written this way round on purpose. The suite does not get to choose
        what a backend can store: an invented marker atom is a shape a
        schema-bound provider has no table for, and DuckDB refused exactly
        that with "no table 'metta-compliance-marker' in this DuckDB space".
        An atom the provider already holds is the one thing every backend is
        certainly able to accept, so the round trip uses that.
        """
        self.requires(provider, exercised, "remove")
        self.restore_or_skip(provider, exercised, "add")
        atom = self.restorable_or_skip(stored)[0]
        before = len(space.atoms()) if provider.can_run("enumerate") else None
        space.remove(atom)
        assert not space.match(atom), "a removed atom still matched"
        space.add(atom)
        assert space.match(atom), "an added atom did not match"
        if before is not None:
            assert len(space.atoms()) == before

    def test_a_batch_add_stores_every_atom(
        self, provider, exercised, space, stored
    ):
        """A batch is a TRANSPORT optimisation and never a semantic one, so it
        has to leave the space where a per-atom loop would.

        Written as a remove-then-restore for the same reason the single write
        is: the suite does not get to choose what a backend can store, and an
        invented marker is a shape a schema-bound provider has no table for.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "add-many")
        self.restore_or_skip(provider, exercised, "remove")
        batch = self.restorable_or_skip(stored, needed=2)[:4]
        before = len(space.atoms()) if provider.can_run("enumerate") else None
        for atom in batch:
            space.remove(atom)
            assert not space.match(atom), f"{atom!r} still matched after removal"
        space.add(*batch)
        for atom in batch:
            assert space.match(atom), (
                f"{atom!r} went in as part of a batch and did not match"
            )
        if before is not None:
            assert len(space.atoms()) == before, (
                "a batch add left a different number of atoms than the "
                "per-atom removes took out"
            )

    def test_a_declared_rule_space_holds_a_program(
        self, provider, exercised, space
    ):
        """`rules` is the capability that separates a data source from a place
        a program lives, and it is the one no protocol can derive: it is a
        promise about what the space HOLDS, not about which methods exist.

        So the check is the promise, and it takes both halves. The engine
        compiles an equation as it goes THROUGH add-atom, which is why an
        equation arriving by a backend's own bulk loader is stored and inert.
        The consequence for this test is that firing alone proves nothing
        about the provider: a provider whose add() silently drops the atom
        still answers 42, measured. So the storage is asserted separately,
        and it is the half that can actually fail here.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "rules")
        if not provider.can_run("add"):
            pytest.skip("a space that cannot be added to cannot be given a rule")
        doubled = _expr(Symbol("*"), 2, Variable("x"))
        rule = _expr(Symbol("="), _expr(MARKER, Variable("x")), doubled)
        space.add(rule)
        try:
            if provider.can_run("match"):
                # Matched rather than compared as text: a stored atom's
                # variables are renamed apart on the way in and again on the
                # way out, so `(= (m $x) ...)` comes back as
                # `(= (m $_17586) ...)` and string equality would fail on a
                # provider that kept it perfectly.
                assert space.match(rule), (
                    f"the space declares rules and did not keep {rule!r}; "
                    f"an equation it drops is one no later reader can find"
                )
            answered = space.run(
                f"!(metta ({MARKER.name} 21) %Undefined% {space.name})"
            )
            assert answered and answered[-1] == [42], (
                f"the space declares rules and {rule!r} did not fire: "
                f"{answered!r}"
            )
        finally:
            if provider.can_run("remove"):
                space.remove(rule)

    def test_a_declared_event_promise_delivers_a_write(
        self, provider, exercised, space
    ):
        """`subscribe` is the other capability no protocol can derive: it is a
        promise about what the SPACE can deliver rather than about which
        methods exist, because a remote store's contents change on the server
        whether or not this process wrote them.

        So the check is the promise, end to end: subscribe to a pattern, write
        an atom that matches it through the space, and read the event back.
        A provider that declares the promise and delivers nothing leaves a
        watcher waiting forever, which is the failure a poll would never have
        told anyone about.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "subscribe", on="add")
        if not provider.can_run("add"):
            pytest.skip("a space that cannot be added to emits no add event")
        announced = Expression([MARKER, Symbol("announced"), Symbol(str(next(_NAMES)))])
        watcher = space.watch(announced, on="add", deadline=5.0)
        try:
            space.add(announced)
            seen = next(iter(watcher))
            assert seen is not None, (
                f"the space declares an event promise and {announced!r} "
                f"arrived with no event; a watcher would wait forever"
            )
        finally:
            watcher.close()
            if provider.can_run("remove"):
                space.remove(announced)

    def test_clear_empties_the_space(self, provider, exercised, space):
        """Skipped unless a subclass sets destructive, because the provider
        under test is usually pointed at data somebody wants to keep.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if not self.destructive:
            # Recorded before the skip, because a capability with no verdict at
            # all is what the coverage check in `exercised` refuses.
            exercised["skipped"].add("clear")
            pytest.skip("set destructive = True to exercise clear")
        self.requires(provider, exercised, "clear")
        space.clear()
        assert space.atoms() == []

    def test_an_undeclared_write_refuses_rather_than_answering_nothing(
        self, provider, exercised, space
    ):
        """An operation a space does not provide has to raise with the space
        and the operation named. Failing into "there is nothing there" is the
        shape that sends an author looking at their data.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        absent = [
            capability
            for capability in ("add", "remove", "clear")
            if not provider.can_run(capability)
        ]
        if not absent:
            pytest.skip("the provider declares every write capability")
        exercised["skipped"].update(absent)
        marker = Expression([MARKER, Symbol("refused")])
        for capability in absent:
            with pytest.raises(MettaError):
                if capability == "add":
                    space.add(marker)
                elif capability == "remove":
                    space.remove(marker)
                else:
                    space.clear()

    def test_the_provider_joins_with_a_native_space(
        self, provider, exercised, space, stored
    ):
        """The provider's atoms have to reach a query that is not entirely
        about the provider, which is where a space that half implements the
        provider interface stops working.

        Written as MeTTa source rather than through match(), because match()
        matches every pattern against ONE space and a cross-space join names
        the other space per conjunct.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        with space._new_space() as native:
            native.add(Expression([Symbol("metta-compliance-native"), atom.args[0]]))
            answered = native.run(
                f"!(collapse (match {space.name} {open_pattern(atom)} "
                f"(match (context-space) "
                f"(metta-compliance-native $shared) (reached $shared))))"
            )
        assert answered and answered[0] and answered[0][0].children, (
            "a join between a native space and the provider answered nothing"
        )

    def test_a_bounded_query_answers_no_more_than_the_bound(
        self, provider, exercised, space, stored
    ):
        """The engine bounds the answers whatever the provider does with the
        number, so this holds of a provider that ignores it entirely.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        assert len(space.match(open_pattern(atom), limit=1)) <= 1
