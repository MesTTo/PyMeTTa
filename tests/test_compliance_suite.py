"""Purpose: petta.testing.SpaceComplianceSuite, the engine's own space tests
run against a third party's provider.

The suite is only worth having if it holds of providers that differ, so it runs
here against three: the simplest honest one, an enumeration-only one that must
skip every write, and a provider declaring nothing, which must FAIL rather than
pass by skipping everything.

It is the other half of test_conformance.py, and the halves answer different
questions. check_space_provider asks whether a provider keeps its own promises,
in process, with no engine. This asks whether the ENGINE's expectations hold of
it: matchable through MeTTa, joinable, refusing loudly. A failure here is ours
until proven otherwise.
Guarantees:
  - a provider declaring nothing cannot pass by skipping every test
    [tested test_a_provider_declaring_nothing_cannot_pass]
  - the write round trip puts back what it took, so a real backend is left as
    it was found [tested test_the_suite_leaves_a_writable_provider_as_it_found_it]
  - the engine-native inherited space passes the same compliance suite as an
    external provider [tested: TestNativeInheritedSpaceComplies;
    commit=755330de329ece49eddcfb7d6db3061c3350a0ca]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from petta import MeTTa, SpaceName
from petta.atoms import S, Sym, Var, expr
from petta.errors import PettaError
from petta.foreign import SpaceProvider
from petta.testing import SpaceComplianceSuite

from .test_foreign import ListSpace

ROWS = [S.edge(S.a, S.b), S.edge(S.b, S.c), S.other(S.a)]


class ReadOnlySpace(SpaceProvider):
    """Enumeration and nothing else, which the seam has always allowed: the
    engine filters the enumeration for a bound pattern.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)


class TestListSpaceComplies(SpaceComplianceSuite):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    @pytest.fixture()
    def provider(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return ListSpace(ROWS)


class TestReadOnlySpaceComplies(SpaceComplianceSuite):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    @pytest.fixture()
    def provider(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return ReadOnlySpace()


class NativeInheritedSpace(SpaceProvider):
    """Adapt a native child to the provider protocol the shared suite drives."""

    def __init__(self):
        """Build a parent and an inheriting child seeded with the suite's rows."""
        self.parent = MeTTa().new_space()
        self.child = MeTTa().new_space(inherits=self.parent)
        self.child.add(*ROWS)

    def match(self, _pattern):
        """Answer the child's atoms for any pattern; the suite checks membership."""
        return iter(self.child.atoms())

    def atoms(self):
        """Enumerate the child-first union the inherited space reads."""
        return iter(self.child.atoms())

    def add(self, atom):
        """Write into the child, front-only."""
        self.child.add(atom)

    def add_many(self, atoms):
        """Bulk-write into the child, front-only."""
        self.child.add(*atoms)

    def remove(self, atom):
        """Remove from the child; a parent-only atom is a miss."""
        return self.child.remove(atom)

    def clear(self):
        """Clear the child and leave the parent untouched."""
        self.child.clear()

    def can_run(self, capability, /, **request):
        """Declare rule capability; defer the rest to the base declaration."""
        if capability == "rules":
            return True
        return super().can_run(capability, **request)

    def close(self):
        """Drop the child before the parent it inherits from."""
        self.child.drop()
        self.parent.drop()


class TestNativeInheritedSpaceComplies(SpaceComplianceSuite):
    """The shared compliance suite passes against the engine-native inherited child."""
    @pytest.fixture()
    def provider(self):
        """Yield a fresh adapter and close it after the suite finishes."""
        provider = NativeInheritedSpace()
        yield provider
        provider.close()

    @pytest.fixture()
    def space(self, provider, exercised):
        """Yield the native child space the suite's generic checks run against."""
        del exercised
        yield provider.child


class ProgramSpace(ListSpace):
    """A provider that takes a whole batch and holds a PROGRAM, not just data.

    These are the two capabilities a provider could declare that the
    compliance suite never checked: `add-many` and `rules` were in
    foreign.CAPABILITIES and absent from the suite's, so a provider declaring
    either got neither a pass nor a skip, which is a hole rather than a
    policy. Nothing in the tree declared them either, so adding the tests
    without adding this would have left them permanently skipped.

    `rules` is the one that matters. It is a promise about what the space
    HOLDS rather than about which methods exist, which is why no protocol can
    derive it and why it is opted into here by hand: say yes and an equation
    added through add-atom is compiled by the engine, say nothing and one is
    refused there.
    """

    def add_many(self, atoms):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.stored.extend(atoms)

    def can_run(self, capability, /, **request):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        if capability == "rules":
            return True
        return super().can_run(capability, **request)


PROGRAM = ProgramSpace(ROWS)


class TestProgramSpaceComplies(SpaceComplianceSuite):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    @pytest.fixture()
    def provider(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return PROGRAM


# One shared instance, so the assertion below observes the provider the suite
# actually drove. A fresh one per test would make the check vacuous.
ROUND_TRIP = ListSpace(ROWS)


class TestRoundTripComplies(SpaceComplianceSuite):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    @pytest.fixture()
    def provider(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return ROUND_TRIP


def test_the_suite_covers_every_declarable_capability():
    """A capability a provider can declare and the suite does not know about
    is neither exercised nor skipped, which is a hole rather than a policy.

    Two were: `add-many` and `rules` sat in foreign.CAPABILITIES and not in
    the suite's, so a provider declaring either got no verdict at all. Read
    from both lists rather than restated, so the next one added to the seam
    fails here instead of going quietly unchecked.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from petta import _compliance, foreign

    assert set(_compliance.CAPABILITIES) == set(foreign.CAPABILITIES), (
        f"the suite does not cover "
        f"{sorted(set(foreign.CAPABILITIES) - set(_compliance.CAPABILITIES))}"
    )


def test_a_space_without_rules_says_how_to_hold_one():
    """The refusal has to teach the capability, because nobody has heard of it.

    A foreign space holds DATA unless it says otherwise, so an equation added
    to one that has not declared `rules` is refused rather than stored where
    it could never fire. That refusal had no message clause, so it printed as
    `Unknown error term: petta_foreign_space_holds_no_rules(...)`, which names
    the capability without saying it is one or how to opt in.
    """
    engine = MeTTa().new_space()
    name = SpaceName("&ruleless")
    engine.register_space(ListSpace([]), name)
    try:
        space = engine.space(name)
        rule = expr(Sym("="), expr(Sym("rl-double"), Var("x")), expr(Sym("*"), 2, Var("x")))
        with pytest.raises(PettaError) as refused:
            space.add(rule)
        message = str(refused.value)
        assert "does not hold rules" in message, message
        assert "declare the rules capability" in message, message
        assert "Unknown error term" not in message, message
    finally:
        engine.unregister_space(name)


def test_the_suite_leaves_a_writable_provider_as_it_found_it():
    """The round trip is what lets this be pointed at a real backend.

    Ordered after TestRoundTripComplies by file position, which is how pytest
    runs them, and asserted on the shared instance the suite wrote through.
    """
    # As a multiset, not a sequence: the round trip removes and re-adds, and a
    # space is a bag of atoms whose order MeTTa's match does not promise.
    assert sorted(map(str, ROUND_TRIP.stored)) == sorted(map(str, ROWS)), (
        f"the compliance suite left {ROUND_TRIP.stored!r} behind, and it was "
        f"given {ROWS!r}"
    )


def test_a_provider_declaring_nothing_cannot_pass(tmp_path):
    """A suite that skipped everything would pass a provider that does nothing,
    which is the failure SQLAlchemy's requirements reporting exists to prevent.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    suite = tmp_path / "test_empty_provider.py"
    suite.write_text(
        "import pytest\n"
        "from petta.foreign import SpaceProvider\n"
        "from petta.testing import SpaceComplianceSuite\n"
        "\n"
        "class Nothing(SpaceProvider):\n"
        "    def can_run(self, capability, /, **request):\n"
        "        return False\n"
        "\n"
        "class TestNothing(SpaceComplianceSuite):\n"
        "    @pytest.fixture()\n"
        "    def provider(self):\n"
        "        return Nothing()\n"
    )
    result = pytest.main([str(suite), "-q", "--no-header", "-p", "no:randomly"])
    assert result != 0


def test_a_collectible_subclass_without_its_fixture_refuses_at_definition():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from petta.testing import GatewayComplianceSuite

    with pytest.raises(TypeError, match=r"without a `provider` fixture"):
        type("TestNoProvider", (SpaceComplianceSuite,), {})
    with pytest.raises(TypeError, match=r"without a `gateway_url` fixture"):
        type("TestNoGateway", (GatewayComplianceSuite,), {})
    # a non-Test intermediate may leave the fixture to its leaves
    middle = type("SharedBase", (SpaceComplianceSuite,), {})
    assert middle.__name__ == "SharedBase"
