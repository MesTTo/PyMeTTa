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
    close_save_load_case,
    digest_case,
    let_heavy,
    let_space,
    py_method_case,
    save_load_case,
    sort_atom_case,
    source_load_case,
    space_name_case,
    typed_call,
    typed_space,
)
from benchmarks.subscription import (
    close_subscription_case,
    subscription_dispatch_case,
)
from benchmarks.workloads import (
    json_payload,
    json_wire,
    structures_dispatch,
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
    #One trip at build time boots the engine, whose codec this is now,
    #so the measured window holds round trips and not the boot.
    json_wire(payload, trips=1)
    return lambda: json_wire(payload), _no_teardown


def _term_operators() -> PerfCase:
    return term_operators, _no_teardown


def _engine_case(factory: Callable[[], EngineCase]) -> PerfCase:
    state = factory()
    return state[1], lambda: close_engine_case(state)


def _save_load(format: str) -> PerfCase:
    state = save_load_case(format)
    return state[1], lambda: close_save_load_case(state)


def _typed_call() -> PerfCase:
    space = typed_space()
    return lambda: typed_call(space), space.drop


def _let_heavy() -> PerfCase:
    space = let_space()
    return lambda: let_heavy(space), space.drop


def _subscription_dispatch() -> PerfCase:
    state = subscription_dispatch_case()
    return state[3], lambda: close_subscription_case(state)


_CASES = {
    "alpha-unique": lambda: _engine_case(alpha_unique_case),
    "json-wire": _json_wire,
    "let-heavy": _let_heavy,
    "py-method-call": lambda: _engine_case(py_method_case),
    "save-load-fast": lambda: _save_load("fast"),
    "save-load-metta": lambda: _save_load("metta"),
    "sort-atom": lambda: _engine_case(sort_atom_case),
    "source-load": lambda: _engine_case(source_load_case),
    "space-digest": lambda: _engine_case(digest_case),
    "space-name": lambda: _engine_case(space_name_case),
    "structures-dispatch": lambda: (structures_dispatch, _no_teardown),
    "subscription-dispatch": _subscription_dispatch,
    "term-operators": _term_operators,
    "typed-call": _typed_call,
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


# Cases measured in STEADY STATE rather than cold, by running the operation
# once before the counters start.
#
# Only a workload that allocates one very large term in a SINGLE operation
# needs it, and alpha-unique is the only one: its measured interval contained
# the engine's one-time global-stack growth, and whether that stack expanded
# once or twice depended on where the process heap happened to start. The
# result was an instruction count with two modes 10.7% apart, deterministic per
# program image and selected by nothing in the tree: adding TEN INERT CLAUSES
# to engine/python.pl moved it from 4176751912 to 3772644013 and removing them
# moved it back, alternating, three rounds [measured 2026-08-16]. Its inference
# count is identical across both modes, so no logical work ever changed.
#
# That is why it is per case rather than for all of them. A warm-up changes
# what a workload MEANS when its second run differs from its first, and
# source-load's does: run twice, it measures redefining a thousand equations
# rather than defining them.
_WARM_UP = frozenset({"alpha-unique"})


def main(argv: Sequence[str] | None = None) -> int:
    """Run exactly one named workload."""
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=sorted(_CASES))
    parser.add_argument("--controlled", action="store_true")
    arguments = parser.parse_args(argv)
    operation, teardown = _CASES[arguments.case]()
    try:
        if arguments.case in _WARM_UP:
            operation()
        completed = _controlled(operation) if arguments.controlled else operation()
    finally:
        teardown()
    if completed <= 0:
        raise AssertionError(f"{arguments.case} completed no operations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
