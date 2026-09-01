"""Purpose: execute, profile, and evaluate terms for one named space.
Guarantees:
  - named host values retain object identity through source execution
    [tested test_run_using_carries_identity]
  - capture never changes an answer shape, and atomic, speculative, and
    execution policy scopes compose without per-call flags [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms,
    test_every_public_execution_door_honours_speculative_policy,
    test_an_answers_view_uses_policy_when_its_engine_work_runs;
    commit=1262dd20ada9d5c799d9bdc4bdf5d2b859ca7a98]
  - eager eval follows the same atomic and speculative policy wrapper as run,
    so State property writes cannot bypass a speculative fence [tested:
    test_speculative_state_write_is_fenced; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - value() refuses zero, multiple, and undefined answers [tested
    test_value_answers_the_one_answer, test_value_refuses_undefined_truth]
  - ordinary evaluation returns an unreduced term directly and has no
    residual-shape flag [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - lazy evaluation preserves caller-variable rows and held-engine inference
    accounting across progressive pulls [tested:
    test_answers_project_caller_variables_and_slices_stay_answers,
    test_a_cached_definition_memoizes_its_complete_answer_bag;
    commit=5059173b1767600ce4df0f6b7841d88116ee62d3]
  - lazy evaluation keeps the answer value distinct from its parallel caller
    bindings [tested: test_calls_keep_values_and_binding_rows;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - an algebra call cursor returns its annotation beside the value while
    counting uses the engine aggregate with no value decoding [tested:
    test_counting_counts_duplicate_call_answers_inside_the_engine,
    test_ranked_and_tropical_slices_are_stable_best_prefixes;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - the held-evaluation cursor ships in the boot-consulted bridge rather than
    being consulted on the first answer pull [tested:
    test_first_answer_pull_has_no_late_consult_floor; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - controlled run, eval, status, profile, and lazy-pull calls preserve the /5
    limit seam unless a scoped stack byte count selects /6 [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - status evaluation accepts the eager eval door's named host substitutions
    and capture scope without evaluating the target twice [tested:
    test_eval_status_reports_the_four_outcomes,
    test_run_using_carries_identity; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - lazy evaluation uses a second engine for cardinality only when the
    translated goal is effect-safe [tested:
    test_effectful_relational_candidates_run_once_per_yield_on_fresh_list;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - an effect-bearing goal's cardinality and its values come from ONE
    evaluation that holds its answers in the engine, so a length nobody turns
    into values crosses one integer rather than encoding every answer
    [tested: test_a_retained_count_replays_the_bag_the_cursor_would_have_answered,
    test_a_length_evaluates_an_effect_bearing_goal_exactly_once;
    commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2]
  - abandoning that view releases the engine its count retained, on the path
    where the answers were never pulled as well [tested:
    test_a_counted_view_releases_its_engine_when_it_is_dropped;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements:
    - the holding evaluation covers the plain cursor only. A carrier cursor
      (evaluate_answers under=) answers an annotation beside every value,
      which metta_py_eval_count_retaining/6 does not hold, so its declined
      count still counts through one materializing pass.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import re
from collections import deque
from collections.abc import Generator, Iterable, Iterator, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Self

from ._engine import Runtime
from ._space_objects import (
    _CHUNK_CAP,
    EngineProfile,
    FunctionCost,
    _apply_limited,
    _column_names,
    _limits,
    _record_engine_inferences,
)
from .atoms import (
    Atom,
    Grounded,
    Undefined,
    _atom_from_wire,
    _decode,
    _encode,
    _from_wire,
    _to_atom,
)
from .errors import EngineError
from .results import Answers, _AnswerItem, _row_class, error_answer

_SCOPED_EXECUTION: ContextVar[frozenset[str]] = ContextVar(
    "metta_scoped_execution", default=frozenset()
)

_CAPTURED_OUTPUT: ContextVar[CapturedOutput | None]


def speculative_enabled() -> bool:
    """Whether this task is inside the discarded execution policy."""
    return "speculative" in _SCOPED_EXECUTION.get()


class ScopedExecution:
    """One execution policy applied to calls inside a with-block."""

    def __init__(self, mode: str) -> None:
        if mode not in ("atomic", "speculative"):
            msg = f"unknown execution mode {mode!r}"
            raise ValueError(msg)
        self.mode = mode
        self._token: Any = None

    def __enter__(self) -> Self:
        current = _SCOPED_EXECUTION.get()
        opposite = {"atomic": "speculative", "speculative": "atomic"}.get(
            self.mode
        )
        if opposite is not None and opposite in current:
            msg = (
                "atomic and speculative scopes are exclusive: one commits "
                "each call whole, the other discards its writes"
            )
            raise ValueError(msg)
        self._token = _SCOPED_EXECUTION.set(current | {self.mode})
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _SCOPED_EXECUTION.reset(self._token)


class CapturedOutput:
    """Printed engine text accumulated without changing call return values."""

    def __init__(self) -> None:
        self._chunks: list[str] = []
        self._token: Any = None

    @property
    def text(self) -> str:
        return "".join(self._chunks)

    def __enter__(self) -> Self:
        self._token = _CAPTURED_OUTPUT.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _CAPTURED_OUTPUT.reset(self._token)

    def _append(self, text: str) -> None:
        self._chunks.append(text)


_CAPTURED_OUTPUT = ContextVar("metta_captured_output", default=None)


def execution_scope(mode: str) -> ScopedExecution:
    return ScopedExecution(mode)


def capture_output() -> CapturedOutput:
    return CapturedOutput()


@dataclass(frozen=True, slots=True)
class _ExecutionPolicy:
    """One immutable reading of the task-local execution scopes."""

    mode: str | None
    captured: CapturedOutput | None


def _execution_policy() -> _ExecutionPolicy:
    """Read every execution policy at one crossing boundary."""
    modes = _SCOPED_EXECUTION.get()
    mode = "atomic" if "atomic" in modes else None
    if "speculative" in modes:
        mode = "speculative"
    return _ExecutionPolicy(mode, _CAPTURED_OUTPUT.get())


_DEFERRED_EXECUTION_OPENERS = {
    "metta_py_cursor_open": "metta_py_cursor_open_controlled",
    "metta_py_cursor_open_under": "metta_py_cursor_open_under_controlled",
    "metta_py_eval_cursor_open": "metta_py_eval_cursor_open_controlled",
    "metta_py_eval_cursor_open_under": (
        "metta_py_eval_cursor_open_under_controlled"
    ),
}
_DEFERRED_EXECUTION_RESUMES = {
    "metta_py_cursor_chunk": "metta_py_cursor_chunk_controlled",
    "metta_py_cursor_next": "metta_py_cursor_next_controlled",
}


def _run_target(space: str, source: str, using: dict[str, Any] | None) -> tuple[str, list[Any]]:
    if not using:
        return "metta_py_run", [source, space]
    # A NAME only. bind() also takes an atom key, which means that exact atom
    # and is applied in the host before a TERM is asked; source text has no
    # term yet, so there is nothing here to apply it to. Refusing beats
    # dropping it, which would run the source with the binding silently
    # missing.
    unnamed = [key for key in using if not isinstance(key, str)]
    if unnamed:
        msg = (
            f"source execution binds by NAME, and {unnamed!r} names an atom. "
            f"An atom key is applied to a TERM, so pass the term to eval(), "
            f"answers() or eval_status() instead, or bind the name the "
            f"source writes."
        )
        raise TypeError(msg)
    pairs = [[name, _encode(value).to_wire()] for name, value in using.items()]
    return "metta_py_run_using", [source, space, pairs]


def _controlled_run(
    rt: Runtime,
    predicate: str,
    inputs: list[Any],
    limits: tuple[float, int, int] | None,
    *,
    policy: _ExecutionPolicy | None = None,
) -> Any:
    """Execute one engine target through the complete task-local policy.

    No caller selects individual wrappers. That is the invariant which keeps
    lazy cursors, diagnostics, and future execution doors from silently
    inheriting only a subset of capture, atomic, and speculative semantics.
    """
    policy = _execution_policy() if policy is None else policy
    deferred = _DEFERRED_EXECUTION_OPENERS.get(predicate)
    resumed = _DEFERRED_EXECUTION_RESUMES.get(predicate)
    mode_is_held = deferred is not None or resumed is not None
    if deferred is not None:
        predicate = deferred
        inputs = [
            *inputs,
            [policy.mode or "none", policy.captured is not None],
        ]
    elif resumed is not None and policy.captured is not None:
        predicate = resumed
    elif not mode_is_held:
        if policy.mode == "atomic":
            predicate, inputs = "metta_py_atomic", [predicate, inputs]
        elif policy.mode == "speculative":
            predicate, inputs = "metta_py_speculative", [predicate, inputs]
    if policy.captured is not None and not mode_is_held:
        predicate, inputs = "metta_py_captured", [predicate, inputs]
    has_outer_policy = not mode_is_held and (
        policy.captured is not None or policy.mode is not None
    )
    output = (
        rt.apply_must(predicate, *inputs)
        if limits is None and not has_outer_policy
        else _apply_limited(
            rt,
            limits if limits is not None else (-1.0, -1, -1),
            predicate,
            inputs,
        )
    )
    captures_output = policy.captured is not None and (
        resumed is not None or deferred is None
    )
    if captures_output:
        output, text = output
        policy.captured._append(str(text))
    return output


def _decode_groups(wires: Any) -> list[list[Atom]]:
    return [[_atom_from_wire(wire) for wire in group] for group in wires]


def run_source(
    rt: Runtime,
    space: str,
    source: str,
    using: dict[str, Any] | None,
    *,
    timeout: float | None,
    inferences: int | None,
) -> list[list[Atom]]:
    """Execute source through the direct or controlled engine entry."""
    predicate, inputs = _run_target(space, source, using)
    limits = _limits(timeout, inferences)
    return _decode_groups(_controlled_run(rt, predicate, inputs, limits))


def profile_source(
    rt: Runtime,
    space: str,
    source: str,
    using: dict[str, Any] | None,
    *,
    timeout: float | None,
    inferences: int | None,
) -> tuple[list[list[Atom]], EngineProfile]:
    predicate, inputs = _run_target(space, source, using)
    output, samples, ticks, nodes = _controlled_run(
        rt,
        "metta_py_profiled",
        [predicate, inputs],
        _limits(timeout, inferences) or (-1.0, -1, -1),
    )
    return _decode_groups(output), EngineProfile(samples, ticks, nodes)


# The profiler names a predicate the way Prolog writes it, module and arity
# included, so `user:'vec-dot'/2` has to be read back apart to be matched
# against a registered function's name.
_PROFILED_PREDICATE = re.compile(r"^(?:[^:]+:)?'?(.*?)'?/(\d+)$")


def _profiled_rows(nodes: Iterable[Sequence[Any]]) -> dict[tuple[str, int], tuple[int, int, int]]:
    """calls, redos and self-ticks per (name, arity), from the sampler."""
    rows: dict[tuple[str, int], tuple[int, int, int]] = {}
    for node in nodes:
        predicate, calls, redos, ticks_self = node[0], node[1], node[2], node[3]
        found = _PROFILED_PREDICATE.match(str(predicate))
        if found is None:
            continue
        key = (found.group(1), int(found.group(2)))
        # A predicate can appear once per calling context; the function's cost
        # is their sum, not whichever the sampler listed first.
        previous = rows.get(key, (0, 0, 0))
        rows[key] = (
            previous[0] + int(calls),
            previous[1] + int(redos),
            previous[2] + int(ticks_self),
        )
    return rows


def profile_extension(
    rt: Runtime,
    space: str,
    source: str,
    using: dict[str, Any] | None,
    names: Sequence[str],
    *,
    timeout: float | None,
    inferences: int | None,
) -> tuple[list[list[Atom]], list[FunctionCost]]:
    """Run source under the profiler and report only the named functions.

    The sampler already answers per predicate; what it cannot say is which
    tier put a name there and whether the clause index its callers rely on
    exists, which the engine knows and is asked for here.
    """
    groups, profile = profile_source(
        rt, space, source, using, timeout=timeout, inferences=inferences
    )
    measured = _profiled_rows(profile.nodes)
    costs: list[FunctionCost] = []
    for name in names:
        tier, detail, arities, determinism = _controlled_run(
            rt, "metta_py_function_shape", [name], None
        )
        shapes: list[tuple[int | None, float, bool]] = [
            (int(arity), float(speedup), bool(indexed))
            for arity, speedup, indexed in arities
        ]
        # A function with no recorded arity is still worth a row: it is the
        # answer to "did my registration take", and a silent omission reads
        # as "it cost nothing".
        for arity, speedup, indexed in shapes or [(None, 1.0, False)]:
            # No arity means no registered predicate, so the sampler cannot
            # have a row for it either.
            measurement = (0, 0, 0) if arity is None else measured.get((name, arity), (0, 0, 0))
            calls, redos, ticks = measurement
            costs.append(
                FunctionCost(
                    name=str(name),
                    tier=str(tier),
                    source=str(detail),
                    arity=arity,
                    calls=calls,
                    redos=redos,
                    ticks=ticks,
                    speedup=speedup,
                    indexed=indexed,
                    determinism=str(determinism),
                )
            )
    costs.sort(key=lambda cost: (-cost.ticks, -cost.calls, cost.name))
    return groups, costs


def evaluate(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
    *,
    using: dict[str, Any] | None = None,
) -> list[Atom | Undefined]:
    predicate = "metta_py_eval_all"
    # Source text goes over as text. Parsing it here would cross to the engine's
    # reader, build an Atom from the wire form it answers, and walk that Atom
    # straight back to the same wire form for this call, so a string target cost
    # two crossings and a round trip through a term that never left the engine
    # [measured 2026-08-16: eval("(structured (pair a b))") 516.00 inferences
    # parsed first against 449.00 read where it is evaluated].
    inputs = [space, target if isinstance(target, str) else _to_atom(target).to_wire()]
    if using:
        predicate = "metta_py_eval_using_all"
        inputs = [
            *inputs,
            [[name, _encode(value).to_wire()] for name, value in using.items()],
        ]
    wires = _controlled_run(
        rt, predicate, inputs, _limits(timeout, inferences)
    )
    return [_from_wire(wire) for wire in wires]


def evaluate_many(
    rt: Runtime,
    space: str,
    targets: tuple[Any, ...],
    timeout: float | None,
    inferences: int | None,
    *,
    using: dict[str, Any] | None = None,
) -> list[list[Atom | Undefined]]:
    """Evaluate several targets in ONE crossing, one answer group each.

    The batch is how evaluation amortises the boundary the way add's
    batch amortises writes: run()'s own grouping carried to the eval
    door. One bind scope applies to every target, limits bound the whole
    crossing, and a capture scope collects once, all exactly as the
    single door's wrappers behave.
    """
    predicate = "metta_py_eval_many_all"
    encoded = [
        target if isinstance(target, str) else _to_atom(target).to_wire()
        for target in targets
    ]
    inputs: list[Any] = [space, encoded]
    if using:
        predicate = "metta_py_eval_many_using_all"
        inputs.append(
            [[name, _encode(value).to_wire()] for name, value in using.items()]
        )
    groups = _controlled_run(
        rt, predicate, inputs, _limits(timeout, inferences)
    )
    return [[_from_wire(wire) for wire in group] for group in groups]


def _count_inputs(
    space: str,
    target: Any,
    using: dict[str, Any] | None,
) -> list[Any]:
    """The space, wire target, and named substitutions a count door takes."""
    encoded_target = target if isinstance(target, str) else _to_atom(target).to_wire()
    pairs = (
        []
        if not using
        else [[name, _encode(value).to_wire()] for name, value in using.items()]
    )
    return [space, encoded_target, pairs]


def _count_call(
    rt: Runtime,
    predicate: str,
    inputs: list[Any],
    timeout: float | None,
    inferences: int | None,
) -> Any:
    """Send one counting predicate through the shared policy wrapper."""
    return _controlled_run(
        rt, predicate, inputs, _limits(timeout, inferences)
    )


def evaluate_count(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
    *,
    using: dict[str, Any] | None = None,
    under: str | None = None,
) -> int:
    """Count call answers in the engine without decoding any answer value.

    For the caller whose count IS the whole evaluation. The counting carrier
    holds no answer cursor beside its scalar, so nothing here can run twice
    and the repeatability question does not arise.
    """
    inputs = _count_inputs(space, target, using)
    predicate = "metta_py_eval_count"
    if under is not None:
        predicate = "metta_py_eval_count_under"
        inputs.append(under)
    return int(_count_call(rt, predicate, inputs, timeout, inferences))


def evaluate_count_if_repeatable(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
    *,
    using: dict[str, Any] | None = None,
    under: str | None = None,
) -> int | None:
    """The same count for a caller that also holds this goal's answer cursor.

    Answers None when the engine classifies the goal effect-unsafe to run a
    second time; counting it here and then opening the cursor would fire the
    effects twice. The repeatability guard survives the carrier, because a
    count is a second evaluation whatever algebra tags it.
    """
    inputs = _count_inputs(space, target, using)
    predicate = "metta_py_eval_count_if_repeatable"
    if under is not None:
        predicate = "metta_py_eval_count_under_if_repeatable"
        inputs.append(under)
    output = _count_call(rt, predicate, inputs, timeout, inferences)
    return int(output[0]) if output else None


def _retain_and_count(
    rt: Runtime,
    inputs: list[Any],
    seconds: float | None,
    stack: int,
) -> tuple[int, Any]:
    """Evaluate once, answer the count, and hold the answers unencoded.

    The wall and stack limits wrap this call the way they wrap one cursor
    pull, and the inference limit rides inside the predicate as it does for
    the cursor, because this single call is the whole enumeration.
    """
    limits = (
        None
        if seconds is None and stack < 0
        else (-1.0 if seconds is None else seconds, -1, stack)
    )
    output = _controlled_run(
        rt, "metta_py_eval_count_retaining", inputs, limits
    )
    count, handle = output
    return int(count), handle


class _RetainedAnswers:
    """An answer stream that owns the cursor a declined count left behind.

    Both close on every path that abandons the view.
    Both hold ONE SWI engine and the whole bag it counted. Closing the
    generator alone released nothing when the generator had never started,
    because a generator that never ran runs no finally block: a view that was
    counted and never iterated left its engine and its answers alive for the
    life of the process [measured 2026-08-30: current_engine/1 still counted
    the engine after del and gc.collect(), and metta_py_cursor_next still
    answered from the abandoned handle; tested
    test_a_counted_view_releases_its_engine_when_it_is_dropped].
    """

    __slots__ = ("_answers", "_retained", "_rt")

    def __init__(
        self, answers: Generator[Any], retained: list[Any], rt: Runtime
    ) -> None:
        self._answers = answers
        self._retained = retained
        self._rt = rt

    def __iter__(self) -> Iterator[Any]:
        return self

    def __next__(self) -> Any:
        return next(self._answers)

    def close(self) -> None:
        """Release the stream and any cursor it never took over.

        A started generator has already popped the handle, so its own finally
        closes that engine and the list is empty here; an unstarted one leaves
        it, and this is the only place left to close it.
        """
        try:
            self._answers.close()
        finally:
            while self._retained:
                self._rt.do("metta_py_cursor_close", self._retained.pop())


def evaluate_answers(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
    *,
    using: dict[str, Any] | None = None,
    under: str | None = None,
    order: str | None = None,
) -> Answers[Any]:
    """Return evaluation as a cached lazy answer sequence.

    The SWI engine is opened on the first pull. Its inference budget spans
    every resume, while the wall limit wraps each CROSSING, which since the
    chunked pull covers a doubling batch of answers rather than one, the
    accepted price of the crossing win [tested:
    test_the_evaluation_cursor_chunks_too;
    test_function_calls_pull_engine_answers_only_as_demanded;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4].

    A pristine view counts through a separate engine only when the translated
    goal is effect-safe. Otherwise the count and the values come from ONE
    evaluation that holds its answers in the engine, so list() cannot execute
    an effect once for its length hint and again for its values, and a count
    nobody turns into values crosses one integer instead of encoding every
    answer [tested:
    test_effectful_relational_candidates_run_once_per_yield_on_fresh_list,
    test_a_retained_count_replays_the_bag_the_cursor_would_have_answered;
    commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2].
    """
    encoded_target = target if isinstance(target, str) else _to_atom(target).to_wire()
    columns = [] if isinstance(target, str) else _column_names((_to_atom(target),))
    pairs = (
        None
        if not using
        else [[name, _encode(value).to_wire()] for name, value in using.items()]
    )
    limits = _limits(timeout, inferences)
    seconds = None if limits is None or limits[0] < 0 else limits[0]
    steps = -1 if limits is None else limits[1]
    stack = -1 if limits is None else limits[2]
    #: The cursor a declined count left behind, at most one, read by the first
    #: pull. Written under Answers' own lock, which serialises len() against
    #: every pull, and only while the view is still pristine.
    retained: list[Any] = []

    def count_answers(*, values_wanted: bool) -> int | None:
        counted = evaluate_count_if_repeatable(
            rt,
            space,
            target,
            timeout,
            inferences,
            using=using,
            under=under,
        )
        if counted is not None or under is not None or values_wanted:
            # Three ways this count is already the cheapest one available.
            # An effect-safe goal counts on its own engine. A carrier cursor
            # answers an annotation beside every value, a shape the holding
            # door does not carry. And a caller that has taken an iterator is
            # about to read the answers, so holding them to avoid a second
            # evaluation buys nothing that one materializing pass does not.
            return counted
        count, handle = _retain_and_count(
            rt,
            [space, encoded_target, pairs or [], columns, steps],
            seconds,
            stack,
        )
        retained.append(handle)
        return count

    def stream() -> Generator[Any]:
        policy = _execution_policy()
        if retained:
            handle = retained.pop()
        else:
            predicate = "metta_py_eval_cursor_open"
            inputs: list[Any] = [space, encoded_target, pairs or [], columns, steps]
            if under is not None:
                predicate = "metta_py_eval_cursor_open_under"
                inputs.extend((under, order or "none"))
            # engine_create/3 is inert, but the selected execution mode must
            # be embedded in its held goal before the first pull starts it.
            handle = _controlled_run(
                rt, predicate, inputs, None, policy=policy
            )
        row_cls = _row_class(tuple(columns))
        reported_inferences = 0
        # The same doubling chunk the match cursor pulls, for the same
        # measured reason: the crossing is half the cost of a drain, and a
        # short chunk is the whole of the exhaustion signal. Captured engine
        # output arrives once per refill rather than once per answer, which
        # capture()'s block-scoped contract never promised more finely.
        buffered: deque[Any] = deque()
        want = 1
        drained = False
        try:
            while True:
                if not buffered:
                    if drained:
                        return
                    pull_limits = (
                        None
                        if seconds is None and stack < 0
                        else (-1.0 if seconds is None else seconds, -1, stack)
                    )
                    output = _controlled_run(
                        rt,
                        "metta_py_cursor_chunk",
                        [handle, want],
                        pull_limits,
                        policy=policy,
                    )
                    if len(output) < want:
                        drained = True
                    want = min(want * 2, _CHUNK_CAP)
                    if not output:
                        return
                    buffered.extend(output)
                if under is None:
                    value_wire, row_wires, cumulative_inferences = buffered.popleft()
                    annotation_wire = None
                else:
                    value_wire, row_wires, annotation_wire, cumulative_inferences = (
                        buffered.popleft()
                    )
                current_inferences = int(cumulative_inferences)
                _record_engine_inferences(
                    max(0, current_inferences - reported_inferences)
                )
                reported_inferences = current_inferences
                value: Any = _from_wire(value_wire)
                if (
                    annotation_wire is not None
                    and error_answer(value) is None
                    and not isinstance(value, Undefined)
                ):
                    from ._space import Space  # noqa: PLC0415 -- avoid module cycle
                    from .algebra import captured_answer  # noqa: PLC0415 -- lazy satellite

                    value = captured_answer(
                        Space(space, _runtime=rt),
                        value,
                        _atom_from_wire(annotation_wire),
                        under,
                    )
                # A failed branch is still its Error/Undefined answer.  For an
                # ordinary relational answer, preserve the caller bindings as
                # metadata instead of replacing the value with its row.
                if (
                    columns
                    and error_answer(value) is None
                    and not isinstance(value, Undefined)
                ):
                    row = row_cls(_atom_from_wire(wire) for wire in row_wires)
                    yield _AnswerItem(value, row)
                else:
                    yield value
        finally:
            rt.do("metta_py_cursor_close", handle)

    return Answers(
        _RetainedAnswers(stream(), retained, rt),
        columns=columns,
        space=space,
        target=target,
        count=count_answers,
    )


def value_one(target: Any, answers: list[Atom | Undefined]) -> Any:
    if len(answers) != 1:
        msg = (
            f"value({_to_atom(target)}) expected exactly one answer, "
            f"got {len(answers)}; use eval() for any number"
        )
        raise EngineError(
            msg
        )
    answer = answers[0]
    if isinstance(answer, Undefined):
        msg = (
            f"value({_to_atom(target)}) answered with undefined truth "
            f"({answer.why}); a caller asking for THE value has asserted a "
            f"definite one exists. eval() carries the third truth value."
        )
        raise EngineError(
            msg
        )
    return _decode(answer) if isinstance(answer, Grounded) else answer


def evaluate_status(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
    *,
    using: dict[str, Any] | None = None,
) -> list[tuple[str, Atom | Undefined | None]]:
    """Pair each answer with the evaluation path that produced it."""
    predicate = "metta_py_eval_status_all"
    inputs: list[Any] = [
        space,
        target if isinstance(target, str) else _to_atom(target).to_wire(),
    ]
    if using:
        predicate = "metta_py_eval_status_using_all"
        inputs.append(
            [[name, _encode(value).to_wire()] for name, value in using.items()]
        )
    rows = _controlled_run(
        rt,
        predicate,
        inputs,
        _limits(timeout, inferences),
    )
    return [
        (str(status), None if status == "empty" else _from_wire(wire))
        for status, wire in rows
    ]


def run_status(
    rt: Runtime,
    space: str,
    source: str,
    timeout: float | None,
    inferences: int | None,
) -> list[list[tuple[str, Atom | Undefined | None]]]:
    """One (status, answer) list per ! directive, in source order."""
    groups = _controlled_run(
        rt,
        "metta_py_run_status",
        [source, space],
        _limits(timeout, inferences) or (-1.0, -1, -1),
    )
    return [
        [
            (str(status), None if status == "empty" else _from_wire(wire))
            for status, wire in group
        ]
        for group in groups
    ]
