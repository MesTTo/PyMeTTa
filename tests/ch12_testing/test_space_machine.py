"""Purpose: the exported bag-law machine, run against three kinds of space.

`SpaceMachine` is the library's own stateful machine made general, so what has
to hold is that it still passes over the space it was written for, that it
passes over somebody else's provider, and that it FAILS over a provider that
breaks the law it checks. A machine that cannot fail is not a machine, so the
deliberately wrong provider is the load-bearing case here.

Guarantees:
  - the machine passes over a native scratch space and over a Python provider
    that keeps the multiset laws [tested: test_a_native_space_is_a_multiset,
    test_a_python_provider_that_keeps_the_laws_passes]
  - a provider that drops a duplicate fails, and the shrunk history names the
    rule that exposed it
    [tested: test_a_provider_that_drops_a_duplicate_fails_the_machine]
  - a provider that removes every copy instead of one fails on the removal rule
    [tested: test_a_provider_that_removes_every_copy_fails_the_machine]
  - each planted defect is exercised before random rules, and the same
    histories pass for a correct provider
    [tested: test_a_provider_that_drops_a_duplicate_fails_the_machine,
    test_a_provider_that_removes_every_copy_fails_the_machine,
    test_the_planted_histories_pass_for_a_correct_provider; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - a capability the provider does not declare skips exactly its own rules, by
    name, with the engine's own refusal as the reason
    [tested: test_a_provider_without_removal_skips_only_the_removal_rules]
  - transaction and speculation rules run for a native space, skip for a
    foreign one that does not promise a rollback, and run again once it does
    [tested: test_the_transaction_rules_follow_the_spaces_own_promise]
  - the model starts from what the space already holds
    [tested: test_the_model_starts_from_what_the_space_already_holds]
  - construction refuses a space the machine cannot drive, naming the two
    conformance surfaces that can ask it something
    [tested: test_a_read_only_provider_is_refused_with_somewhere_else_to_go]
  - for_(factory) answers a class, so the same object is both the argument
    run_state_machine_as_test documents and the pytest shape
    [tested: test_the_bound_machine_is_both_a_callable_and_a_test_case]
Owns: one registered provider name per test, dropped by the machine's own
  teardown or by the test that made it
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import itertools

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, settings  # noqa: E402
from hypothesis.stateful import initialize, run_state_machine_as_test  # noqa: E402

import metta as metta_package  # noqa: E402
from metta import (  # noqa: E402 -- import follows its initialization prerequisite
    S,
    testing,
)
from metta._errors.errors import MettaError  # noqa: E402
from metta.foreign import SpaceProvider  # noqa: E402

#: Short random walks check passing providers. Planted providers exercise
#: their counterexample in an initialization rule, before any random rule.
#: The longer native sweep is tests/ch04_spaces_and_matching/test_space_stateful.py.
SHORT = settings(
    max_examples=10,
    stateful_step_count=12,
    deadline=None,
    suppress_health_check=list(HealthCheck),
)

_NAMES = itertools.count()


class Bag(SpaceProvider):
    """A list holding atoms, with the multiset laws kept."""

    declares = ("match", "enumerate", "add", "remove", "clear")

    def __init__(self, held=()):
        """Hold the given atoms, in the order they arrive."""
        self.items = list(held)

    def can_run(self, capability, /, **request):
        """Declare exactly the capabilities this bag implements."""
        del request
        return capability in self.declares

    def atoms(self):
        """Every atom held, as a snapshot the caller may outlive."""
        return iter(list(self.items))

    def add(self, atom):
        """Append one atom, duplicates and all."""
        self.items.append(atom)

    def remove(self, atom):
        """Take ONE copy, and say whether one was there."""
        if atom in self.items:
            self.items.remove(atom)
            return True
        return False

    def clear(self):
        """Drop every copy of everything."""
        self.items.clear()

    def match(self, pattern):
        """Over-approximate: every atom is a candidate the engine re-unifies."""
        del pattern
        return iter(list(self.items))

    def __len__(self):
        """How many atoms are held, copies counted."""
        return len(self.items)


class Deduping(Bag):
    """Wrong on purpose: a second copy of an atom is dropped."""

    def add(self, atom):
        """Append only what is not already held, which loses multiplicity."""
        if atom not in self.items:
            self.items.append(atom)


class Sweeping(Bag):
    """Wrong on purpose: removal takes every copy rather than one."""

    def remove(self, atom):
        """Take EVERY copy, which loses the one-copy law."""
        if atom not in self.items:
            return False
        self.items[:] = [held for held in self.items if held != atom]
        return True


class DuplicateWitness(testing.SpaceMachine):
    """Exercise the duplicate law before random rules can clear the space."""

    @initialize(atom=testing.expressions(max_leaves=5, ground=True))
    def write_two_copies(self, atom):
        """Let the inherited invariant check the inherited duplicate rule."""
        self.add_a_second_copy(atom)


class RemovalWitness(testing.SpaceMachine):
    """Exercise removal while two copies are known to be present."""

    @initialize(atom=testing.expressions(max_leaves=5, ground=True))
    def remove_one_of_two(self, atom):
        """Establish the duplicate bag before checking one-copy subtraction."""
        self.add_a_second_copy(atom)
        self.storage_matches_the_model()
        self.remove_a_stored_atom(atom)


class WriteOnly(Bag):
    """Neither enumerable nor writable: nothing for a model to compare."""

    declares = ("match",)


class Transactional(Bag):
    """A bag that participates in the engine's transactions."""

    def __init__(self, held=()):
        """Hold the given atoms, with room for one saved image."""
        super().__init__(held)
        self._saved = None

    def begin(self):
        """Save the image a rollback would restore."""
        self._saved = list(self.items)

    def commit(self):
        """Keep what was written and forget the image."""
        self._saved = None

    def rollback(self):
        """Put the saved image back."""
        if self._saved is not None:
            self.items[:] = self._saved
            self._saved = None


@pytest.fixture(name="foreign")
def _foreign(metta):
    """A factory answering a fresh registered space per call, all dropped after.

    The machine drops the space it was handed, so the list here only catches
    the ones a test makes for itself: `skips` takes a space and never runs a
    machine, and construction refusals never reach teardown.
    """
    made = []

    def factory(provider_class=Bag, held=(), atomicity=None):
        name = f"&machine-{next(_NAMES)}"
        space = metta_package.space(name, provider_class(held))
        if atomicity is not None:
            space.atomicity(atomicity)
        # The NAME rather than the handle: a dropped handle refuses even its
        # own name, and some of these are dropped by the machine under test.
        made.append((name, space))
        return space

    yield factory
    for name, space in made:
        if name in metta.space_names():
            space.drop()


def failing_history(machine_class) -> str:
    """The shrunk history Hypothesis printed for a machine that had to fail."""
    with pytest.raises(AssertionError) as caught:
        run_state_machine_as_test(machine_class, settings=SHORT)
    return "\n".join(getattr(caught.value, "__notes__", ()))


def test_a_native_space_is_a_multiset(metta):
    """The space the machine was written against, driven through the export."""
    run_state_machine_as_test(
        testing.SpaceMachine.for_(metta._new_space), settings=SHORT
    )


def test_a_python_provider_that_keeps_the_laws_passes():
    """Somebody else's store, proved by running the library's own machine."""

    def fresh():
        return metta_package.space(f"&machine-good-{next(_NAMES)}", Bag())

    run_state_machine_as_test(testing.SpaceMachine.for_(fresh), settings=SHORT)


def test_a_provider_that_drops_a_duplicate_fails_the_machine():
    """Multiplicity is the half of the contract a set-backed store loses.

    One add is indistinguishable from one add in a set. The second copy is
    what tells them apart, and the rule that writes it is what the shrunk
    history names.
    """

    def fresh():
        return metta_package.space(f"&machine-dedupe-{next(_NAMES)}", Deduping())

    history = failing_history(DuplicateWitness.for_(fresh))
    assert "write_two_copies" in history


def test_a_provider_that_removes_every_copy_fails_the_machine():
    """Removal subtracts ONE copy, which is the other half of the same law."""

    def fresh():
        return metta_package.space(f"&machine-sweep-{next(_NAMES)}", Sweeping())

    history = failing_history(RemovalWitness.for_(fresh))
    assert "remove_one_of_two" in history


@pytest.mark.parametrize("machine", (DuplicateWitness, RemovalWitness))
def test_the_planted_histories_pass_for_a_correct_provider(machine):
    """A forced history detects the provider defect without inventing one."""

    def fresh():
        return metta_package.space(f"&machine-witness-{next(_NAMES)}", Bag())

    run_state_machine_as_test(machine.for_(fresh), settings=SHORT)


def test_a_provider_without_removal_skips_only_the_removal_rules(foreign):
    """A capability the provider does not declare skips its rules by name.

    The reason is the ENGINE's refusal rather than a sentence written by the
    machine, so a provider author reads the same words a refused write would
    have given them.
    """
    space = foreign(provider_class=type("NoRemoval", (Bag,), {
        "declares": ("match", "enumerate", "add", "clear"),
    }))
    skipped = testing.SpaceMachine.skips(space)

    assert set(skipped) == {
        "remove_a_stored_atom",
        "remove_an_arbitrary_atom",
        "a_speculative_write_leaves_nothing",
        "a_committed_transaction_keeps_its_write",
        "a_rolled_back_transaction_keeps_nothing",
    }
    reason = skipped["remove_a_stored_atom"]
    assert "SpaceMachine.remove_a_stored_atom" in reason
    assert "NoRemoval" in reason
    assert "remove" in reason


def test_the_transaction_rules_follow_the_spaces_own_promise(metta, foreign):
    """Three answers to one question, read off the space's own declaration.

    A native space is the engine's own database and is rolled back with it. A
    foreign one that promises nothing is refused by the engine inside a
    transaction, so there is no law here to check and the rules skip. The same
    provider promising `transactional` runs them.
    """
    with metta._new_space() as native:
        assert testing.SpaceMachine.skips(native) == {}

    silent = foreign()
    assert set(testing.SpaceMachine.skips(silent)) == {
        "a_speculative_write_leaves_nothing",
        "a_committed_transaction_keeps_its_write",
        "a_rolled_back_transaction_keeps_nothing",
    }
    assert "nothing" in testing.SpaceMachine.skips(silent)[
        "a_rolled_back_transaction_keeps_nothing"
    ]

    promising = foreign(provider_class=Transactional, atomicity="transactional")
    assert testing.SpaceMachine.skips(promising) == {}

    accepting = foreign(provider_class=Transactional, atomicity="best-effort")
    assert set(testing.SpaceMachine.skips(accepting)) == {
        "a_speculative_write_leaves_nothing",
        "a_committed_transaction_keeps_its_write",
        "a_rolled_back_transaction_keeps_nothing",
    }


def test_a_transactional_provider_passes_every_rule():
    """With the promise kept as well as declared, the whole machine runs."""

    def fresh():
        space = metta_package.space(f"&machine-tx-{next(_NAMES)}", Transactional())
        space.atomicity("transactional")
        return space

    run_state_machine_as_test(testing.SpaceMachine.for_(fresh), settings=SHORT)


def test_the_model_starts_from_what_the_space_already_holds(foreign):
    """A store with rows in it is not an error, it is the starting bag."""
    space = foreign(held=[S.seed(S.one), S.seed(S.one), S.seed(S.two)])
    machine = testing.SpaceMachine(lambda: space)
    try:
        assert machine.model[S.seed(S.one)] == 2
        assert machine.model[S.seed(S.two)] == 1
        machine.storage_matches_the_model()
    finally:
        machine.teardown()


def test_a_read_only_provider_is_refused_with_somewhere_else_to_go(metta):
    """A machine that cannot write or cannot read back checks nothing.

    The refusal names the two conformance surfaces that CAN ask a read-only
    provider something, rather than leaving the author with a machine that
    passes by skipping everything.
    """
    name = f"&machine-ro-{next(_NAMES)}"
    space = metta_package.space(name, WriteOnly())
    with pytest.raises(MettaError) as caught:
        testing.SpaceMachine(lambda: space)

    assert caught.value.capability == "add"
    assert "WriteOnly" in str(caught.value)
    assert "check_space_provider" in caught.value.remedy.python
    # The refusal released the space it was handed, so nothing is left
    # registered for the next test on this worker.
    assert name not in metta.space_names()


def test_the_bound_machine_is_both_a_callable_and_a_test_case(metta):
    """for_(factory) answers a class, which is what makes one object do both.

    `run_state_machine_as_test` documents its argument as anything answering an
    instance when called with no arguments, and the pytest shape needs
    something carrying `.TestCase`. A class is both.
    """
    bound = testing.SpaceMachine.for_(metta._new_space)

    assert issubclass(bound, testing.SpaceMachine)
    assert "_new_space" in bound.__name__
    machine = bound()
    try:
        assert isinstance(machine, testing.SpaceMachine)
    finally:
        machine.teardown()
    assert hasattr(bound, "TestCase")


def test_an_unbound_machine_says_how_to_bind_one():
    """The base class has no factory, and says which two spellings supply one."""
    with pytest.raises(TypeError) as caught:
        testing.SpaceMachine()

    assert "SpaceMachine.for_(factory)" in str(caught.value)
    assert caught.value.remedy.python == "SpaceMachine.for_(<factory>)"
