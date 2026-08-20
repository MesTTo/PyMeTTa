"""Purpose: the engine's own space tests, pointed at somebody else's provider.

This is the rung above `check_space_provider`, and the two divide the work
along a line worth keeping sharp.

`check_space_provider` is the PROVIDER AUTHOR's half. It runs in process, calls
the provider's methods directly, needs no engine, and asks whether the object
keeps its own promises: that a declared capability has a method, that match
over-approximates rather than under-approximating, that an `exact` pushdown
claim is true. Those are facts about their code.

This is OUR half. It registers the provider on a real engine and runs the
expectations the ENGINE places on a space: that a stored atom is matchable
through MeTTa, that a conjunction joins across it, that an undeclared write
refuses loudly instead of answering nothing, that a bound is honoured whatever
the provider does with it. Those are facts about the seam, and they are ours to
keep true. An author gets them by subclassing rather than by reading a summary
of them, which is SQLAlchemy's dialect compliance suite, "the primary target
for new dialects", with about thirty external dialects on the strength of it
[source: SQLAlchemy README.dialects.rst,
https://github.com/sqlalchemy/sqlalchemy/blob/main/README.dialects.rst,
read 2026-08-16].

So this suite deliberately does NOT re-run `check_space_provider`. Folding one
into the other would make a failure ambiguous about whose code was wrong, which
is the whole value of having two. Run both; they answer different questions.

The exclusion half is already here and is better than SQLAlchemy's, which needs
a parallel `SuiteRequirements` class: a PeTTa provider declares its
capabilities on itself through `can_run`, so this reads the provider rather
than a second declaration that can disagree with it.

Assumes:
  - the provider under test holds atoms before the suite runs, or supplies
    them through the `stored` fixture; the suite does not choose the data,
    because it cannot know what the backend can hold
Guarantees:
  - a capability the provider does not declare is skipped, not failed, and a
    provider declaring nothing FAILS rather than passing vacuously
    [tested test_a_provider_declaring_nothing_cannot_pass]
  - writes are exercised by removing an atom the provider already holds and
    adding it back, and clear only when a subclass opts in, so the suite
    cannot destroy the data of the backend it is run against, and cannot
    demand a shape the backend has no table for
    [tested test_the_suite_leaves_a_writable_provider_as_it_found_it,
    test_a_write_round_trip_leaves_the_provider_as_it_was]
  - CAPABILITIES matches foreign.CAPABILITIES exactly, so a capability a
    provider can declare is either exercised or reported as skipped and never
    silently outside the suite. `add-many` and `rules` were the two that were
    [tested test_the_suite_covers_every_declarable_capability]
  - `rules` is checked on the provider's STORAGE and not only on the rule
    firing. The engine compiles an equation as it passes through add-atom, so
    a provider whose add() drops the atom still answers the call
    [measured 2026-08-17], and firing alone would pass for a provider holding
    nothing [tested test_a_declared_rule_space_holds_a_program]
  - the cross-space join witness carries the shared value and inspects the
    collapse result's children, so one joined row cannot look like no answer
    [tested: test_the_provider_joins_with_a_native_space;
    commit=755330de329ece49eddcfb7d6db3061c3350a0ca]
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
from typing import Any

from ._api_types import SpaceName
from ._optional import require_module
from .atoms import Expr, Sym, Var, expr
from .errors import PettaError
from .foreign import Enumerable
from .space import MeTTa

pytest = require_module(
    "pytest",
    "petta.testing.SpaceComplianceSuite is a pytest suite; install pytest to "
    "run it, or use check_space_provider(), which needs nothing",
)

CAPABILITIES = (
    "match", "enumerate", "add", "add-many", "remove", "clear", "subscribe",
    "plan", "rules",
)
MARKER = Sym("petta-compliance-marker")

_NAMES = itertools.count()


def _same_shape(stored, atom):
    """The stored atoms sharing an atom's head and argument count."""
    return [
        other
        for other in stored
        if isinstance(other, Expr)
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
    free = [Var(f"c{index}") for index in range(ground_prefix, len(atom.args))]
    return Expr([atom.head, *kept, *free])


def shaped_atom(stored: list) -> Any:
    """An atom the shape-dependent tests can be written against, or None.

    An expression with a symbol head and at least one argument. A provider
    holding only scalars or bare symbols has nothing with a shape to ask about,
    and those tests skip rather than inventing data the backend could not
    answer.
    """
    for atom in stored:
        if isinstance(atom, Expr) and isinstance(atom.head, Sym) and atom.args:
            return atom
    return None


class SpaceComplianceSuite:
    """The engine's space tests, run against your provider.

    Subclass it in your own test file and supply the provider:

        from petta.testing import SpaceComplianceSuite

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
        leaves, pytest's own collection contract."""
        super().__init_subclass__(**kwargs)
        if cls.__name__.startswith("Test") and not any(
            "provider" in ancestor.__dict__
            for ancestor in cls.__mro__
            if ancestor not in (SpaceComplianceSuite, object)
        ):
            raise TypeError(
                f"{cls.__name__} subclasses SpaceComplianceSuite without a "
                f"`provider` fixture; define one answering the provider "
                f"under test"
            )

    # ------------------------------------------------------------ fixtures

    @pytest.fixture()
    def provider(self):
        raise NotImplementedError(
            "a SpaceComplianceSuite subclass supplies a `provider` fixture "
            "answering the provider under test"
        )

    @pytest.fixture()
    def stored(self, provider) -> list:
        """What the provider holds. Enumeration by default; override it for a
        provider that does not enumerate."""
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
        otherwise pass by skipping everything."""
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
        if not record["ran"]:
            raise AssertionError(
                "the compliance suite exercised no capability at all. A "
                "provider that declares nothing cannot pass this suite by "
                "skipping every test in it"
            )

    @pytest.fixture()
    def space(self, provider, exercised):
        """The provider registered on a fresh engine, under its own name."""
        del exercised
        engine = MeTTa().new_space()
        name = SpaceName(f"&compliance{next(_NAMES)}")
        engine.register_space(provider, name)
        try:
            yield engine.space(name)
        finally:
            engine.unregister_space(name)

    # ------------------------------------------------------------- helpers

    def requires(self, provider, exercised, capability: str) -> None:
        """Read the provider's own declaration, and record either way."""
        if provider.can_run(capability):
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
        them is skipped on the other rather than failed for not having it."""
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
        """get-atoms and count read the provider, not a cache of it."""
        self.requires(provider, exercised, "enumerate")
        assert len(space.atoms()) == len(stored)
        assert space.count() == len(stored)

    def test_a_stored_atom_matches_itself(self, provider, exercised, space, stored):
        """Driven through the ENGINE rather than by calling match directly,
        which is the difference between this suite and check_space_provider:
        an atom the provider holds has to be reachable from MeTTa."""
        if not stored:
            pytest.skip("the provider holds no atoms to match")
        self.requires(provider, exercised, "match")
        for atom in stored[:8]:
            assert space.query(atom), (
                f"the provider holds {atom!r} and matching it answered nothing"
            )

    def test_an_open_pattern_answers_every_stored_atom_of_its_shape(
        self, provider, exercised, space, stored
    ):
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        same_shape = _same_shape(stored, atom)
        assert len(space.query(open_pattern(atom))) >= len(same_shape)

    def test_a_bound_position_selects_whatever_the_provider_yielded(
        self, provider, exercised, space, stored
    ):
        """The engine unifies, so a bound position filters even when the
        backend ignored it. This is the property that lets a provider
        over-approximate at all, and it is the engine's to keep.

        Checked in both directions, because one alone proves little: every
        atom of that shape with that leading value must come back, and every
        answer that comes back must rebuild into an atom the provider holds.
        """
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        pattern = open_pattern(atom, ground_prefix=1)
        rows = space.query(pattern)
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
            rebuilt = Expr([atom.head, atom.args[0], *row])
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
        """
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        if len(atom.args) < 2:
            pytest.skip("the shape has one argument, so nothing can repeat")
        fold = Var("pcfold")
        tail = open_pattern(atom).args[2:]
        pattern = Expr([atom.head, fold, fold, *tail])
        rows = space.query(pattern)
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
            rebuilt = Expr([atom.head, values[0], values[0], *values[1:]])
            assert str(rebuilt) in held, (
                f"{pattern!r} answered {rebuilt!r}, which is not a held atom "
                f"with equal positions, so a repeated variable did not "
                f"constrain the answer"
            )

    def test_a_conjunction_over_the_provider_joins(
        self, provider, exercised, space, stored
    ):
        """A self-join on one shape, which any provider holding that shape can
        answer. The engine routes each conjunct through the provider."""
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        left = open_pattern(atom)
        assert space.query(left, Expr([atom.head, *left.args]))

    def test_a_claimed_join_answers_what_the_split_answers(
        self, provider, exercised, space, stored
    ):
        """A claim is the one thing in this seam the engine cannot check.

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
        right = Expr([atom.head, *left.args])
        claimed = sorted(str(row) for row in space.query(left, right))
        with space.new_space() as native:
            native.add(*stored)
            split = sorted(str(row) for row in native.query(left, right))
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
        that with "no table 'petta-compliance-marker' in this DuckDB space".
        An atom the provider already holds is the one thing every backend is
        certainly able to accept, so the round trip uses that.
        """
        self.requires(provider, exercised, "remove")
        self.restore_or_skip(provider, exercised, "add")
        atom = self.restorable_or_skip(stored)[0]
        before = space.count() if provider.can_run("enumerate") else None
        space.remove(atom)
        assert not space.query(atom), "a removed atom still matched"
        space.add(atom)
        assert space.query(atom), "an added atom did not match"
        if before is not None:
            assert space.count() == before

    def test_a_batch_add_stores_every_atom(
        self, provider, exercised, space, stored
    ):
        """A batch is a TRANSPORT optimisation and never a semantic one, so it
        has to leave the space where a per-atom loop would.

        Written as a remove-then-restore for the same reason the single write
        is: the suite does not get to choose what a backend can store, and an
        invented marker is a shape a schema-bound provider has no table for.
        """
        self.requires(provider, exercised, "add-many")
        self.restore_or_skip(provider, exercised, "remove")
        batch = self.restorable_or_skip(stored, needed=2)[:4]
        before = space.count() if provider.can_run("enumerate") else None
        for atom in batch:
            space.remove(atom)
            assert not space.query(atom), f"{atom!r} still matched after removal"
        space.add(*batch)
        for atom in batch:
            assert space.query(atom), (
                f"{atom!r} went in as part of a batch and did not match"
            )
        if before is not None:
            assert space.count() == before, (
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
        """
        self.requires(provider, exercised, "rules")
        if not provider.can_run("add"):
            pytest.skip("a space that cannot be added to cannot be given a rule")
        doubled = expr(Sym("*"), 2, Var("x"))
        rule = expr(Sym("="), expr(MARKER, Var("x")), doubled)
        space.add(rule)
        try:
            if provider.can_run("match"):
                # Matched rather than compared as text: a stored atom's
                # variables are renamed apart on the way in and again on the
                # way out, so `(= (m $x) ...)` comes back as
                # `(= (m $_17586) ...)` and string equality would fail on a
                # provider that kept it perfectly.
                assert space.query(rule), (
                    f"the space declares rules and did not keep {rule!r}; "
                    f"an equation it drops is one no later reader can find"
                )
            answered = space.run(
                f"!(metta ({MARKER.name} 21) %Undefined% {space.space_name})"
            )
            assert answered and answered[-1] == [42], (
                f"the space declares rules and {rule!r} did not fire: "
                f"{answered!r}"
            )
        finally:
            if provider.can_run("remove"):
                space.remove(rule)

    def test_clear_empties_the_space(self, provider, exercised, space):
        """Skipped unless a subclass sets destructive, because the provider
        under test is usually pointed at data somebody wants to keep."""
        if not self.destructive:
            pytest.skip("set destructive = True to exercise clear")
        self.requires(provider, exercised, "clear")
        space.clear()
        assert space.count() == 0

    def test_an_undeclared_write_refuses_rather_than_answering_nothing(
        self, provider, exercised, space
    ):
        """An operation a space does not provide has to raise with the space
        and the operation named. Failing into "there is nothing there" is the
        shape that sends an author looking at their data."""
        absent = [
            capability
            for capability in ("add", "remove", "clear")
            if not provider.can_run(capability)
        ]
        if not absent:
            pytest.skip("the provider declares every write capability")
        exercised["skipped"].update(absent)
        marker = Expr([MARKER, Sym("refused")])
        for capability in absent:
            with pytest.raises(PettaError):
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
        seam stops working.

        Written as MeTTa source rather than through query(), because query()
        matches every pattern against ONE space and a cross-space join names
        the other space per conjunct.
        """
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        with space.new_space() as native:
            native.add(Expr([Sym("petta-compliance-native"), atom.args[0]]))
            answered = native.run(
                f"!(collapse (match {space.space_name} {open_pattern(atom)} "
                f"(match (context-space) "
                f"(petta-compliance-native $shared) (reached $shared))))"
            )
        assert answered and answered[0] and answered[0][0].children, (
            "a join between a native space and the provider answered nothing"
        )

    def test_a_bounded_query_answers_no_more_than_the_bound(
        self, provider, exercised, space, stored
    ):
        """The engine bounds the answers whatever the provider does with the
        number, so this holds of a provider that ignores it entirely."""
        self.requires(provider, exercised, "match")
        atom = self.shape_or_skip(stored)
        assert len(space.query(open_pattern(atom), limit=1)) <= 1
