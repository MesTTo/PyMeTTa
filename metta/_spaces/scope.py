"""Purpose: carry the task-local algebra selected by ``with metta.under(...)``.

Guarantees:
  - algebra and demand cross internal evaluation without changing answer shape
    [tested: sh extensions/python/test.sh
    tests/ch06_many_answers/test_evaluation_context.py -n 0; commit=54cb2eee69c42c1ae685643cbe2578f8d617a265]
  - an omitted per-call carrier reads the innermost scope, an explicit value
    wins, and exit restores the previous carrier even after an exception
    [tested: test_scoped_under_is_task_local_and_explicit_under_wins;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - a transaction body is named to the engine by a ticket `transaction_body`
    resolves, never crossed as a callable, and a body's own exception comes
    back as itself from a boundary that holds no engine record, so hundreds of
    rolled-back bodies leave no frame, handle or cell behind once the
    reclamation barrier runs [tested: test_aborted_births_leave_nothing_behind,
    test_a_callback_exception_is_released_at_the_reclamation_barrier;
    commit=WORKTREE]
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, cast, overload

import metta._spaces.cursor as _spaces_cursor_module
import metta._spaces.execution as _spaces_execution_module
import metta.doors as _doors
from metta._atoms.designation import _P, _R, _UNSET, _SpaceId
from metta._atoms.factories import Atom, Expression, Symbol, Undefined, _to_atom
from metta._binding.runtime import Runtime, original_exception
from metta._errors.errors import EngineError, MettaError
from metta._lazy import lazy

_SCOPED_UNDER: ContextVar[Any | None] = ContextVar(
    "metta_scoped_under", default=None
)

@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """The selected algebra and the demand carried by one evaluation."""

    algebra: str
    limit: int | None = None
    order: str | None = None

    def to_wire(self) -> list[Any]:
        """Encode the engine's evaluation_context term fields."""
        return [self.algebra, self.limit or 0, self.order or "none"]

class ScopedUnder:
    """A dynamic algebra scope with ContextVar task and thread semantics."""

    __slots__ = ("_carrier", "_token")

    def __init__(self, carrier: Any) -> None:
        if carrier is None:
            msg = "under() needs an algebra carrier, not None"
            raise TypeError(msg)
        self._carrier = carrier
        self._token: Any = None

    def __enter__(self) -> Self:
        self._token = _SCOPED_UNDER.set(self._carrier)
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        _SCOPED_UNDER.reset(self._token)

def selected(explicit: Any = _UNSET) -> Any | None:
    """Resolve one call's explicit carrier before its surrounding scope."""
    if explicit is _UNSET:
        return _SCOPED_UNDER.get()
    if explicit is None:
        msg = "under= needs an algebra carrier, not None"
        raise TypeError(msg)
    return explicit

__all__ = ["ScopedUnder"]

_SCOPED_LIMITS: ContextVar[tuple[float | None, int | None, int | None]] = ContextVar(
    "metta_scoped_limits", default=(None, None, None)
)

class ScopedLimits:
    """The with-block m.limits() answers: sets the scoped defaults on
    entry, restores the previous scope on exit, exceptions included.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(
        self,
        timeout: float | None,
        inferences: int | None,
        stack: int | None,
    ) -> None:
        _spaces_cursor_module._require_bound(timeout, "timeout", (int, float), "seconds as a number")
        _spaces_cursor_module._require_bound(inferences, "inferences", (int,), "a positive int")
        _spaces_cursor_module._require_bound(stack, "stack", (int,), "a positive byte count")
        self._value = (timeout, inferences, stack)
        self._token: Any = None

    def __enter__(self) -> Self:
        self._token = _SCOPED_LIMITS.set(self._value)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _SCOPED_LIMITS.reset(self._token)

def _limits(
    timeout: float | None,
    inferences: int | None,
    stack: int | None = None,
) -> tuple[float, int, int] | None:
    """Validate the per-call bounds into the shim's ``-1 = none`` triple.
    A bound the call did not name falls back to the scoped default
    m.limits() set, which is how one with-block replaces a parameter
    forest while every per-call kwarg still overrides.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if timeout is None or inferences is None or stack is None:
        scoped_timeout, scoped_inferences, scoped_stack = _SCOPED_LIMITS.get()
        if timeout is None:
            timeout = scoped_timeout
        if inferences is None:
            inferences = scoped_inferences
        if stack is None:
            stack = scoped_stack
    if timeout is inferences is stack is None:
        return None
    _spaces_cursor_module._require_bound(timeout, "timeout", (int, float), "seconds as a number")
    _spaces_cursor_module._require_bound(inferences, "inferences", (int,), "a positive int")
    _spaces_cursor_module._require_bound(stack, "stack", (int,), "a positive byte count")
    return (
        -1.0 if timeout is None else float(timeout),
        -1 if inferences is None else int(inferences),
        -1 if stack is None else int(stack),
    )

def _apply_limited(
    runtime: Runtime,
    limits: tuple[float, int, int],
    predicate: str,
    inputs: list[Any],
) -> Any:
    """Apply the preserved /5 call or stack-aware /6 call as required."""
    seconds, steps, stack = limits
    if stack < 0:
        return runtime.apply_must(
            "metta_py_limited", seconds, steps, predicate, inputs
        )
    return runtime.apply_must(
        "metta_py_limited", seconds, steps, stack, predicate, inputs
    )

class _Assuming:
    """Facts scoped to a with-block; see MeTTa.assuming."""

    __slots__ = ("_facts", "_space")

    def __init__(self, space: _root.Space, facts: list[Atom]) -> None:
        self._space = space
        self._facts = facts

    def __enter__(self) -> _root.Space:
        self._space.add(*self._facts)
        return self._space

    def __exit__(self, exc_type, exc, tb) -> None:
        failures: list[BaseException] = []
        for fact in self._facts:
            try:
                self._space.remove(fact)
            except BaseException as failure:  # noqa: BLE001 -- every hypothetical is removed before any cleanup failure leaves
                failures.append(failure)
        if len(failures) == 1:
            raise failures[0]
        if failures:
            msg = "removing assumed facts failed"
            raise BaseExceptionGroup(msg, failures)

_EMPTY_BATCHES: dict[str, list] = {}  # never mutated; entering copies

_ACTIVE_BATCHES: ContextVar[dict[str, list]] = ContextVar(
    "metta_active_batches", default=_EMPTY_BATCHES
)

def _refuse_in_batch(space_name: str, operation: str) -> None:
    """Refuse an operation that would order around pending batched adds."""
    if space_name in _ACTIVE_BATCHES.get():
        msg = (
            f"{operation}() on {space_name} inside its own batch block "
            f"would silently order around the adds the block is holding; "
            f"leave the `with m.batch():` block first"
        )
        raise MettaError(
            msg
        )

class _Batch:
    """The write collector m.batch() answers; see its docstring for the
    stated edges (reads see the pre-batch space, remove and clear
    refuse, an exception discards).
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_pending", "_space", "_token")

    def __init__(self, space: _root.Space) -> None:
        self._space = space
        self._pending: list[Any] = []
        self._token: Any = None

    def __enter__(self) -> Self:
        current = _ACTIVE_BATCHES.get()
        name = self._space.name
        if name in current:
            msg = (
                f"a batch is already collecting for {name} in this "
                f"context; batches do not nest per space"
            )
            raise MettaError(
                msg
            )
        self._pending = []
        self._token = _ACTIVE_BATCHES.set(current | {name: self._pending})
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _ACTIVE_BATCHES.reset(self._token)
        pending, self._pending = self._pending, []
        if exc_type is None and pending:
            # The batch is no longer active here, so this is the one real
            # crossing, the engine's own bulk operation underneath.
            self._space.add(*pending)

    def __len__(self) -> int:
        return len(self._pending)

_ACTIVE_SPACE: ContextVar[_SpaceId | None] = ContextVar(
    "metta_active_space", default=None
)

_RUN_BINDINGS: ContextVar[dict[str, Any] | None] = ContextVar(
    "metta_run_bindings", default=None
)

class _BoundValues:
    """Named host values visible to source execution inside one block."""

    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values
        self._token: Any = None

    def __enter__(self) -> Self:
        inherited = _RUN_BINDINGS.get() or {}
        self._token = _RUN_BINDINGS.set({**inherited, **self._values})
        return self

    def __exit__(self, *_exception: object) -> None:
        _RUN_BINDINGS.reset(self._token)

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.context,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_assuming_groups_multiple_cleanup_failures_after_removing_all', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_assuming_removes_every_fact_after_one_cleanup_fails', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_assuming_scopes_facts'),
)
def assuming(space: _root.Space, *facts: Any) -> _Assuming:
    """Facts held only inside a with-block: the assumptions reading of
    a what-if query, added on entry, removed on exit, exceptions
    included.

        with m.assuming(S.closed(S.bridge)):
            detour = m.match(S.route(V.r), where=...)
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _Assuming(space, [_to_atom(f) for f in facts])

# The body of a transaction in flight, by the ticket its engine call carries.
# The engine runs the body through metta_ops:transaction_body with the ticket,
# so no callable crosses: a crossed callable is held by its blob until atom GC
# and the next Prolog-to-Python call, and with it everything it closes over,
# the handle a `transaction(space.drop)` names included
# [tested: test_committed_retirements_leave_nothing_behind; commit=WORKTREE].
_BODIES: dict[int, Callable[[], Any]] = {}


def transaction_body(ticket: int) -> None:
    """The engine's call into a transaction's body, found by its ticket."""
    _BODIES[int(ticket)]()


def run_transaction(runtime: Runtime, body: Callable[[], Any]) -> dict[str, Any]:
    """Run ``body`` inside one closed engine transaction, handing the engine a ticket, never the body."""
    ticket = id(body)
    _BODIES[ticket] = body
    try:
        return runtime.once("metta_py_transaction(Ticket, R)", Ticket=ticket)
    finally:
        _BODIES.pop(ticket, None)


@overload
def transaction(space: _root.Space, target: Callable[[], _R], /) -> _R: ...

@overload
def transaction(space: _root.Space, target: Atom | str, /) -> list[Atom | Undefined]: ...

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_composes_with_transaction', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_transaction_term_uses_empty_answer_rollback_law', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_saga_refuses_transaction_speculation_and_batch_boundaries'),
    refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_transaction_refuses_an_unreported_engine_failure'),),
)
def transaction(space: _root.Space, target: Callable[[], _R] | Any, /) -> Any:
    """Run one callable or term inside a closed engine transaction.

    The two inputs preserve their native failure laws. A zero-argument
    Python callable commits its return value and rolls back on a Python
    exception. A term returns its engine answers and rolls back when that
    answer set is empty, exactly like ``(transaction ...)``.

        m.transaction(lambda: migrate(m))
        m.transaction(S.progn(write, verify))

    Every engine write the callable makes, stored atoms, equations
    and their compiled clauses included, commits or rolls back
    together. An exception is the callable's rollback trigger, because a
    Python callable cannot fail the Prolog way, and it re-raises AS
    ITSELF: your ValueError arrives as ValueError with the engine
    boundary in its chain. Only the engine's dynamic state rolls
    back; what the callable did on the Python side (a list appended,
    a file written) is yours to undo, SWI transactions being
    database-scoped.
    A cursor or ``fn`` call opened inside the transaction evaluates
    eagerly on its thread and belongs to that transaction.

    Transactions nest, SWI's own semantics: an inner commit is
    relative to its outer transaction, so an outer rollback discards
    inner work too.

    There is deliberately no `with m.transaction():` form. SWI's
    transaction/1 takes a closed goal; there is no open begin/commit
    to hold across a block, and pretending otherwise would lie about
    the isolation actually provided. transactional() is the
    decorator twin.
    """
    if not callable(target):
        return space.eval(Expression([Symbol("transaction"), _to_atom(target)]))
    #The callback's answer is CAPTURED here rather than carried back
    #through janus. janus converts whatever a callback returns and has no
    #conversion for an atom that is not a sequence: a body ending in
    #`add-atom` used to answer the unit expression, which converted as an
    #empty sequence, and answering `true` raised "Grounded(True) is a leaf
    #atom and has no length" from inside the transaction [measured
    #2026-08-30, examples/gallery/journaled_observed_store.py].
    #
    #Boxing rather than discarding, because the answer IS the result of
    #this call: _replace_catalog_declaration/4 returns the atom it stored
    #through here, so a transaction that answered None stopped every
    #catalog declaration silently, `compensates` included.
    answer: list[Any] = []

    def _capture() -> None:
        answer.append(target())

    # The operation registry is the library's OWN mirror of engine state,
    # which is what separates it from the Python state above: a rolled-back
    # registration left it claiming an operation the engine had forgotten,
    # so registered() said True while the call no longer reduced and an
    # installer's "already there" check skipped reinstalling a dead name.
    with lazy('metta._declare.operations').registry_undo():
        try:
            row = run_transaction(space._rt, _capture)
        except MettaError as error:
            original = original_exception(error)
            if original is not None and original is not error:
                raise original from error
            raise
        if not row:
            msg = (
                "the transaction goal failed without an exception, which "
                "metta_py_transaction does not do on purpose"
            )
            raise EngineError(
                msg
            )
    return cast("_R", answer[0] if answer else None)

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.context,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_scoped_limits_apply_and_per_call_overrides', 'extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_scoped_limits_validate_at_the_block', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_aio.py::test_aio_scoped_limits_cross_to_the_worker'),
    alias='limits',
)
def limits(
    _space: _root.Space,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
    stack: int | None = None,
) -> ScopedLimits:
    """Scoped default bounds for every call in the with-block:

        with m.limits(inferences=1_000_000, timeout=2.0):
            m.match(...)      # bounded without saying so again

    decimal.localcontext's shape, contextvars underneath, so the
    scope is async-correct and per-task. A per-call timeout= or
    inferences= still overrides, which is the whole ladder: one
    block replaces the parameter forest, and the forest remains
    for whoever wants per-call control.

    stack= is SWI's combined stack ceiling in BYTES, the bound a
    runaway recursion hits as a StackOverflow error atom. It is NOT
    MeTTa's reduction depth: that is the max-stack-depth pragma,
    `(with-pragma! ((max-stack-depth N)) expr)`, which counts
    reduction steps and is scoped in the program text.
    """  # noqa: D415  -- the first line deliberately introduces the indented example that follows
    return ScopedLimits(timeout, inferences, stack)

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.context,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_capture_composes_with_limits', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_eval_capture', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_capture_collects_held_engine_output'),
)
def capture(_space: _root.Space) -> _spaces_execution_module.CapturedOutput:
    r"""Collect printed engine text without changing answer shapes.

    with m.capture() as output:
        groups = m.run("!(println! hello) !(+ 1 2)")
    assert groups == [[3]]
    assert output.text == "hello\n"
    """
    return _spaces_execution_module.capture_output()

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/ch17_concurrency_and_the_loop/test_scopes.py::test_scope_releases_mints_and_refuses_every_alias', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_scopes.py::test_scope_joins_three_children_before_releasing_their_spaces', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_scopes.py::test_scope_owner_confines_keep_and_close'),
    async_excluded="a synchronous context manager confines exit to its entering host thread; use metta.scope() around the caller's block, not a manager constructed by a remote async worker",
)
def scope(space: _root.Space) -> _root.parallel.Scope:
    """Join children and release resources created in this block.

    ``with m.scope() as scope:`` owns newly minted spaces, channels,
    futures, pools and subscriptions. ``scope.keep(value)`` transfers
    spaces on successful exit. Child failure cancels siblings. Foreign
    calls must return before an engine checkpoint can stop them.
    """
    return lazy('metta.parallel').Scope(space)

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.context,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_an_atomic_scope_makes_one_python_write_one_transaction', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_atomic_run_commits_or_rolls_back_whole', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_atomic_rolls_back_after_a_late_cursor_failure'),
)
def atomic(_space: _root.Space) -> _spaces_execution_module.ScopedExecution:
    """Make each CALL in the block one committing engine transaction.

    Per call, the write doors included: ``m.add(a, b)`` inside the block
    is one transaction, so a provider that refuses the second atom takes
    the first back with it. Across SEVERAL calls the boundary is
    :meth:`transaction`, because SWI's transaction/1 takes a closed goal
    and an engine cannot yield out of one, so no with-block can hold one
    open; a raise later in the block does not undo a call that already
    committed.
    """
    return _spaces_execution_module.execution_scope("atomic")

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.context,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch08_data/test_state_cell.py::test_speculative_state_write_is_fenced', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_every_public_execution_door_honours_speculative_policy', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_speculative_lazy_execution_preserves_every_answer'),
    alias='speculate',
)
def speculative(_space: _root.Space) -> _spaces_execution_module.ScopedExecution:
    """Run each CALL against a snapshot and discard its writes.

    Per call, the write doors included: ``m.add(atom)`` inside the block
    leaves nothing behind, exactly as ``m.run("!(add-atom &self ...)")``
    in the same block does, and a later call in the block does not see
    what an earlier one wrote, because each call is its own what-if.
    """
    return _spaces_execution_module.execution_scope("speculative")

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.context,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_composes_with_transaction', 'extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_crosses_once_and_reads_see_the_pre_batch_space', 'extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_edges_are_enforced'),
)
def batch(space: _root.Space) -> _Batch:
    """Collect this space's add() calls and cross once at exit:

        with m.batch():
            for edge in edges:
                m.add(edge)          # collected, no crossing yet
        # one add_many crossing happened here

    The write forms are add for one or several atoms, batch for a region,
    transaction for all-or-nothing work, and a provider's bulk method
    underneath them. A batch is a transport economy and must not invent
    semantics, so the sharp edges are stated and enforced: reads
    inside the block see the space WITHOUT the pending adds; a
    remove() or clear() on this space inside the block refuses,
    because it would otherwise silently order around writes the
    program already made; and an exception discards the pending
    batch rather than landing writes the code after the raise never
    saw. Compose with transaction() for atomicity: batch for
    economy, transaction for all-or-nothing, or both.
    """  # noqa: D415  -- the first line deliberately introduces the indented example that follows
    return _Batch(space)

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.callable,
    effect=_doors.EffectClass.pureStructural,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync,),
    evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_transaction.py::test_transactional_is_the_decorator_twin',),
    async_excluded="a transaction body is a closed synchronous goal, SWI's transaction/1 takes one; transaction() is the async spelling, and there is no decorator because decoration cannot await",
    state=_doors.State.any,
)
def transactional(space: _root.Space, fn: Callable[_P, _R], /) -> Callable[_P, _R]:
    """transaction()'s decorator twin, the atomic shape Django made
    familiar: each CALL of the wrapped function runs inside its own
    engine transaction. Decorating runs nothing, exactly as a
    decorator should not; reach for transaction() to run one
    callable now.

        @m.transactional
        def migrate():
            m.add(...)
            m.remove(...)

        migrate()     # one transaction; a raise rolls it all back
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    @functools.wraps(fn)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        return space.transaction(lambda: fn(*args, **kwargs))

    return wrapper

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta.parallel  # noqa: F401 -- child of the annotation namespace
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
