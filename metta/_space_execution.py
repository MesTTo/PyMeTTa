"""Purpose: execute, profile, and evaluate terms for one named space.
Guarantees:
  - named host values retain object identity through source execution
    [tested test_run_using_carries_identity]
  - capture never changes an answer shape, and atomic, speculative, and
    strict execution policy scopes compose without per-call flags [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - value() refuses zero, multiple, and undefined answers [tested
    test_value_answers_the_one_answer, test_value_refuses_undefined_truth]
  - ordinary evaluation returns an unreduced term directly and has no
    residual-shape flag [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - lazy evaluation preserves caller-variable rows and held-engine inference
    accounting across progressive pulls [tested:
    test_answers_project_caller_variables_and_slices_stay_answers,
    test_a_cached_definition_tables_and_answers_from_its_trie;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - lazy evaluation keeps the answer value distinct from its parallel caller
    bindings [tested: test_calls_keep_values_and_binding_rows;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - the held-evaluation cursor ships in the boot-consulted bridge rather than
    being consulted on the first answer pull [tested:
    test_first_answer_pull_has_no_late_consult_floor; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - controlled run, eval, status, profile, and lazy-pull calls preserve the /5
    limit seam unless a scoped stack byte count selects /6 [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - status evaluation accepts the eager eval door's named host substitutions
    and capture scope without evaluating the target twice [tested:
    test_strict_eval_refuses_only_not_reducible; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from contextvars import ContextVar
from typing import Any, Self

from ._engine import Runtime
from ._space_objects import (
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
    "petta_scoped_execution", default=frozenset()
)

_CAPTURED_OUTPUT: ContextVar[CapturedOutput | None]


class ScopedExecution:
    """One execution policy applied to calls inside a with-block."""

    def __init__(self, mode: str) -> None:
        if mode not in ("atomic", "speculative", "strict"):
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


_CAPTURED_OUTPUT = ContextVar("petta_captured_output", default=None)


def execution_scope(mode: str) -> ScopedExecution:
    return ScopedExecution(mode)


def capture_output() -> CapturedOutput:
    return CapturedOutput()


def strict_enabled() -> bool:
    return "strict" in _SCOPED_EXECUTION.get()


def _run_target(space: str, source: str, using: dict[str, Any] | None) -> tuple[str, list[Any]]:
    if not using:
        return "petta_py_run", [source, space]
    pairs = [[name, _encode(value).to_wire()] for name, value in using.items()]
    return "petta_py_run_using", [source, space, pairs]


def _direct_run(
    rt: Runtime,
    predicate: str,
    inputs: list[Any],
    using: dict[str, Any] | None,
) -> Any:
    names = ["Src", "Space", "Pairs"] if using else ["Src", "Space"]
    goal = f"{predicate}({', '.join(names)}, Groups)"
    return rt.must(goal, **dict(zip(names, inputs, strict=True))).get("Groups", [])


def _controlled_run(
    rt: Runtime,
    predicate: str,
    inputs: list[Any],
    limits: tuple[float, int, int] | None,
    *,
    capture: bool,
    atomic: bool,
    speculative: bool,
) -> Any:
    if atomic:
        predicate, inputs = "petta_py_atomic", [predicate, inputs]
    elif speculative:
        predicate, inputs = "petta_py_speculative", [predicate, inputs]
    if capture:
        predicate, inputs = "petta_py_captured", [predicate, inputs]
    return _apply_limited(
        rt,
        limits if limits is not None else (-1.0, -1, -1),
        predicate,
        inputs,
    )


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
    modes = _SCOPED_EXECUTION.get()
    atomic = "atomic" in modes
    speculative = "speculative" in modes
    captured = _CAPTURED_OUTPUT.get()
    capture = captured is not None
    predicate, inputs = _run_target(space, source, using)
    limits = _limits(timeout, inferences)
    if limits is None and not (capture or atomic or speculative):
        output = _direct_run(rt, predicate, inputs, using)
    else:
        output = _controlled_run(
            rt,
            predicate,
            inputs,
            limits,
            capture=capture,
            atomic=atomic,
            speculative=speculative,
        )
    if captured is not None:
        groups_wire, text = output
        captured._append(str(text))
        return _decode_groups(groups_wire)
    return _decode_groups(output)


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
    output, samples, ticks, nodes = _apply_limited(
        rt,
        _limits(timeout, inferences) or (-1.0, -1, -1),
        "petta_py_profiled",
        [predicate, inputs],
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
        tier, detail, arities, determinism = rt.apply_must(
            "petta_py_function_shape", name
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
    predicate = "petta_py_eval_all"
    # Source text goes over as text. Parsing it here would cross to the engine's
    # reader, build an Atom from the wire form it answers, and walk that Atom
    # straight back to the same wire form for this call, so a string target cost
    # two crossings and a round trip through a term that never left the engine
    # [measured 2026-08-16: eval("(structured (pair a b))") 516.00 inferences
    # parsed first against 449.00 read where it is evaluated].
    inputs = [space, target if isinstance(target, str) else _to_atom(target).to_wire()]
    if using:
        predicate = "petta_py_eval_using_all"
        inputs = [
            *inputs,
            [[name, _encode(value).to_wire()] for name, value in using.items()],
        ]
    limits = _limits(timeout, inferences)
    captured = _CAPTURED_OUTPUT.get()
    if limits is captured is None:
        wires = rt.apply_must(predicate, *inputs)
    else:
        if captured is not None:
            predicate, inputs = "petta_py_captured", [predicate, inputs]
        output = _apply_limited(
            rt,
            limits if limits is not None else (-1.0, -1, -1),
            predicate,
            inputs,
        )
        if captured is not None:
            wires, text = output
            captured._append(str(text))
            return [_from_wire(wire) for wire in wires]
        wires = output
    return [_from_wire(wire) for wire in wires]


def evaluate_answers(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
    *,
    using: dict[str, Any] | None = None,
) -> Answers[Any]:
    """Return evaluation as a cached lazy answer sequence.

    The SWI engine is opened on the first pull. Its inference budget spans
    every resume, while the wall limit wraps each individual resume, matching
    the established query-cursor economics [tested:
    test_function_calls_pull_engine_answers_only_as_demanded;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4].
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

    def count_answers() -> int:
        predicate = "petta_py_eval_count"
        inputs: list[Any] = [space, encoded_target, pairs or []]
        captured = _CAPTURED_OUTPUT.get()
        if captured is not None:
            predicate, inputs = "petta_py_captured", [predicate, inputs]
        if limits is None:
            output = rt.apply_must(predicate, *inputs)
        else:
            output = _apply_limited(rt, limits, predicate, inputs)
        if captured is not None:
            output, captured_text = output
            captured._append(str(captured_text))
        return int(output)

    def stream() -> Iterator[Any]:
        handle = rt.apply_must(
            "petta_py_eval_cursor_open", space, encoded_target, pairs or [], columns, steps
        )
        row_cls = _row_class(tuple(columns))
        reported_inferences = 0
        try:
            while True:
                captured = _CAPTURED_OUTPUT.get()
                predicate = "petta_py_cursor_next"
                inputs: list[Any] = [handle]
                if captured is not None:
                    predicate, inputs = "petta_py_captured", [predicate, inputs]
                if seconds is None and stack < 0:
                    output = rt.apply_must(predicate, *inputs)
                else:
                    output = _apply_limited(
                        rt,
                        (-1.0 if seconds is None else seconds, -1, stack),
                        predicate,
                        inputs,
                    )
                if captured is not None:
                    output, text = output
                    captured._append(str(text))
                if not output:
                    return
                value_wire, row_wires, cumulative_inferences = output[0]
                current_inferences = int(cumulative_inferences)
                _record_engine_inferences(
                    max(0, current_inferences - reported_inferences)
                )
                reported_inferences = current_inferences
                value = _from_wire(value_wire)
                # A failed branch is still its Error/Undefined answer.  For an
                # ordinary relational answer, preserve the caller bindings as
                # metadata instead of replacing the value with its row.
                if columns and error_answer(value) is None and not isinstance(value, Undefined):
                    row = row_cls(_atom_from_wire(wire) for wire in row_wires)
                    yield _AnswerItem(value, row)
                else:
                    yield value
        finally:
            rt.do("petta_py_cursor_close", handle)

    return Answers(
        stream(),
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
    predicate = "petta_py_eval_status_all"
    inputs: list[Any] = [
        space,
        target if isinstance(target, str) else _to_atom(target).to_wire(),
    ]
    if using:
        predicate = "petta_py_eval_status_using_all"
        inputs.append(
            [[name, _encode(value).to_wire()] for name, value in using.items()]
        )
    captured = _CAPTURED_OUTPUT.get()
    if captured is not None:
        predicate, inputs = "petta_py_captured", [predicate, inputs]
    output = _apply_limited(
        rt,
        _limits(timeout, inferences) or (-1.0, -1, -1),
        predicate,
        inputs,
    )
    if captured is not None:
        rows, captured_text = output
        captured._append(str(captured_text))
    else:
        rows = output
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
    groups = _apply_limited(
        rt,
        _limits(timeout, inferences) or (-1.0, -1, -1),
        "petta_py_run_status",
        [source, space],
    )
    return [
        [
            (str(status), None if status == "empty" else _from_wire(wire))
            for status, wire in group
        ]
        for group in groups
    ]
