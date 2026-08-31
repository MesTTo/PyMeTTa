"""Purpose: record committed effect receipts and run declared compensations.

Assumes:
  - receipt writes and their subscription callbacks obey the existing
    transaction post-commit event law.
Guarantees:
  - ``Saga.run`` commits successful writesState-or-stronger operation
    receipts as ordinary ``(did op args result)`` atoms and a failed step
    publishes none [tested:
    test_committed_effects_leave_queryable_receipts_and_failed_steps_leave_none;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - rollback preflights every declaration, compensates in reverse receipt
    order, and retains the failed suffix for an idempotent retry [tested:
    test_saga_compensates_in_reverse_commit_order,
    test_saga_preflights_missing_compensations_before_undo,
    test_a_failed_compensation_can_be_retried_without_losing_its_receipt;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - a receipt space whose provider refuses its commit leaves no phantom
    obligation: the step's effects are recovered at once instead of being
    recorded against a journal entry that never became durable [tested:
    test_a_provider_receipt_space_commits_the_receipt_before_recovery_reads_it,
    test_a_refused_provider_commit_recovers_the_step_it_could_not_journal;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - an effect whose recovery receipt could not be made durable is retained
    as an obligation carrying no receipt, compensated at once and still
    retryable with rollback() after the scope closed. A failed durable write
    never costs the obligation it was recording [tested:
    test_a_refused_recovery_receipt_still_compensates_the_effect_it_could_not_record,
    test_an_unjournalled_obligation_survives_scope_close_and_a_later_rollback;
    commit=WORKTREE]
  - a step whose enlisted providers did not all commit is retained and
    refused by name rather than compensated on a guess, because the receipt
    records the operation and not the participant that carried it [tested:
    test_a_lost_participant_leaves_the_saga_in_doubt_rather_than_compensating;
    commit=WORKTREE]
Owns resources:
  - the receipt-space subscription opened on context entry and cancelled on
    every exit, including rollback and cancellation failures.
"""

from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

from ._ops import (
    _begin_receipt_capture,
    _CapturedReceipt,
    _end_receipt_capture,
    _select_receipt_operations,
    _suspend_receipt_capture,
)
from ._space_execution import speculative_enabled
from ._space_objects import _ACTIVE_BATCHES
from .atoms import (
    Atom,
    Expression,
    Symbol,
    Undefined,
    V,
    _atom_from_wire,
    _from_wire,
    _is_ground,
    _to_atom,
)
from .errors import EngineError, MettaError
from .foreign import Adder, Enumerable, Remover, Transactional
from .structures import _canonical

if TYPE_CHECKING:
    from ._space import Space
    from .subscribe import Subscription

__all__ = ["Saga"]


def _unenlisted(pending: list[_CapturedReceipt]) -> list[Expression]:
    """The step's effects its own engine transaction cannot roll back."""
    return [captured.atom for captured in pending if not captured.enlisted]


@dataclass(frozen=True)
class _Obligation:
    """One effect this runner owes a compensation for, and its journal state.

    ``journalled`` says a receipt for this effect is durable in the receipt
    space, which is the ordinary case and the one the reverse pass preflights
    against. It is False for an effect whose receipt write did NOT become
    durable, or whose durable outcome the receipt space cannot answer, and
    such an obligation is still owed: the effect happened. Rollback therefore
    compensates it without demanding a stored receipt, because demanding one
    is what left a surviving external effect with an obligation that could
    never be discharged.
    """

    atom: Expression
    journalled: bool


class _EmptySagaStepError(Exception):
    """Make a no-answer target trigger the callable transaction rollback."""


class _CompensationFailedError(Exception):
    """Roll back a handler whose ordinary evaluation outcome is failure."""


class Saga:
    """A scope of committed effect receipts and their reverse recovery.

    Construct it with ``space.saga(receipts)`` and run each forward term with
    :meth:`run`. A normal context exit keeps the committed work and its
    queryable receipt atoms. An exceptional exit invokes :meth:`rollback`.

    Compensation is semantic reversal, not restoration of an old snapshot.
    Each compensating operation receives the complete ``(did ...)`` record
    and must be idempotent because a failed recovery can be retried. The
    runner writes the call as ``(quote <record>)`` so the record is not
    evaluated on the way in; a quote is a barrier and does not survive, so the
    handler is handed the record itself.
    """

    __slots__ = (
        "_awaiting",
        "_committed",
        "_entered",
        "_foreign",
        "_lock",
        "_receipts",
        "_recovering",
        "_recovery_failed",
        "_running",
        "_space",
        "_subscription",
    )

    def __init__(self, space: Space, receipts: Space) -> None:
        """Bind one runner to its execution space and explicit receipt space."""
        if space._rt is not receipts._rt:
            msg = "a saga and its receipt space must belong to the same engine runtime"
            raise ValueError(msg)
        backing = getattr(receipts, "_backing", None)
        if backing is not None:
            requirements = (
                (Adder, "add"),
                (Enumerable, "enumerate"),
                (Remover, "remove"),
                (Transactional, "begin/commit/rollback"),
            )
            missing = [
                capability
                for protocol, capability in requirements
                if not isinstance(backing, protocol)
            ]
            if missing:
                listed = ", ".join(missing)
                msg = (
                    f"saga receipt space {receipts} cannot own recovery data: "
                    f"its {type(backing).__name__} provider lacks {listed}"
                )
                raise MettaError(
                    msg,
                    space=str(receipts),
                    capability="saga-receipt-store",
                )
        if receipts._rt.once(
            "seam:foreign_space(Space)",
            Space=receipts._space,
        ):
            writes = receipts._rt.must(
                "metta_writes(Space, Atomicity)",
                Space=receipts._space,
            )["Atomicity"]
            if writes != "transactional":
                msg = (
                    f"saga receipt space {receipts} declares writes {writes}; "
                    "receipts must commit and roll back with the forward "
                    "transaction, so declare transactional writes"
                )
                raise MettaError(
                    msg,
                    space=str(receipts),
                    capability="transactional-writes",
                )
        events = receipts._rt.must(
            "metta_event_capability(Space, Delivery, Order)",
            Space=receipts._space,
        )
        if (events["Delivery"], events["Order"]) != (
            "per-write-exactly",
            "ordered",
        ):
            msg = (
                f"saga receipt space {receipts} declares event delivery "
                f"{events['Delivery']} and order {events['Order']}; recovery "
                "requires per-write-exactly ordered post-commit events"
            )
            raise MettaError(
                msg,
                space=str(receipts),
                capability="per-write-exactly-ordered-events",
            )
        self._space = space
        self._receipts = receipts
        self._committed: list[_Obligation] = []
        self._foreign: list[Expression] = []
        self._awaiting: list[Expression] = []
        self._subscription: Subscription | None = None
        self._entered = False
        self._running = False
        self._recovering = False
        self._recovery_failed = False
        self._lock = threading.RLock()

    def __enter__(self) -> Self:
        """Start observing this runner's own post-commit receipt writes."""
        with self._lock:
            if self._entered:
                msg = "a Saga context cannot be entered twice"
                raise MettaError(msg)
            if self._committed or self._recovery_failed:
                msg = (
                    "this Saga has pending recovery; call rollback() until it "
                    "succeeds before entering a new scope"
                )
                raise MettaError(msg, operation="enter", space=str(self._space))
            if self._subscription is not None:
                msg = (
                    "this Saga still owns a subscription whose cancellation "
                    "failed; call close() before entering it again"
                )
                raise MettaError(msg, operation="enter", space=str(self._receipts))
            self._require_boundary("enter")
            self._subscription = self._receipts.subscribe(
                Expression([Symbol("did"), V.op, V.args, V.result]),
                self._observe_receipt,
            )
            self._entered = True
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        error: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Recover exceptional exits, then always retire the observer."""
        failures: list[BaseException] = []
        with self._lock:
            # Close the admission door before recovery. A concurrent run blocks
            # on this lock and then observes the closed scope instead of adding
            # an obligation after the reverse pass.
            self._entered = False
            if error is not None and not self._recovery_failed and self._committed:
                try:
                    self.rollback()
                except BaseException as rollback_error:  # noqa: BLE001 -- preserve control signals too
                    failures.append(rollback_error)
            elif error is None and self._recovery_failed:
                failures.append(
                    MettaError(
                        "the saga still has a failed recovery; retry rollback()",
                        operation="rollback",
                        space=str(self._space),
                    )
                )
            if error is None and not self._recovery_failed:
                # A completed context leaves its receipts as ordinary audit
                # data, but this runner's recovery scope is over.
                self._committed.clear()
        try:
            self.close()
        except BaseException as cancellation_error:  # noqa: BLE001 -- preserve both failures
            failures.append(cancellation_error)
        if failures:
            members = [error, *failures] if error is not None else failures
            msg = "the saga body and its recovery did not both complete"
            raise BaseExceptionGroup(msg, members) from None

    def close(self) -> None:
        """Cancel the receipt observer, retaining its handle if cancel fails."""
        with self._lock:
            subscription = self._subscription
            if subscription is None:
                return
            self._subscription = None
        try:
            subscription.cancel()
        except BaseException:
            with self._lock:
                if self._subscription is None:
                    self._subscription = subscription
            raise

    def _require_entered(self, operation: str) -> None:
        if not self._entered:
            msg = f"Saga.{operation}() requires an active 'with space.saga(receipts)' scope"
            raise MettaError(msg, operation=operation, space=str(self._space))

    def _require_boundary(self, operation: str) -> None:
        """Refuse ambient scopes that can invalidate receipt ordering."""
        if self._space._rt.once("metta_in_user_transaction"):
            msg = (
                f"Saga.{operation}() is already inside a user transaction; "
                "each saga step or compensation must be the durable boundary"
            )
            raise MettaError(msg, operation=operation, space=str(self._space))
        if speculative_enabled():
            msg = (
                f"Saga.{operation}() cannot run in a speculative scope, "
                "which discards writes after the receipt decision"
            )
            raise MettaError(msg, operation=operation, space=str(self._space))
        active_batches = _ACTIVE_BATCHES.get()
        if active_batches:
            names = ", ".join(sorted(active_batches))
            msg = (
                f"Saga.{operation}() cannot run while a batch is active on "
                f"{names}; a host operation could queue an effect whose receipt "
                "would commit first"
            )
            raise MettaError(msg, operation=operation, space=str(self._space))

    def _observe_receipt(self, event: Any) -> None:
        """Record a committed receipt event this runner did not write.

        Rollback matches the runner's committed multiset against what the
        receipt space actually holds, so a `(did ...)` atom somebody else put
        there is compensated as though this saga had performed it. The space
        promises per-write-exactly ordered post-commit events, and this is
        where that promise is checked.

        Membership is asked of the COMMITTED set, not the pending one the
        earlier shape of this guard consulted: the event arrives after the
        transaction's commit callback, which extends `_committed` and then
        clears `_awaiting`, so `event.atom in self._awaiting` was False for
        every legitimate receipt and a refusal built on it would have refused
        them all [measured 2026-08-26: two steps observed at
        `awaiting=0, committed=1` and `awaiting=0, committed=2`, each atom
        present in `_committed`].

        Refusing here would raise inside a post-commit observer, where an
        exception can cost the obligation it was protecting, so the foreign
        atom is recorded and the next boundary refuses.
        """
        if any(event.atom == obligation.atom for obligation in self._committed):
            return
        self._foreign.append(event.atom)

    def _require_own_receipts(self, operation: str) -> None:
        """Refuse once another writer's receipt has entered this journal."""
        if not self._foreign:
            return
        atoms = ", ".join(str(atom) for atom in self._foreign[:3])
        msg = (
            f"Saga.{operation}() cannot trust its journal: the receipt space "
            f"delivered {len(self._foreign)} committed receipt(s) this runner "
            f"did not write ({atoms}). Give each saga its own receipt space, "
            "or keep other writers out of this one; compensating a receipt "
            "this saga never earned would undo somebody else's work"
        )
        raise MettaError(msg, operation=operation, space=str(self._receipts))

    def run(self, target: Any) -> list[Atom | Undefined]:
        """Run one forward step and atomically commit its ``(did ...)`` data.

        A target with no answers is the engine's rollback outcome and returns
        ``[]``. An exception is re-raised after both its writes and pending
        receipts are discarded. The runner refuses an enclosing user
        transaction because its apparently committed receipt events would
        remain tentative until that outer scope ended, defeating per-step
        recovery order.
        """
        with self._lock:
            self._require_entered("run")
            if self._running:
                msg = "Saga.run() cannot re-enter the same runner"
                raise MettaError(msg, operation="run", space=str(self._space))
            if self._recovering:
                msg = "Saga.run() cannot start while this runner is recovering"
                raise MettaError(msg, operation="run", space=str(self._space))
            if self._recovery_failed:
                msg = (
                    "Saga.run() cannot add work while a failed recovery is pending; "
                    "retry rollback() first"
                )
                raise MettaError(msg, operation="run", space=str(self._space))
            self._require_boundary("run")
            self._running = True
            committed_start = len(self._committed)
            pending: list[_CapturedReceipt] = []
            answers: list[Atom | Undefined] = []

            def step() -> None:
                token = _begin_receipt_capture(pending)
                try:
                    target_wire = (
                        target
                        if isinstance(target, str)
                        else _to_atom(target).to_wire()
                    )

                    def capture_native(wire: list[Any]) -> None:
                        pending.append(self._native_receipt(wire))

                    answer_wires = self._space._rt.apply_must(
                        "metta_py_saga_eval_all",
                        self._space._space,
                        target_wire,
                        _select_receipt_operations,
                        capture_native,
                    )
                    answers.extend(_from_wire(wire) for wire in answer_wires)
                finally:
                    _end_receipt_capture(token)
                if not answers:
                    raise _EmptySagaStepError
                receipt_atoms = [captured.atom for captured in pending]
                self._awaiting.extend(receipt_atoms)
                if receipt_atoms:
                    self._receipts.add(*receipt_atoms)

            def committed() -> None:
                self._committed.extend(
                    _Obligation(captured.atom, journalled=True)
                    for captured in pending
                )
                self._awaiting.clear()

            def rolled_back() -> None:
                self._awaiting.clear()

            try:
                try:
                    self._transaction(step, committed, rolled_back)
                except _EmptySagaStepError:
                    self._recover_survivors(_unenlisted(pending))
                    return []
                except BaseException as step_error:  # a control signal recovers too
                    self._after_failed_step(step_error, committed_start, pending)
                    raise
                return answers
            finally:
                self._awaiting.clear()
                self._running = False

    def _native_receipt(self, wire: list[Any]) -> _CapturedReceipt:
        """Read one engine-side receipt the step's own transaction can undo."""
        receipt = _atom_from_wire(wire)
        if not isinstance(receipt, Expression):
            msg = f"native saga capture returned non-receipt {receipt}"
            raise EngineError(msg, space=str(self._space))
        if (
            receipt.children[1] == Symbol("remove-atom")
            and len(receipt.children) >= 3
            and isinstance(receipt.children[2], Expression)
            and len(receipt.children[2].children) >= 2
            and not _is_ground(receipt.children[2].children[1])
        ):
            msg = (
                "Saga.run refuses non-ground remove-atom because "
                "its receipt records the pattern, not the concrete "
                "occurrence selected for recovery"
            )
            raise MettaError(
                msg,
                atom=receipt,
                operation="remove-atom",
                space=str(self._space),
                capability="ground-destructive-receipt",
            )
        return _CapturedReceipt(receipt, enlisted=True)

    def _after_failed_step(
        self,
        step_error: BaseException,
        committed_start: int,
        pending: list[_CapturedReceipt],
    ) -> None:
        """Recover whatever a failed step performed without a durable receipt.

        A step whose obligation was never recorded rolled its enlisted work
        back, so only the host effects survived. A step whose obligation WAS
        recorded but whose receipts the receipt space does not hold performed
        every effect while its journal entry did not become durable: a receipt
        space with its own provider commits after the engine's durable
        decision, so a provider that refuses its commit leaves the work done
        and nothing to compensate from. Both are the same shape, and both take
        the immediate persist-then-compensate recovery below. Returning
        normally means the step's obligation stands and the caller re-raises.

        Before either, the step's OTHER participants are asked whether they
        made their writes durable, because the local database's outcome does
        not answer for them and this runner used to read it as though it did.
        """
        try:
            lost = self._lost_participants()
            if lost:
                self._retain_in_doubt(committed_start, pending, lost)
            if len(self._committed) == committed_start:
                survivors = _unenlisted(pending)
            else:
                positions = self._undurable(committed_start)
                if not positions:
                    return
                survivors = [self._committed[index].atom for index in positions]
                for index in reversed(positions):
                    del self._committed[index]
            self._recover_survivors(survivors)
        except BaseException as recovery_error:  # noqa: BLE001 -- preserve both
            msg = "the saga step and its immediate recovery both failed"
            raise BaseExceptionGroup(
                msg,
                [step_error, recovery_error],
            ) from None

    def _lost_participants(self) -> list[str]:
        """Providers, other than this journal, whose writes did not commit.

        Commit is single-coordinator and two-phase commit is out of scope, so
        a step's participants can end split between durable and rolled back.
        Only the coordinator knows which, and the answer arrives here rather
        than through the transaction's notifications, whose two callbacks
        carry no arguments [source: engine/metta/space_hooks.pl
        metta_foreign_writes_lost/2].
        """
        row = self._space._rt.once(
            "metta_foreign_writes_lost(Journal, Lost)",
            Journal=self._receipts._space,
        )
        return [str(space) for space in row["Lost"]] if row else []

    def _retain_in_doubt(
        self,
        committed_start: int,
        pending: list[_CapturedReceipt],
        lost: list[str],
    ) -> None:
        """Keep a partly applied step's obligations and refuse to guess.

        This is a MIXED OUTCOME in the sense the X/Open XA specification gives
        the word, "committed some work and rolled back other work", which a
        transaction manager reports rather than resolves: JTA raises
        HeuristicMixedException, "a heuristic decision was made and ... some
        relevant updates have been committed while others have been rolled
        back", and leaves the decision to the application [source:
        docs.oracle.com/cd/E17802_01/products/products/jta/jta-1_0_1B-doc/
        javax/transaction/HeuristicMixedException.html].

        The reason it cannot be resolved here is a granularity mismatch, not
        a missing channel: a receipt records the OPERATION, durability is a
        fact about a PARTICIPANT, and one operation can write to several.
        Compensating anyway can reverse an effect that never landed, and
        dropping the obligations can forget one that did. So the obligations
        are retained unjournalled, nothing is lost while the caller decides,
        and rollback() stays available as that decision.

        The remedy the refusal names is the transactional outbox: store the
        record in the same database, in the same transaction, as the entities
        it describes, and it exists if and only if they do [source:
        microservices.io/patterns/data/transactional-outbox.html, whose first
        force is "2PC is not an option"] - here, a receipt space backed by the
        store the effects go to.
        """
        del self._committed[committed_start:]
        self._committed.extend(
            _Obligation(captured.atom, journalled=False) for captured in pending
        )
        self._recovery_failed = True
        names = ", ".join(lost)
        receipts = ", ".join(str(captured.atom) for captured in pending[:3])
        msg = (
            f"this saga step ended with a mixed outcome: it committed in some "
            f"participants and not in {names}, which threw its writes away. "
            f"The step's receipt(s) ({receipts}) name the operations, not the "
            f"participant that carried each one, so compensating them now "
            f"could reverse an effect that never landed. They are kept as "
            f"obligations: decide against {names} and this receipt space, "
            f"then call rollback() to compensate all of them, or reverse the "
            f"durable half by hand. To stop the split happening, put the "
            f"receipts in the store the effects go to, so one commit covers "
            f"both (the transactional-outbox shape), or declare (writes "
            f"<space> best-effort) to accept partial application deliberately"
        )
        raise MettaError(
            msg,
            operation="run",
            space=str(self._receipts),
            capability="atomic-step",
        )

    def _undurable(self, start: int) -> list[int]:
        """Positions from ``start`` whose receipt the receipt space lacks.

        Earlier obligations have first claim on the stored occurrences, so the
        answer is about the newest step alone and a tampered older receipt
        still reaches the rollback preflight's own refusal.
        """
        available: Counter[Atom] = Counter(
            _canonical(atom)
            for atom in self._receipts.atoms()
            if isinstance(atom, Expression)
        )
        for earlier in self._committed[:start]:
            key = _canonical(earlier.atom)
            if available[key]:
                available[key] -= 1
        missing = []
        for index in range(start, len(self._committed)):
            key = _canonical(self._committed[index].atom)
            if available[key]:
                available[key] -= 1
            else:
                missing.append(index)
        return missing

    def _recover_survivors(self, survivors: list[Expression]) -> None:
        """Persist and reverse effects a failed step cannot undo itself.

        The effects already happened, so the obligation to reverse them is
        owed whatever the journal does. A recovery receipt that raises leaves
        its durable fate unknown either way, the local write may have landed
        and its provider commit refused, so the obligation is retained
        UNJOURNALLED and the reverse pass below matches it against a stored
        receipt if one turns up and compensates it without one otherwise.
        Raising here instead, which is what this did, dropped the obligation
        entirely and left the surviving external effect with nothing that
        could ever discharge it [tested:
        test_a_refused_recovery_receipt_still_compensates_the_effect_it_could_not_record].
        """
        if not survivors:
            return
        start = len(self._committed)

        def persist() -> None:
            self._awaiting.extend(survivors)
            self._receipts.add(*survivors)

        def committed() -> None:
            # Recorded from inside the notification, not after the call
            # returns, because the receipt space's own post-commit event
            # arrives BEFORE the call returns and _observe_receipt reads this
            # list to tell this runner's receipts from a stranger's. Recording
            # afterwards made the runner refuse its own recovery receipt as
            # one "this runner did not write".
            self._committed.extend(
                _Obligation(atom, journalled=True) for atom in survivors
            )
            self._awaiting.clear()

        def rolled_back() -> None:
            self._awaiting.clear()

        persistence_error: BaseException | None = None
        try:
            self._transaction(persist, committed, rolled_back)
        except BaseException as error:  # noqa: BLE001  -- a failed durable write, cancellation included, must leave the obligation retained and retryable
            persistence_error = error
            del self._committed[start:]
            self._committed.extend(
                _Obligation(atom, journalled=False) for atom in survivors
            )
        try:
            self._rollback_committed(start)
        except BaseException:
            self._recovery_failed = bool(self._committed[start:])
            raise
        if persistence_error is not None:
            raise persistence_error

    def _transaction(
        self,
        target: Any,
        committed: Any,
        rolled_back: Any,
    ) -> Any:
        """Run a callback with explicit durable-outcome notifications."""
        #The callback's answer is CAPTURED here rather than carried back
        #through janus, which converts whatever a callback returns and has no
        #conversion for an atom that is not a sequence: a body ending in
        #`add-atom` answers `true`, and janus raised "Grounded(True) is a leaf
        #atom and has no length" for the sibling metta_py_transaction/2 before
        #it stopped returning one [measured 2026-08-30]. Boxing keeps the value
        #AND keeps it off the boundary.
        answer: list[Any] = []

        def _capture() -> None:
            answer.append(target())

        try:
            row = self._space._rt.once(
                "metta_py_saga_transaction(F, C, B, R)",
                F=_capture,
                C=committed,
                B=rolled_back,
            )
        except MettaError as error:
            term = getattr(error.__cause__, "term", None)
            original = (
                self._space._rt._original_python_error(term, base=BaseException)
                if term is not None
                else None
            )
            if original is not None and original is not error:
                raise original from error
            raise
        if not row:
            msg = "the notified saga transaction failed without an outcome"
            raise EngineError(msg, space=str(self._space))
        return answer[0] if answer else None

    def _compensation_for(self, receipt: Expression) -> str:
        operation = str(receipt.children[1])
        compensation = self._space._rt.apply("metta_compensation", operation)
        if compensation is None:
            msg = (
                f"receipt {receipt} has no compensation; declare one with "
                f"space.compensates({operation!r}, <operation>) before rollback"
            )
            raise MettaError(
                msg,
                atom=receipt,
                operation=operation,
                capability="compensation",
            )
        compensation_name = str(compensation)
        if not self._space._rt.once(
            "metta_py_saga_compensation_callable(Space, Name)",
            Space=self._space._space,
            Name=compensation_name,
        ):
            msg = (
                f"receipt {receipt} names stale compensation "
                f"{compensation_name!r}; register a one-receipt callable "
                "visible from the saga space before rollback"
            )
            raise MettaError(
                msg,
                atom=receipt,
                operation=compensation_name,
                capability="compensation",
            )
        return compensation_name

    @staticmethod
    def _is_error_answer(answer: Atom) -> bool:
        return (
            isinstance(answer, Expression)
            and bool(answer.children)
            and answer.children[0] == Symbol("Error")
        )

    def rollback(self) -> None:
        """Compensate every committed receipt in reverse order.

        All compensation declarations are resolved before the first handler
        runs. Each handler then gets its own transaction. Recovery stops on
        the first failure and retains that receipt and every earlier one, so
        calling ``rollback()`` again retries from the same idempotent handler.

        The reverse sequential algorithm follows Garcia-Molina and Salem's
        backward recovery and Temporal's implementation at commit
        ``1b2ffb18bfa8a09d15ed63e3b0e9dfe50f9c5709``.
        """
        with self._lock:
            # Before the reverse pass, not after: compensation is the one
            # operation a foreign receipt turns destructive, and by the time a
            # handler has run its effect is already undone.
            self._require_own_receipts("rollback")
            if not self._entered and not self._committed:
                self._require_entered("rollback")
            if self._running:
                msg = "Saga.rollback() cannot run inside a forward saga step"
                raise MettaError(
                    msg,
                    operation="rollback",
                    space=str(self._space),
                )
            if self._recovering:
                msg = "Saga.rollback() cannot re-enter recovery"
                raise MettaError(
                    msg,
                    operation="rollback",
                    space=str(self._space),
                )
            self._require_boundary("rollback")
            self._recovering = True
            try:
                self._rollback_committed(0)
            except BaseException:
                # A post-commit publisher may raise after the transaction's
                # durable notification has already retired the last receipt.
                # Retry is pending only while an obligation actually remains.
                self._recovery_failed = bool(self._committed)
                raise
            else:
                self._recovery_failed = False
            finally:
                self._recovering = False

    def _rollback_committed(self, start: int = 0) -> None:  # noqa: C901  -- recovery reads as one ordered ledger walk
        """Run one preflighted reverse plan while the runner lock is held.

        Journalled obligations claim their stored occurrences first. An
        unjournalled one takes what is left, so it can never remove the very
        receipt another obligation was preflighted against, and when nothing
        is left it compensates with no receipt to retire: the effect happened
        and the missing journal entry is the reason this obligation exists.
        """
        available: dict[Atom, list[Expression]] = {}
        for atom in self._receipts.atoms():
            if isinstance(atom, Expression):
                available.setdefault(_canonical(atom), []).append(atom)
        obligations = self._committed[start:]
        stored: list[Expression | None] = [None] * len(obligations)
        missing: Counter[Atom] = Counter()
        missing_examples: dict[Atom, Expression] = {}
        for position, obligation in enumerate(obligations):
            if not obligation.journalled:
                continue
            key = _canonical(obligation.atom)
            candidates = available.get(key)
            if candidates:
                stored[position] = candidates.pop()
            else:
                missing[key] += 1
                missing_examples.setdefault(key, obligation.atom)
        if missing:
            key, count = next(iter(missing.items()))
            missing_receipt = missing_examples[key]
            msg = (
                f"saga recovery is missing {count} committed occurrence(s) "
                f"of receipt {missing_receipt}; restore every receipt before any "
                "compensation runs"
            )
            raise MettaError(
                msg,
                atom=missing_receipt,
                operation="rollback",
                space=str(self._receipts),
                capability="receipt-multiplicity",
            )
        for position, obligation in enumerate(obligations):
            if obligation.journalled:
                continue
            candidates = available.get(_canonical(obligation.atom))
            if candidates:
                stored[position] = candidates.pop()
        plan: list[tuple[Expression, Expression | None, Expression, str]] = []
        for obligation, receipt in reversed(
            list(zip(obligations, stored, strict=True))
        ):
            record = obligation.atom if receipt is None else receipt
            plan.append(
                (obligation.atom, receipt, record,
                 self._compensation_for(record))
            )
        for snapshot, receipt, record, compensation in plan:
            target = Expression(
                [
                    Symbol("once"),
                    Expression(
                        [
                            Symbol(compensation),
                            Expression([Symbol("quote"), record]),
                        ]
                    ),
                ]
            )

            def recover(
                current_receipt: Expression | None = receipt,
                current_target: Expression = target,
            ) -> None:
                if current_receipt is not None and not self._receipts.remove(
                    current_receipt
                ):
                    msg = (
                        f"committed receipt {current_receipt} disappeared before "
                        "its compensation began"
                    )
                    raise EngineError(
                        msg,
                        atom=current_receipt,
                        space=str(self._receipts),
                    )
                outcomes = self._space.eval_status(current_target)
                failed = not outcomes or any(
                    status != "value"
                    or answer is None
                    or isinstance(answer, Undefined)
                    or self._is_error_answer(answer)
                    for status, answer in outcomes
                )
                if failed:
                    raise _CompensationFailedError

            def committed(current_snapshot: Expression = snapshot) -> None:
                self._pop_recovered(current_snapshot)

            def rolled_back() -> None:
                return

            token = _suspend_receipt_capture()
            try:
                try:
                    self._transaction(recover, committed, rolled_back)
                except _CompensationFailedError:
                    msg = (
                        f"compensation {compensation} failed for receipt "
                        f"{record}; the receipt remains pending and the "
                        "idempotent handler may be retried with "
                        "Saga.rollback()"
                    )
                    raise MettaError(
                        msg,
                        atom=record,
                        operation=compensation,
                        capability="compensation",
                    ) from None
            finally:
                _end_receipt_capture(token)

    def _pop_recovered(self, receipt: Expression) -> None:
        """Retire the one LIFO obligation whose transaction committed."""
        if (
            not self._committed
            or _canonical(self._committed[-1].atom) != _canonical(receipt)
        ):
            msg = "the saga receipt order changed while rollback was running"
            raise EngineError(msg, atom=receipt, space=str(self._receipts))
        self._committed.pop()
