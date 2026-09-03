"""Purpose: metta.testing.check_space_provider, the conformance kit a
downstream library runs against its own provider.

The platform ships the suite for its own extension points, which is the CSI
sanity suite's reading and JDBC's and pytest's `pytester`. Without it a library
learns its provider is wrong from a bug report. These tests are the kit's own
kit: they assert it catches the two mistakes it exists for.
Guarantees:
  - a provider that under-approximates its match is refused, naming the atom
    [tested test_the_kit_catches_an_under_approximating_matcher]
  - a capability declared without its method is refused at check time rather
    than inside an engine callback
    [tested test_the_kit_catches_a_capability_with_no_method]
  - a provider claiming its filtering exact while over-approximating is
    refused, which is the one claim in the seam that can cost answers
    [tested test_a_false_exact_claim_is_caught]
  - a registered Python-backed Space handle reaches the engine checker and
    passes every declared hook's qualified ownership guard
    [tested: test_a_python_backed_space_handle_passes_the_engine_checker;
    commit=90362cf551149c822a05fb26fbf80d0c2ce11fa4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa, Space, testing
from metta.atoms import Expression, Variable, parse
from metta.foreign import SpaceProvider
from metta.spaces import view

ROWS = [parse("(edge a b)"), parse("(edge b c)")]


class Conforming(SpaceProvider):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)

    def match(self, pattern):  # noqa: ARG002, D102  -- the test double preserves the protocol method signature its caller exercises; the test double method is documented by its containing scenario and protocol
        # Every atom, every time: over-approximating is always correct,
        # because the engine keeps unification.
        return iter(ROWS)


class Enumerating(SpaceProvider):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)


class UnderApproximating(SpaceProvider):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)

    def match(self, pattern):  # noqa: ARG002, D102  -- the test double preserves the protocol method signature its caller exercises; the test double method is documented by its containing scenario and protocol
        return iter(())


class FalselyExact(SpaceProvider):
    """Claims exact and over-approximates, which is the combination that loses
    answers: the engine hands it the caller's bound, it truncates at N, and
    fewer than N of those N candidates were answers.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)

    def match(self, pattern):  # noqa: ARG002, D102  -- the test double preserves the protocol method signature its caller exercises; the test double method is documented by its containing scenario and protocol
        return iter(ROWS)

    def pushdown(self, pattern):  # noqa: ARG002, D102  -- the test double preserves the protocol method signature its caller exercises; the test double method is documented by its containing scenario and protocol
        return "exact"


def _ground(atom):
    if isinstance(atom, Variable):
        return False
    if isinstance(atom, Expression):
        return all(_ground(child) for child in atom.children)
    return True


class TrulyExact(SpaceProvider):
    """Claims exact for ground patterns and filters those by equality; an
    open pattern is answered by over-approximation and claimed inexact.
    That is the honest shape of an equality-filtered source: the earlier
    version of this fixture claimed exact for everything while filtering
    by equality, which under-answers every open pattern, exactly the
    docstring-only claim the kit exists to refuse.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)

    def match(self, pattern):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        if _ground(pattern):
            return iter([row for row in ROWS if row == pattern])
        return iter(ROWS)

    def pushdown(self, pattern):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return "exact" if _ground(pattern) else "inexact"


class RepeatedVariableLiar(SpaceProvider):
    """Filters each position independently, the classic wrong filter: exact
    on every ground pattern, and it answers (edge a b) to (edge $x $x)
    because neither position alone disagrees. Ground self-match cannot
    catch it, which is why the kit checks the folded variants.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)

    def match(self, pattern):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        def hit(row):
            if not isinstance(pattern, Expression) or not isinstance(row, Expression):
                return row == pattern
            if len(row.children) != len(pattern.children):
                return False
            return all(
                isinstance(want, Variable) or want == got
                for want, got in zip(pattern.children, row.children, strict=True)
            )

        return iter([row for row in ROWS if hit(row)])

    def pushdown(self, pattern):  # noqa: ARG002, D102  -- the test double preserves the protocol method signature its caller exercises; the test double method is documented by its containing scenario and protocol
        return "exact"


class GroundOnlyMatcher(SpaceProvider):
    """Handles ground patterns and answers nothing for one with a variable,
    which under-answers every real query.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(ROWS)

    def match(self, pattern):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        if _ground(pattern):
            return iter([row for row in ROWS if row == pattern])
        return iter(())


class Lying(SpaceProvider):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(())

    def can_run(self, capability, /, **request):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        if capability == "add":
            return True
        return super().can_run(capability, **request)


class Explaining(SpaceProvider):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return iter(())

    def can_run(self, capability, /, **request):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        if capability == "add":
            return False
        return super().can_run(capability, **request)

    def refusal(self, capability, /, **_request):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        if capability == "add":
            return "load this space with the importer"
        return None


def test_a_conforming_provider_passes():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    checks = testing.check_space_provider(Conforming())
    # Two atoms, each vouching for a family of eight patterns: itself,
    # three opened positions, the all-arguments form, and three folds.
    assert any(
        "over-approximation holds over 16 patterns" in line for line in checks
    )


def test_an_enumeration_only_provider_passes():
    """The Python seam has always said enumeration is enough, and the Prolog
    seam now agrees, so the kit must not demand a Matcher.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    checks = testing.check_space_provider(Enumerating())
    assert any("enumeration is the candidate set" in line for line in checks)


def test_the_kit_catches_an_under_approximating_matcher():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(AssertionError, match="answered neither"):
        testing.check_space_provider(UnderApproximating())


def test_a_false_exact_claim_is_caught():
    """The one claim in the seam that can cost answers, so the kit tests it.

    Over-approximation being sound covers everything else a provider says.
    "exact" is different: it licenses truncating at the caller's bound, and a
    provider that truncates while yielding non-matching candidates answers
    fewer rows than exist, which the contract forbids.
    """
    with pytest.raises(AssertionError, match="claims exact and"):
        testing.check_space_provider(FalselyExact())


def test_a_true_exact_claim_passes_and_is_reported():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    checks = testing.check_space_provider(TrulyExact())
    # Of the sixteen family patterns only the two ground ones are claimed.
    assert any(
        "2 of 16 patterns claimed exact, and are" in line for line in checks
    )


def test_a_repeated_variable_liar_is_caught_by_the_folded_pattern():
    """The regression the family exists for: a positional filter is exact
    on all ground data, so the pre-family kit passed it, and it loses
    answers in production the first time a pattern repeats a variable.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with pytest.raises(AssertionError, match="claims exact and"):
        testing.check_space_provider(RepeatedVariableLiar())


def test_a_ground_only_matcher_is_caught_by_the_open_pattern():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(AssertionError, match="answered neither"):
        testing.check_space_provider(GroundOnlyMatcher())


def test_an_unclaimed_provider_is_reported_as_inexact():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    checks = testing.check_space_provider(Conforming())
    assert any("not claimed, so inexact and re-unified" in line for line in checks)


def test_the_kit_catches_a_capability_with_no_method():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(AssertionError, match="says yes to add and the method is not there"):
        testing.check_space_provider(Lying())


def test_the_kit_reports_a_providers_own_refusal():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    checks = testing.check_space_provider(Explaining())
    assert any("load this space with the importer" in line for line in checks)


def test_the_kit_refuses_something_that_is_not_a_provider():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class NotOne:
        def atoms(self):
            return iter(())

    with pytest.raises(AssertionError, match="is not a SpaceProvider"):
        testing.check_space_provider(NotOne())


def test_a_mangling_store_fails_the_round_trip_law():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The GetPut law: add then enumerate is identity on the stored atom,
    # so a store that normalizes case answers a DIFFERENT atom and must
    # fail loudly, named, instead of misanswering in production.
    class Uppercasing(SpaceProvider):
        def __init__(self):
            self.stored = []

        def add(self, atom):
            self.stored.append(parse(str(atom).upper()))

        def atoms(self):
            return iter(self.stored)

        def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return iter(self.stored)

    with pytest.raises(AssertionError, match="identity on the"):
        testing.check_space_provider(
            Uppercasing(), atoms_to_store=[parse("(fact low)")]
        )


def test_a_faithful_store_passes_the_round_trip_law():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Keeping(SpaceProvider):
        def __init__(self):
            self.stored = []

        def add(self, atom):
            self.stored.append(atom)

        def atoms(self):
            return iter(self.stored)

        def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return iter(self.stored)

    report = testing.check_space_provider(
        Keeping(), atoms_to_store=[parse("(fact (f $x) $x)")]
    )
    assert "round-trip: 1 stored atoms recovered intact" in report


def test_a_space_handle_dispatches_to_the_engine_checker(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The universal half of the door: handed an engine Space rather than a
    # Python object, the kit runs lib_conformance's checker through the seam,
    # in a scratch sibling so the subject space is never modified. The rows
    # name the seam's own hooks, which no Python-side lint ever does, so this
    # is the proof the ENGINE checker ran. The provider is the same shipped
    # fixture the conformance example opens, absolute because the engine
    # resolves a source path against the process working directory.
    m = MeTTa().space()
    m.register_prolog(
        path=repo_root / "examples" / "ch08-data" / "08-03-the-shipped-libraries" / "_fixtures" / "demo_provider.pl"
    )
    try:
        demo = m.metta.space("&demo_provider")
        assert isinstance(demo, Space)
        report = testing.check_space_provider(demo)
        assert "match: declared, seam:foreign_match/3 has clauses" in report
        assert (
            "match: over-approximation holds over 2 atoms and their pattern families"
            in report
        )
        assert "source: repeated, two enumerations agree" in report
    finally:
        # The registration is engine-global and outlives the handle; a later
        # test enumerating foreign spaces must not meet this fixture.
        m.unregister_prolog("demo_provider")


def test_a_python_backed_space_handle_passes_the_engine_checker():
    """A qualified Python hook body is inspected through its leading guard."""
    with view([1, 2, 3]) as python_space:
        report = testing.check_space_provider(python_space)

    assert "match: declared, seam:foreign_match/3 has clauses" in report
    assert (
        "match: over-approximation holds over 3 atoms and their pattern families"
        in report
    )
    assert "source: repeated, two enumerations agree" in report
