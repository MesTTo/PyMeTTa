"""Purpose: the multiset laws of a space, as a machine run against any store.

A space is a multiset: order is unspecified, multiplicity is not. That one
sentence is the whole contract a backend has to keep, and it is a contract
about HISTORIES rather than about single calls, so a machine that generates a
history and checks it against a `Counter` is what proves it. The library's own
suite has run exactly that machine over a native space since the multiset
ruling; this is the same machine with the space it drives supplied by the
caller, so a third-party provider proves the laws instead of reading them.

The division of labour with the two conformance surfaces beside it:
`check_space_provider` asks whether the provider keeps its OWN promises, in
process and without an engine; `SpaceComplianceSuite` asks whether it satisfies
the ENGINE, one expectation per test; this asks whether a sequence of writes
leaves it holding what a multiset would. None of the three subsumes another,
and a provider that passes all three has been asked three different questions.

Prior art, and the shape taken from each: Hypothesis's own
`RuleBasedStateMachine` with a `Bundle` of what has been stored, which is
Quviq's `eqc_statem` model-and-commands shape
[source: hypothesis/docs/stateful.rst, the Bundle and precondition sections];
`run_state_machine_as_test(lambda: Machine(store))` as the way a machine is
pointed at a store the caller owns, which is what zarr-python's
`tests/test_store/test_stateful.py` and chroma's
`chromadb/test/property/test_embeddings.py` both do
[source: https://github.com/zarr-developers/zarr-python/blob/main/tests/test_store/test_stateful.py,
read 2026-09-07]; and SQLAlchemy's dialect compliance suite for the
subclass-and-supply shape `_compliance.py` already cites.

Assumes:
  - `space_factory()` answers a FRESH space the machine may write into, clear
    and drop; Hypothesis builds one machine per example, so a factory handing
    back the same space twice would carry one example's atoms into the next
Guarantees:
  - a rule whose capability the space does not declare is skipped by name with
    the engine's own refusal as the reason, and the mapping is answerable
    ahead of a run through `SpaceMachine.skips(space)` [tested:
    test_a_provider_without_removal_skips_only_the_removal_rules;
    commit=ef5b91d7950594a49e177d972a954841a6b8d6e0]
  - transaction and speculation rules run only where the space's writes are
    undone with the engine's, which is every native space and a foreign one
    declaring `(writes <space> transactional)`; anything else skips, because a
    write a rollback cannot undo is not a bag law to check [tested:
    test_the_transaction_rules_follow_the_spaces_own_promise; commit=ef5b91d7950594a49e177d972a954841a6b8d6e0]
  - the model is seeded from what the space already holds, so a provider
    pointed at a store with rows in it starts from those rather than from empty
    [tested: test_the_model_starts_from_what_the_space_already_holds;
    commit=ef5b91d7950594a49e177d972a954841a6b8d6e0]
  - a provider that drops a duplicate fails the run, and the failing rule is
    named [tested: test_a_provider_that_drops_a_duplicate_fails_the_machine;
    commit=ef5b91d7950594a49e177d972a954841a6b8d6e0]
Fails when:
  - the space cannot enumerate or cannot be written to. The model would have
    nothing to compare against or nothing to change, so construction refuses
    and names `check_space_provider` and `SpaceComplianceSuite`, which ask
    questions a read-only or opaque provider can answer
Owns resources: the space the factory answered, dropped in teardown whatever
  the run did
Decides: which of the multiset laws are general enough to hold of ANY space,
  and that the rest belong to the caller's own subclass; save and load are the
  worked example of one that does not, and live in the library's own subclass
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import contextlib
from collections import Counter
from typing import Any

from . import testing
from ._optional import require_module
from .atoms import Expression, Symbol, Variable, unify
from .errors import MettaError, Remedy, refusing
from .foreign import has_provider, require_capability
from .vocabularies import Atomicity

require_module(
    "hypothesis.stateful",
    "metta.testing.SpaceMachine is a hypothesis state machine; install "
    "pymetta[test] to run it, or use check_space_provider() and "
    "SpaceComplianceSuite, which need no hypothesis",
)

# The guard above has to run BEFORE this import, so that a missing hypothesis
# answers with the installation line rather than with a bare
# ModuleNotFoundError; the guard is a local import, so this third-party one
# cannot precede every local one and the ordering rule is waived here.
# pylint: disable-next=wrong-import-order
from hypothesis.stateful import (  # noqa: E402  -- the guard above answers a missing hypothesis first
    Bundle,
    RuleBasedStateMachine,
    invariant,
    precondition,
    rule,
)

#: The catalog space every context's declarations are stored in, which is where
#: the engine reads a space's atomicity from before it lets a transaction write
#: to it [source: engine/metta/space_hooks.pl, metta_writes/2 over
#: metta_contract_fact/1].
_CATALOG = "&metta"

#: The requirement key for the three rules that need the space's writes to be
#: undone with the engine's own. It is not one of foreign.CAPABILITIES: a
#: provider declares it as an atomicity rather than as a capability, so it is
#: read from the declaration rather than asked of `can_run`.
_ROLLBACK = "rollback"

#: Which requirement each rule needs, in one place, so that what `skips` says a
#: run will not check and what the run actually skips cannot disagree. Every
#: key is checked against the class below at import.
# closed-set: decides; policy=which provider capability each compliance rule needs, so what `skips` reports and what the run skips cannot differ; reads=none, it is the source, checked against the rule class at import
_RULE_REQUIREMENTS = {
    "remove_a_stored_atom": "remove",
    "remove_an_arbitrary_atom": "remove",
    "clear_everything": "clear",
    "query_answers_the_model": "match",
    "a_speculative_write_leaves_nothing": _ROLLBACK,
    "a_committed_transaction_keeps_its_write": _ROLLBACK,
    "a_rolled_back_transaction_keeps_nothing": _ROLLBACK,
}

#: What construction requires: something to change and something to read it
#: back with. `add` alone leaves the model unverifiable and `enumerate` alone
#: leaves it unchanging, so neither is a machine.
_REQUIRED = ("add", "enumerate")


class _RollbackError(Exception):
    """Raised inside a transaction body to roll it back.

    A transaction takes back everything its body wrote when the body raises,
    so a private exception nothing else catches is how the rule asks for a
    rollback. It never leaves the rule that raised it.
    """


def _substitute(atom: Any, bindings: dict[str, Any]) -> Any:
    """A pattern with its answer's bindings put back, which is the atom matched."""
    if isinstance(atom, Variable):
        return bindings.get(atom.name, atom)
    if isinstance(atom, Expression):
        return Expression([_substitute(child, bindings) for child in atom])
    return atom


def _capability_refusal(space: Any, capability: str, operation: str) -> str | None:
    """The engine's own sentence for a capability this space lacks, or None.

    `foreign.require_capability` is the door every write already passes
    through, so asking it here means the machine's idea of what a space can do
    is the engine's rather than a second reading of `can_run`. A space with no
    provider registered is native, and it answers for everything.
    """
    try:
        require_capability(str(space.name), capability, operation)
    except MettaError as refused:
        return str(refused)
    return None


def _declared_atomicity(space: Any) -> str:
    """What `(writes <space> ...)` says, or "nothing" where no row says anything."""
    rows = space._at(_CATALOG).match(
        Expression([Symbol("writes"), Symbol(str(space.name)), Variable("atomicity")])
    )
    return str(rows[0][0]) if rows else "nothing"


def _rollback_refusal(space: Any) -> str | None:
    """Why this space's writes do not follow a transaction, or None.

    A native space is the engine's own database and follows `transaction/1` by
    construction. A foreign one follows it exactly when it declares
    `transactional`: `best-effort` is the author's declared acceptance of a
    write that SURVIVES a rollback, and undeclared or `atomic-single` refuses a
    transactional write outright
    [source: engine/spaces/foreign.pl, foreign_write/3's atomicity branch].
    """
    if not has_provider(str(space.name)):
        return None
    declared = _declared_atomicity(space)
    if declared == Atomicity.transactional.value:
        return None
    return (
        f"{space.name} declares its writes as {declared}, so a rolled-back "
        f"transaction does not undo them and there is no bag law here to "
        f"check; declare atomicity('transactional') and implement "
        f"metta.foreign.Transactional to have these rules run"
    )


def _needs(rule_name: str):
    """The precondition that keeps a rule the space cannot support unselected."""
    return precondition(lambda machine: rule_name not in machine.skipped)


class SpaceMachine(RuleBasedStateMachine):
    """The multiset laws of a space, generated as histories and checked.

    Point it at your own store and run it:

        import itertools
        import metta
        from hypothesis.stateful import run_state_machine_as_test
        from metta import testing

        names = itertools.count()

        def fresh():
            return metta.space(f"&duckdb-{next(names)}", DuckDBSpace(connect()))

        def test_the_duckdb_space_is_a_multiset():
            run_state_machine_as_test(testing.SpaceMachine.for_(fresh))

    `for_(factory)` answers this machine bound to that factory, as a CLASS, so
    the pytest shape is the same object with Hypothesis's own `.TestCase` taken
    off it:

        TestDuckDBSpace = testing.SpaceMachine.for_(fresh).TestCase

    The longhand under both is `SpaceMachine(fresh)`, the constructor taking
    the factory, which is what `run_state_machine_as_test(lambda:
    SpaceMachine(fresh))` passes.

    Each generated step is one write, one read or one scoped write, and after
    every step the space is compared against a `Counter` of what the steps
    should have left there. What that catches is what single-call tests cannot:
    a store that drops a duplicate, one whose remove takes every copy instead
    of one, one whose clear leaves a row behind, one whose rollback does not.

    A rule whose capability the space does not declare is not run, and
    `SpaceMachine.skips(space)` answers which rules those are and why, ahead of
    any run, each reason the engine's own refusal. Construction requires `add`
    and `enumerate` and refuses without them, because a machine that cannot
    change the space or cannot read it back checks nothing.

    Add a law of your own by subclassing, exactly as you would extend any
    class; the library's own suite adds the native save/load round trip that
    way. This asks whether your space is a multiset under a history. Whether
    your provider keeps its own promises is `check_space_provider`, and whether
    it satisfies the engine is `SpaceComplianceSuite`. Run all three.
    """

    #: Set by `for_`; the constructor's argument overrides it.
    space_factory = None

    #: Every atom a rule has stored, so removal has something real to take.
    #: Non-consuming, so the same atom can be offered twice, which is how the
    #: "one copy leaves, not all of them" law gets generated.
    stored = Bundle("stored")

    def __init__(self, space_factory=None):
        """Build the machine over one fresh space, reading what it can do."""
        super().__init__()
        factory = space_factory if space_factory is not None else type(self).space_factory
        if factory is None:
            msg = (
                "SpaceMachine needs a factory answering a fresh space: pass one "
                "to the constructor, or bind one with SpaceMachine.for_(factory) "
                "and use the class it answers"
            )
            raise refusing(
                TypeError(msg),
                remedy=Remedy(
                    "bind the machine to a space factory",
                    "quickfix",
                    "prose",
                    python="SpaceMachine.for_(<factory>)",
                ),
            )
        self.space = factory()
        # Read once, because a dropped handle refuses even its own name, and
        # the refusal below drops before it raises.
        name = str(self.space.name)
        for capability in _REQUIRED:
            refusal = _capability_refusal(self.space, capability, "SpaceMachine")
            if refusal is None:
                continue
            # The factory has already made the space by the time the refusal is
            # known, and teardown only runs for a machine that was built, so
            # this is the one path that has to release it itself.
            self.space.drop()
            raise refusing(
                MettaError(refusal, space=name, capability=capability),
                remedy=Remedy(
                    "ask this provider a question it can answer",
                    "refactor",
                    "prose",
                    python=(
                        "metta.testing.check_space_provider(<provider>) or "
                        "class Test<Name>(metta.testing.SpaceComplianceSuite)"
                    ),
                ),
            )
        #: Rule name -> why this space skips it. Computed once: a space's
        #: declarations do not change under the machine's own steps.
        self.skipped = self.skips(self.space)
        self.model = Counter(self.space.atoms())
        # Countability is a separate promise from enumerability, and a foreign
        # space whose provider is not Sized refuses len() rather than counting
        # by enumerating [source: engine/metta/space_hooks.pl,
        # metta_foreign_space_count/1]. Asking once is a read and leaves
        # nothing behind; a proxy for the answer would be a second reading of
        # the same promise.
        try:
            len(self.space)
        except MettaError:
            self.countable = False
        else:
            self.countable = True

    @classmethod
    def for_(cls, space_factory) -> type[SpaceMachine]:
        """This machine bound to one factory, as a class.

        A class rather than a closure because Hypothesis's two entry points
        want different things from it and a class is both: it is a zero-
        argument callable answering an instance, which is what
        `run_state_machine_as_test` documents its argument as, and it carries
        `.TestCase`, which is the pytest shape.
        """
        return type(
            f"{cls.__name__}_{getattr(space_factory, '__name__', 'factory')}",
            (cls,),
            {
                "space_factory": staticmethod(space_factory),
                "__doc__": cls.__doc__,
            },
        )

    @staticmethod
    def skips(space: Any) -> dict[str, str]:
        """Which rules this space will not run, and the reason for each.

        Answerable without running anything, so a provider author reads what
        the machine will and will not check before spending a suite on it. Each
        reason is the engine's own refusal rather than a sentence written here.
        """
        reasons = {}
        for rule_name, requirement in _RULE_REQUIREMENTS.items():
            refusal = (
                _rollback_refusal(space)
                if requirement == _ROLLBACK
                else _capability_refusal(space, requirement, f"SpaceMachine.{rule_name}")
            )
            if refusal is not None:
                reasons[rule_name] = refusal
        return reasons

    # ---------------------------------------------------------------- writes

    @rule(target=stored, atom=testing.expressions(max_leaves=5, ground=True))
    def add_one(self, atom):
        """One atom in, one copy more."""
        self.space.add(atom)
        self.model[atom] += 1
        return atom

    @rule(target=stored, atom=testing.expressions(max_leaves=5, ground=True))
    def add_a_second_copy(self, atom):
        """The same atom twice in one call: a space holds two, not one."""
        self.space.add(atom, atom)
        self.model[atom] += 2
        return atom

    @_needs("remove_a_stored_atom")
    @rule(atom=stored)
    def remove_a_stored_atom(self, atom):
        """One copy leaves, and the answer says whether one was there.

        Multiset subtraction, and the bundle is what makes it bite: an atom
        drawn fresh is almost never stored, so a model that popped the whole
        count agreed with the space on every generated history until a real
        copy was removed.
        """
        assert self.space.remove(atom) is (atom in self.model)
        self.model -= Counter({atom: 1})

    @_needs("remove_an_arbitrary_atom")
    @rule(atom=testing.expressions(max_leaves=5, ground=True))
    def remove_an_arbitrary_atom(self, atom):
        """Removing what was never stored answers False and changes nothing."""
        assert self.space.remove(atom) is (atom in self.model)
        self.model -= Counter({atom: 1})

    @_needs("clear_everything")
    @rule()
    def clear_everything(self):
        """Empty means empty, every copy of every atom."""
        self.space.clear()
        self.model.clear()

    # ---------------------------------------------------------------- reads

    @_needs("query_answers_the_model")
    @rule(pattern=testing.expressions(max_leaves=5))
    def query_answers_the_model(self, pattern):
        """Every stored atom the pattern unifies with, once per copy.

        The answers are compared as a bag rather than as a list, because
        answer order within one query is unspecified and multiplicity is not.
        """
        expected: Counter = Counter()
        for atom, copies in self.model.items():
            if unify(pattern, atom) is not None:
                expected[atom] += copies

        rows = self.space.match(pattern)
        answered = Counter(
            _substitute(pattern, dict(zip(rows.columns, row, strict=True))) for row in rows
        )
        assert answered == expected

    # --------------------------------------------------------------- scopes

    @_needs("a_speculative_write_leaves_nothing")
    @rule(atom=testing.expressions(max_leaves=5, ground=True))
    def a_speculative_write_leaves_nothing(self, atom):
        """A what-if write is discarded when its call ends."""
        with self.space.speculative():
            self.space.add(atom)

    @_needs("a_committed_transaction_keeps_its_write")
    @rule(target=stored, atom=testing.expressions(max_leaves=5, ground=True))
    def a_committed_transaction_keeps_its_write(self, atom):
        """A transaction that returns keeps everything it wrote."""
        self.space.transaction(lambda: self.space.add(atom))
        self.model[atom] += 1
        return atom

    @_needs("a_rolled_back_transaction_keeps_nothing")
    @rule(atom=testing.expressions(max_leaves=5, ground=True))
    def a_rolled_back_transaction_keeps_nothing(self, atom):
        """A transaction whose body raises leaves the bag as it found it."""

        def write_then_fail() -> None:
            self.space.add(atom)
            raise _RollbackError

        with contextlib.suppress(_RollbackError):
            self.space.transaction(write_then_fail)

    # ------------------------------------------------------------ invariant

    @invariant()
    def storage_matches_the_model(self):
        """After every step: the same atoms, the same counts, the same size."""
        assert Counter(self.space.atoms()) == self.model
        if self.countable:
            assert len(self.space) == sum(self.model.values())
        for atom in self.model:
            assert atom in self.space

    def teardown(self):
        """Drop the space the factory answered, whatever the run did with it."""
        self.space.drop()


# The table above names rules by string, which is the one thing here that can
# go stale silently: a renamed rule would leave its row gating nothing and the
# rule running where the space cannot support it. Asking at import costs one
# dict walk and cannot be forgotten.
_UNKNOWN_RULES = sorted(name for name in _RULE_REQUIREMENTS if not hasattr(SpaceMachine, name))
if _UNKNOWN_RULES:  # pragma: no cover -- a structural error caught at import
    _MESSAGE = (
        f"_RULE_REQUIREMENTS names rules SpaceMachine does not define: "
        f"{', '.join(_UNKNOWN_RULES)}"
    )
    raise AttributeError(_MESSAGE)
