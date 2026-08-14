"""Purpose: run one benchmark workload for perf instructions:u.
Guarantees:
  - setup and teardown stay outside perf's controlled measurement interval
    [tested test_perf_workload_setup_and_teardown_stay_outside_control]
Owns:
  - main releases the selected workload after success or failure
    [tested test_perf_workload_teardown_runs_after_failure]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import argparse
import os
from collections.abc import Callable, Sequence

from benchmarks.engine_workloads import (
    EngineCase,
    alpha_unique_case,
    close_engine_case,
    digest_case,
    let_heavy,
    let_space,
    py_method_case,
    sort_atom_case,
    source_load_case,
    space_name_case,
)
from benchmarks.workloads import (
    json_payload,
    json_wire,
    term_operators,
    wire_atom,
    wire_codec,
)

PerfCase = tuple[Callable[[], int], Callable[[], None]]


def _no_teardown() -> None:
    pass


def _wire_codec() -> PerfCase:
    atom = wire_atom()
    return lambda: wire_codec(atom), _no_teardown


def _json_wire() -> PerfCase:
    payload = json_payload()
    return lambda: json_wire(payload), _no_teardown


def _term_operators() -> PerfCase:
    return term_operators, _no_teardown


def _engine_case(factory: Callable[[], EngineCase]) -> PerfCase:
    state = factory()
    return state[1], lambda: close_engine_case(state)


def _let_heavy() -> PerfCase:
    space = let_space()
    return lambda: let_heavy(space), space.drop


_CASES = {
    "alpha-unique": lambda: _engine_case(alpha_unique_case),
    "json-wire": _json_wire,
    "let-heavy": _let_heavy,
    "py-method-call": lambda: _engine_case(py_method_case),
    "sort-atom": lambda: _engine_case(sort_atom_case),
    "source-load": lambda: _engine_case(source_load_case),
    "space-digest": lambda: _engine_case(digest_case),
    "space-name": lambda: _engine_case(space_name_case),
    "term-operators": _term_operators,
    "wire-codec": _wire_codec,
}


def _acknowledge(descriptor: int) -> None:
    response = bytearray()
    while b"\n" not in response:
        chunk = os.read(descriptor, 16 - len(response))
        if not chunk:
            raise RuntimeError("perf control acknowledgement pipe closed")
        response.extend(chunk)
        if len(response) == 16 and b"\n" not in response:
            raise RuntimeError(f"invalid perf control acknowledgement: {response!r}")
    if response.rstrip(b"\0") != b"ack\n":
        raise RuntimeError(f"invalid perf control acknowledgement: {response!r}")


def _controlled(operation) -> int:
    try:
        control = int(os.environ["PETTA_PERF_CONTROL_FD"])
        acknowledge = int(os.environ["PETTA_PERF_ACK_FD"])
        close_descriptors = tuple(
            int(value) for value in os.environ["PETTA_PERF_CLOSE_FDS"].split(",")
        )
    except (KeyError, ValueError) as error:
        raise RuntimeError("controlled perf descriptors are missing or invalid") from error
    for descriptor in close_descriptors:
        os.close(descriptor)
    if os.write(control, b"enable\n") != len(b"enable\n"):
        raise RuntimeError("perf control enable command was truncated")
    _acknowledge(acknowledge)
    try:
        return operation()
    finally:
        if os.write(control, b"disable\n") != len(b"disable\n"):
            raise RuntimeError("perf control disable command was truncated")
        _acknowledge(acknowledge)


def main(argv: Sequence[str] | None = None) -> int:
    """Run exactly one named workload."""
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=sorted(_CASES))
    parser.add_argument("--controlled", action="store_true")
    arguments = parser.parse_args(argv)
    operation, teardown = _CASES[arguments.case]()
    try:
        completed = _controlled(operation) if arguments.controlled else operation()
    finally:
        teardown()
    if completed <= 0:
        raise AssertionError(f"{arguments.case} completed no operations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
