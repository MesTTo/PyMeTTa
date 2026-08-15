"""Purpose: execute, profile, and evaluate terms for one named space.
Guarantees:
  - named host values retain object identity through source execution
    [tested test_run_using_carries_identity]
  - atomic and speculative writes remain mutually exclusive and preserve
    their transaction semantics [tested test_atomic_run_commits_or_rolls_back_whole,
    test_speculative_run_answers_and_discards]
  - value() refuses zero, multiple, and undefined answers [tested
    test_value_answers_the_one_answer, test_value_refuses_undefined_truth]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from ._engine import Runtime
from ._space_objects import EngineProfile, _limits
from .atoms import Atom, Gnd, Undefined, _to_atom, atom_from_wire, decode, encode, from_wire
from .errors import EngineError


def _run_target(space: str, source: str, using: dict[str, Any] | None) -> tuple[str, list[Any]]:
    if not using:
        return "petta_py_run", [source, space]
    pairs = [[name, encode(value).to_wire()] for name, value in using.items()]
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
    limits: tuple[float, int] | None,
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
    seconds, steps = limits if limits is not None else (-1.0, -1)
    row = rt.must(
        "petta_py_limited(T, I, P, Ins, Out)",
        T=seconds,
        I=steps,
        P=predicate,
        Ins=inputs,
    )
    return row.get("Out", [])


def _decode_groups(wires: Any) -> list[list[Atom]]:
    return [[atom_from_wire(wire) for wire in group] for group in wires]


def run_source(
    rt: Runtime,
    space: str,
    source: str,
    using: dict[str, Any] | None,
    *,
    timeout: float | None,
    inferences: int | None,
    capture: bool,
    atomic: bool,
    speculative: bool,
) -> list[list[Atom]] | tuple[list[list[Atom]], str]:
    """Execute source through the direct or controlled engine entry."""
    if atomic and speculative:
        raise ValueError(
            "atomic= and speculative= are exclusive: one commits the run's "
            "writes whole, the other discards them whole"
        )
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
    if capture:
        groups_wire, text = output
        return _decode_groups(groups_wire), text
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
    seconds, steps = _limits(timeout, inferences) or (-1.0, -1)
    row = rt.must(
        "petta_py_limited(T, I, P, Ins, Out)",
        T=seconds,
        I=steps,
        P="petta_py_profiled",
        Ins=[predicate, inputs],
    )
    output, samples, ticks, nodes = row["Out"]
    return _decode_groups(output), EngineProfile(samples, ticks, nodes)


def evaluate(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
    *,
    capture: bool,
    residuals: bool,
) -> list[Atom | Undefined] | tuple[list[Atom | Undefined], str]:
    predicate = "petta_py_eval_res_all" if residuals else "petta_py_eval_all"
    inputs = [space, _to_atom(target).to_wire()]
    limits = _limits(timeout, inferences)
    if limits is None and not capture:
        wires = rt.apply_must(predicate, *inputs)
    else:
        if capture:
            predicate, inputs = "petta_py_captured", [predicate, inputs]
        seconds, steps = limits if limits is not None else (-1.0, -1)
        output = rt.apply_must("petta_py_limited", seconds, steps, predicate, inputs)
        if capture:
            wires, text = output
            return [from_wire(wire) for wire in wires], text
        wires = output
    return [from_wire(wire) for wire in wires]


def value_one(target: Any, answers: list[Atom | Undefined]) -> Any:
    if len(answers) != 1:
        raise EngineError(
            f"value({_to_atom(target)}) expected exactly one answer, "
            f"got {len(answers)}; use eval() for any number"
        )
    answer = answers[0]
    if isinstance(answer, Undefined):
        raise EngineError(
            f"value({_to_atom(target)}) answered with undefined truth "
            f"({answer.why}); a caller asking for THE value has asserted a "
            f"definite one exists. eval() carries the third truth value."
        )
    return decode(answer) if isinstance(answer, Gnd) else answer


def evaluate_status(
    rt: Runtime,
    space: str,
    target: Any,
    timeout: float | None,
    inferences: int | None,
) -> list[tuple[str, Atom | Undefined | None]]:
    """Pair each answer with the evaluation path that produced it."""
    seconds, steps = _limits(timeout, inferences) or (-1.0, -1)
    rows = rt.apply_must(
        "petta_py_limited",
        seconds,
        steps,
        "petta_py_eval_status_all",
        [space, _to_atom(target).to_wire()],
    )
    return [
        (str(status), None if status == "empty" else from_wire(wire))
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
    seconds, steps = _limits(timeout, inferences) or (-1.0, -1)
    groups = rt.apply_must(
        "petta_py_limited", seconds, steps, "petta_py_run_status", [source, space]
    )
    return [
        [
            (str(status), None if status == "empty" else from_wire(wire))
            for status, wire in group
        ]
        for group in groups
    ]
