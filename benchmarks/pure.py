"""Purpose: run one engine-free workload for perf instructions:u.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import argparse
import os
from collections.abc import Sequence

from benchmarks.workloads import term_operators, wire_atom, wire_codec


def _wire_codec():
    return wire_codec(wire_atom())


_CASES = {
    "term-operators": term_operators,
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
    operation = _CASES[arguments.case]
    completed = _controlled(operation) if arguments.controlled else operation()
    if completed <= 0:
        raise AssertionError(f"{arguments.case} completed no operations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
