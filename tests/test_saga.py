"""Purpose: prove committed receipts and reverse saga compensation.

Guarantees:
  - only committed writesState-or-stronger answers leave ordinary queryable
    ``(did op args result)`` atoms [tested:
    test_committed_effects_leave_queryable_receipts_and_failed_steps_leave_none,
    test_a_discarded_step_runs_no_compensation;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - rollback preflights the complete receipt multiset and handler catalog,
    then compensates each occurrence in reverse commit order [tested:
    test_saga_compensates_in_reverse_commit_order,
    test_saga_preflights_missing_compensations_before_undo,
    test_duplicate_receipts_remain_distinct_recovery_obligations;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - a failed compensation retains its receipt and can be retried without
    repeating already committed recovery [tested:
    test_a_failed_compensation_can_be_retried_without_losing_its_receipt;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - structural operations cannot publish recovery policy and every host
    dispatch transport records the answer identity it actually committed
    [tested: test_a_structural_operation_cannot_declare_a_compensation,
    test_every_effectful_dispatch_shape_leaves_one_committed_receipt,
    test_first_compiled_call_journals_only_its_semantic_effects,
    test_a_pure_native_form_cannot_journal_its_runtime_helper;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - a provider-owned receipt space commits each receipt inside its own step,
    and a refused provider commit recovers the work it could not journal
    rather than standing as an obligation with no receipt [tested:
    test_a_provider_receipt_space_commits_the_receipt_before_recovery_reads_it,
    test_a_refused_provider_commit_recovers_the_step_it_could_not_journal;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - receipt instrumentation installs and retires as one set, so no step can
    leave a wrapper or a receipt sink behind [tested:
    test_a_refused_wrapper_installation_leaves_no_saga_instrumentation,
    test_saga_teardown_retires_every_wrapper_past_a_missing_one;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
"""

from __future__ import annotations

import uuid
from collections import Counter

import pytest

from metta import Atom, Expression, S, Symbol, V, ground
from metta.errors import MettaError
from metta.foreign import SpaceProvider
from metta.vocabularies import Atomicity


def _unique(prefix: str) -> str:
    """Return one source-readable operation name unique to this process."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _quoted_receipt(value: Atom) -> Expression:
    """Extract the receipt from the runner's explicit quote boundary."""
    assert isinstance(value, Expression)
    assert len(value.children) == 2
    assert value.children[0] == Symbol("quote")
    receipt = value.children[1]
    assert isinstance(receipt, Expression)
    assert receipt.children[0] == Symbol("did")
    return receipt


def _remove_declaration(space, declaration: Atom | None) -> None:
    """Remove one test-owned catalog row if it was installed."""
    if declaration is not None:
        space._at("&metta").remove(declaration)


def _unregister(space, *names: str) -> None:
    """Remove every test-owned operation, preserving the first failure."""
    for name in names:
        try:
            space.unregister_op(name)
        except KeyError:
            pass


def _raise_test_error(error: BaseException) -> None:
    """Raise one intentional body or observer failure without lint ambiguity."""
    raise error


class _Ledger(SpaceProvider):
    """A transactional receipt store that records its own commit protocol.

    ``refusals`` is how many commits refuse before one succeeds, which is what
    an external journal does when its device is briefly unavailable. A refusing
    commit restores the rows the transaction began with, the behaviour a store
    that cannot land its batch owes its caller.
    """

    def __init__(self, refusals: int = 0) -> None:
        """Start empty, outside any transaction, with this refusal budget."""
        self.rows: list[Atom] = []
        self.trace: list[object] = []
        self.refusals = refusals
        self._staged: list[Atom] | None = None

    def delivers(self) -> tuple[str, str]:
        """Every write reaches this store through the engine, in order."""
        return ("per-write-exactly", "ordered")

    def begin(self) -> None:
        """Stage the rows this transaction may have to restore."""
        self.trace.append("begin")
        self._staged = list(self.rows)

    def commit(self) -> None:
        """Land the staged batch, or spend one refusal restoring the rows."""
        self.trace.append("commit")
        staged, self._staged = self._staged, None
        if self.refusals:
            self.refusals -= 1
            self.rows = list(staged or [])
            message = "ledger commit refused"
            raise RuntimeError(message)

    def rollback(self) -> None:
        """Restore the rows this transaction began with."""
        self.trace.append("rollback")
        staged, self._staged = self._staged, None
        if staged is not None:
            self.rows = staged

    def add(self, atom: Atom) -> None:
        """Append one receipt to the uncommitted rows."""
        self.trace.append(("add", atom))
        self.rows.append(atom)

    def remove(self, atom: Atom) -> bool:
        """Retire one stored occurrence, answering whether it was there."""
        self.trace.append(("remove", atom))
        if atom not in self.rows:
            return False
        self.rows.remove(atom)
        return True

    def atoms(self):
        """Enumerate a stable copy of the rows."""
        return iter(list(self.rows))


def _ledger_space(metta, ledger: _Ledger):
    """Register one ledger as a transactional receipt space."""
    receipts = metta.metta.space(backing=ledger)
    receipts.writes(Atomicity.transactional)
    return receipts


def test_committed_effects_leave_queryable_receipts_and_failed_steps_leave_none(
    metta,
):
    """The receipt write shares the forward step's transaction outcome."""
    space = metta._new_space()
    receipts = metta._new_space()
    try:
        with space.saga(receipts) as saga:
            assert saga.run("(add-atom &self (kept yes))") == [Expression()]
            committed = receipts.atoms()
            assert len(committed) == 1
            assert committed[0].children[0:2] == (
                Symbol("did"),
                Symbol("add-atom"),
            )

            assert saga.run(
                "(progn (add-atom &self (rolled-back no)) (empty))"
            ) == []
            assert receipts.atoms() == committed

        assert space.atoms() == [S.kept(S.yes)]
        assert list(receipts.match(S.did(V.op, V.args, V.result)))
        assert list(space.match(S.rolled_back(V.value))) == []
    finally:
        receipts.drop()
        space.drop()


def test_saga_compensates_in_reverse_commit_order(metta):
    """A successful reverse plan removes each receipt after its handler."""
    operation = _unique("saga-forward")
    compensation = _unique("saga-reverse")
    order = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        receipt = _quoted_receipt(quoted)
        order.append(receipt.children[2].children[0])
        return S.done

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(RuntimeError, match="abort the saga"):
            with space.saga(receipts) as saga:
                assert saga.run(f"({operation} 1)") == [1]
                assert saga.run(f"({operation} 2)") == [2]
                _raise_test_error(RuntimeError("abort the saga"))
        assert order == [2, 1]
        assert receipts.atoms() == []
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_a_discarded_step_runs_no_compensation(metta):
    """A no-answer transaction neither journals nor creates recovery work."""
    compensation = _unique("saga-discard-reverse")
    calls = []

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        return S.done

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates("add-atom", compensation)
        with pytest.raises(RuntimeError, match="discard the saga"):
            with space.saga(receipts) as saga:
                assert saga.run(
                    "(progn (add-atom &self (discarded yes)) (empty))"
                ) == []
                _raise_test_error(RuntimeError("discard the saga"))
        assert calls == []
        assert receipts.atoms() == []
        assert list(space.match(S.discarded(V.value))) == []
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, compensation)
        receipts.drop()
        space.drop()


def test_saga_preflights_missing_compensations_before_undo(metta):
    """One missing handler prevents every earlier handler from running."""
    recoverable = _unique("saga-recoverable")
    missing = _unique("saga-missing")
    compensation = _unique("saga-preflight-reverse")
    calls = []

    @metta.op(name=recoverable, effect="writesState")
    def first(value: int) -> int:
        return value

    @metta.op(name=missing, effect="writesState")
    def second(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        return S.done

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(recoverable, compensation)
        with pytest.raises(BaseExceptionGroup) as caught:
            with space.saga(receipts) as saga:
                saga.run(f"({recoverable} 1)")
                saga.run(f"({missing} 2)")
                _raise_test_error(RuntimeError("trigger recovery"))
        assert any(
            isinstance(error, MettaError)
            and error.capability == "compensation"
            for error in caught.value.exceptions
        )
        assert calls == []
        assert len(receipts.atoms()) == 2
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, recoverable, missing, compensation)
        receipts.drop()
        space.drop()


def test_a_failed_compensation_can_be_retried_without_losing_its_receipt(
    metta,
):
    """Recovery progress advances only after the handler transaction commits."""
    operation = _unique("saga-retry-forward")
    compensation = _unique("saga-retry-reverse")
    attempts = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        attempts.append(_quoted_receipt(quoted))
        if len(attempts) == 1:
            _raise_test_error(RuntimeError("transient compensation failure"))
        return S.done

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    saga = space.saga(receipts)
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(BaseExceptionGroup):
            with saga:
                saga.run(f"({operation} 7)")
                _raise_test_error(RuntimeError("trigger recovery"))
        assert len(attempts) == 1
        assert len(receipts.atoms()) == 1

        saga.rollback()
        assert len(attempts) == 2
        assert receipts.atoms() == []
    finally:
        saga.close()
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_a_structural_operation_cannot_declare_a_compensation(metta):
    """Compensation policy is meaningful only at the receipt threshold."""
    operation = _unique("saga-pure")
    compensation = _unique("saga-unused-reverse")

    @metta.op(name=operation, effect="pureStructural")
    def structural(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(_quoted):
        return S.done

    space = metta._new_space()
    try:
        with pytest.raises(MettaError, match="writesState or oracleIO"):
            space.compensates(operation, compensation)
        assert list(
            space._at("&metta").match(
                S.compensates(S[operation], V.compensation)
            )
        ) == []
    finally:
        _unregister(metta, operation, compensation)
        space.drop()


def test_duplicate_receipts_remain_distinct_recovery_obligations(metta):
    """Two identical commits produce two identical atoms and two undo calls."""
    operation = _unique("saga-duplicate")
    compensation = _unique("saga-duplicate-reverse")
    calls = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        return S.done

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(RuntimeError):
            with space.saga(receipts) as saga:
                saga.run(f"({operation} 4)")
                saga.run(f"({operation} 4)")
                counts = Counter(receipts.atoms())
                assert list(counts.values()) == [2]
                _raise_test_error(RuntimeError("recover duplicates"))
        assert len(calls) == 2
        assert calls[0] == calls[1]
        assert receipts.atoms() == []
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_missing_receipt_multiplicity_refuses_before_any_compensation(metta):
    """Recovery validates every committed occurrence before the first undo."""
    operation = _unique("saga-multiplicity")
    compensation = _unique("saga-multiplicity-reverse")
    calls = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        return S.done

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(BaseExceptionGroup) as caught:
            with space.saga(receipts) as saga:
                saga.run(f"({operation} 1)")
                saga.run(f"({operation} 2)")
                assert receipts.remove(receipts.atoms()[0])
                _raise_test_error(RuntimeError("recover with one receipt missing"))
        assert any(
            isinstance(error, MettaError)
            and error.capability == "receipt-multiplicity"
            for error in caught.value.exceptions
        )
        assert calls == []
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_a_nondeterministic_compensation_runs_once_per_receipt(metta):
    """One receipt invokes one handler even when that handler can yield twice."""
    operation = _unique("saga-once")
    compensation = _unique("saga-once-reverse")
    calls = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        yield S.done
        yield S.duplicate

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(RuntimeError):
            with space.saga(receipts) as saga:
                saga.run(f"({operation} 9)")
                _raise_test_error(RuntimeError("recover one occurrence"))
        assert len(calls) == 1
        assert receipts.atoms() == []
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_postcommit_control_signal_still_recovers_the_committed_receipt(metta):
    """Bookkeeping follows the durable outcome when an earlier watcher aborts."""
    operation = _unique("saga-postcommit")
    compensation = _unique("saga-postcommit-reverse")
    calls = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        return S.done

    def interrupt(_event):
        _raise_test_error(KeyboardInterrupt("postcommit watcher interrupted"))

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    blocker = receipts.subscribe(
        S.did(V.op, V.args, V.result), interrupt, on="add"
    )
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(KeyboardInterrupt):
            with space.saga(receipts) as saga:
                saga.run(f"({operation} 5)")
        assert len(calls) == 1
        assert receipts.atoms() == []
    finally:
        blocker.cancel()
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_postcommit_removal_failure_does_not_repeat_compensation(metta):
    """A committed undo retires its obligation before its event error escapes."""
    operation = _unique("saga-remove-event")
    compensation = _unique("saga-remove-event-reverse")
    calls = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        return S.done

    def interrupt(_event):
        _raise_test_error(
            KeyboardInterrupt("receipt removal watcher interrupted")
        )

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    blocker = receipts.subscribe(
        S.did(V.op, V.args, V.result), interrupt, on="remove"
    )
    saga = space.saga(receipts)
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(BaseExceptionGroup):
            with saga:
                saga.run(f"({operation} 6)")
                _raise_test_error(
                    RuntimeError("recover and interrupt publication")
                )
        assert len(calls) == 1
        assert receipts.atoms() == []

        with saga:
            saga.rollback()
        assert len(calls) == 1
    finally:
        saga.close()
        blocker.cancel()
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_every_effectful_dispatch_shape_leaves_one_committed_receipt(metta):
    """Deterministic, many, relational, inverse, and raw answers are journaled."""
    deterministic = _unique("saga-det")
    many = _unique("saga-many")
    relational = _unique("saga-rel")
    inverse = _unique("saga-inverse")
    raw = _unique("saga-raw")
    opaque = object()

    @metta.op(name=deterministic, effect="writesState")
    def det(value: int) -> int:
        return value + 1

    @metta.op(name=many, effect="writesState")
    def several(value: int):
        yield value
        yield value + 1

    @metta.op(name=relational, effect="writesState")
    def relation(origin, destination):
        del origin, destination
        yield (S.paris, S.lyon)

    metta.op(
        lambda value: value * 2,
        name=inverse,
        effect="writesState",
        inverse=lambda result: result // 2,
    )

    @metta.op(name=raw, transport="raw", effect="writesState")
    def raw_identity(value):
        return value

    space = metta._new_space()
    receipts = metta._new_space()
    try:
        with space.saga(receipts) as saga:
            assert saga.run(f"({deterministic} 1)") == [2]
            assert saga.run(f"({many} 3)") == [3, 4]
            assert saga.run(
                f"(let ({relational} $from $to) () (route $from $to))"
            ) == [S.route(S.paris, S.lyon)]
            assert saga.run(
                f"(let ({inverse} $value) 8 (answer $value))"
            ) == [S.answer(4)]
            assert saga.run(S[raw](ground(opaque)))[0].value is opaque

        rows = receipts.atoms()
        assert len(rows) == 6
        counts = Counter(str(row.children[1]) for row in rows)
        assert counts == Counter(
            {
                deterministic: 1,
                many: 2,
                relational: 1,
                inverse: 1,
                raw: 1,
            }
        )
        raw_receipt = next(
            row for row in rows if row.children[1] == Symbol(raw)
        )
        assert raw_receipt.children[2].children[0].value is opaque
        assert raw_receipt.children[3].value is opaque
    finally:
        _unregister(metta, deterministic, many, relational, inverse, raw)
        receipts.drop()
        space.drop()


def test_first_compiled_call_journals_only_its_semantic_effects(metta):
    """Lazy compilation cannot leak internal include calls into recovery data."""
    leaf = _unique("saga-compiled-leaf")
    definition = _unique("saga-compiled-definition")

    @metta.op(name=leaf, effect="writesState")
    def forward(value: int) -> int:
        return value

    space = metta._new_space()
    receipts = metta._new_space()
    try:
        space.run(
            f"(= ({definition} $x) "
            f"(progn (add-atom &self (saga-compiled-seen $x)) ({leaf} $x)))"
        )
        with space.saga(receipts) as saga:
            assert saga.run(f"({definition} 3)") == [3]
        rows = receipts.atoms()
        assert [row.children[1] for row in rows] == [
            Symbol("add-atom"),
            Symbol(leaf),
        ]
        assert all(row.children[1] != Symbol("include") for row in rows)
    finally:
        receipts.drop()
        space.drop()
        _unregister(metta, leaf)


def test_a_pure_native_form_cannot_journal_its_runtime_helper(metta):
    """Semantic source operations, not Prolog implementation calls, journal."""
    space = metta._new_space()
    receipts = metta._new_space()
    try:
        with space.saga(receipts) as saga:
            assert saga.run("(filter-atom (1 2 3) $x (> $x 1))") == [
                Expression(2, 3)
            ]
        assert receipts.atoms() == []
    finally:
        receipts.drop()
        space.drop()


def test_saga_refuses_transaction_speculation_and_batch_boundaries(metta):
    """A saga step owns its durable boundary and cannot be nested in one."""
    operation = _unique("saga-boundary")

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    space = metta._new_space()
    receipts = metta._new_space()
    try:
        with space.saga(receipts) as saga:
            with pytest.raises(MettaError, match="user transaction"):
                space.transaction(lambda: saga.run(f"({operation} 1)"))
            with pytest.raises(MettaError, match="speculative"):
                with space.speculative():
                    saga.run(f"({operation} 2)")
            with pytest.raises(MettaError, match="batch"):
                with space.batch():
                    saga.run(f"({operation} 3)")
        assert receipts.atoms() == []
    finally:
        _unregister(metta, operation)
        receipts.drop()
        space.drop()


def test_a_provider_receipt_space_commits_the_receipt_before_recovery_reads_it(
    metta,
):
    """A provider journal lands each receipt inside the step that wrote it."""
    operation = _unique("saga-ledger-forward")
    compensation = _unique("saga-ledger-reverse")
    order = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        order.append(_quoted_receipt(quoted))
        return S.done

    ledger = _Ledger()
    receipts = _ledger_space(metta, ledger)
    space = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(RuntimeError, match="recover through the ledger"):
            with space.saga(receipts) as saga:
                assert saga.run(f"({operation} 3)") == [3]
                assert [str(row) for row in ledger.rows] == [
                    f"(did {operation} (3) 3)"
                ]
                _raise_test_error(RuntimeError("recover through the ledger"))
        assert len(order) == 1
        assert ledger.rows == []
        receipt = order[0]
        assert ledger.trace == [
            "begin",
            ("add", receipt),
            "commit",
            "begin",
            ("remove", receipt),
            "commit",
        ]
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_a_refused_provider_commit_recovers_the_step_it_could_not_journal(metta):
    """A receipt that never became durable is never a standing obligation."""
    operation = _unique("saga-refused-forward")
    compensation = _unique("saga-refused-reverse")
    order = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        order.append(_quoted_receipt(quoted))
        return S.done

    ledger = _Ledger(refusals=1)
    receipts = _ledger_space(metta, ledger)
    space = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(RuntimeError, match="ledger commit refused"):
            with space.saga(receipts) as saga:
                saga.run(f"({operation} 5)")
        # The step performed its effect, so it is compensated at once rather
        # than recorded against a journal entry the ledger did not keep.
        assert len(order) == 1
        assert ledger.rows == []
        assert ledger.trace.count("commit") == 3
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()


def test_a_refused_wrapper_installation_leaves_no_saga_instrumentation(metta):
    """One step's receipt wrappers install as a whole set or not at all."""
    space = metta._new_space()
    try:
        state = space._rt.must(
            """
            catch(( metta_py_saga_wrap_all(
                        [spaces:'add-atom'/3, not_a_predicate_indicator],
                        [], _Wrapped),
                    Outcome = installed ),
                  _Error,
                  Outcome = refused),
            ( catch(unwrap_predicate(spaces:'add-atom'/3, metta_saga_receipt),
                    _, fail)
            -> Wrapper = present ; Wrapper = absent ),
            ( nb_current('$metta_saga_receipt_sink', _)
            -> Sink = present ; Sink = absent )
            """
        )
        assert state["Outcome"] == "refused"
        assert state["Wrapper"] == "absent"
        assert state["Sink"] == "absent"
    finally:
        space.drop()


def test_saga_teardown_retires_every_wrapper_past_a_missing_one(metta):
    """A wrapper somebody else already retired cannot strand the rest."""
    space = metta._new_space()
    try:
        state = space._rt.must(
            """
            metta_py_saga_wrap_all(
                [spaces:'add-atom'/3, spaces:'remove-atom'/3], [], _Wrapped),
            _Wrapped = [_First|_],
            unwrap_predicate(_First, metta_saga_receipt),
            metta_py_saga_capture_end(_Wrapped),
            ( catch(unwrap_predicate(spaces:'add-atom'/3, metta_saga_receipt),
                    _, fail)
            -> Adder = present ; Adder = absent ),
            ( catch(unwrap_predicate(spaces:'remove-atom'/3,
                                     metta_saga_receipt),
                    _, fail)
            -> Remover = present ; Remover = absent ),
            ( nb_current('$metta_saga_receipt_sink', _)
            -> Sink = present ; Sink = absent )
            """
        )
        assert state["Adder"] == "absent"
        assert state["Remover"] == "absent"
        assert state["Sink"] == "absent"
    finally:
        space.drop()


def test_a_receipt_this_saga_never_wrote_refuses_before_it_is_compensated(metta):
    """Another writer's `(did ...)` atom must not be undone as this saga's own.

    Rollback matches the runner's committed multiset against what the receipt
    space holds, so a receipt somebody else committed there would be handed to
    a compensation handler and undo work this saga never performed. The
    post-commit observer records it and rollback refuses before the first
    handler runs.
    """
    operation = _unique("saga-foreign")
    compensation = _unique("saga-foreign-reverse")
    calls = []

    @metta.op(name=operation, effect="writesState")
    def forward(value: int) -> int:
        return value

    @metta.op(name=compensation, effect="writesState")
    def reverse(quoted):
        calls.append(_quoted_receipt(quoted))
        return S.done

    space = metta._new_space()
    receipts = metta._new_space()
    declaration = None
    try:
        declaration = space.compensates(operation, compensation)
        with pytest.raises(BaseExceptionGroup) as raised:
            with space.saga(receipts) as saga:
                saga.run(f"({operation} 7)")
                # A second writer commits into the same receipt space. It is
                # shaped like a receipt and matches the runner's subscription,
                # which is exactly why it would otherwise be compensated.
                receipts.add(S.did(S.someone_else, Expression([]), Expression()))
                _raise_test_error(RuntimeError("trigger recovery"))
        group = raised.value
        assert any(
            isinstance(member, MettaError)
            and "did not write" in str(member)
            for member in group.exceptions
        ), group.exceptions
        # The refusal comes BEFORE the reverse pass, so nothing was undone.
        assert calls == []
    finally:
        _remove_declaration(space, declaration)
        _unregister(metta, operation, compensation)
        receipts.drop()
        space.drop()
