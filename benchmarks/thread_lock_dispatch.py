"""Purpose: preserve and rerun the Janus call-lock selection measurements.

The probe decides whether an attached Janus engine chooses its call lock once
or on every call.

Assumes:
  - run from ``extensions/python`` so the ``benchmarks`` package is importable
  - ``--instructions`` needs the same unprivileged ``perf instructions:u``
    access as ``benchmarks.check_instructions``

The historical result is retained here because its original scratch probes
were not tracked.  The promoted cases below reproduce the two comparisons:

* direct global-lock selection: 43 ns; per-call thread-id dispatch: 72 ns;
  one thread-local lock read: 59 ns;
* changing the home-thread arm from the direct lock to one thread-local read
  added 15.5 million retired instructions, 0.61%, to ``space-name``.

Those figures were measured on 2026-08-15 and were first recorded in
``extensions/python/metta/_engine.py`` at
da5f3524fb671030928b8e1858580c0cd3a3a6a2.  Rerun the equivalent promoted
probes with::

    python -m benchmarks.thread_lock_dispatch --micro
    python -m benchmarks.thread_lock_dispatch --instructions

On the promoted probe's 2026-09-01 toolchain those commands measured
10.6/35.8/28.6 ns respectively, and +17,142,305 instructions (+0.44%) for
the thread-local arm.  Absolute costs moved with Python and the engine image;
both A/Bs preserve the decision's direction [measured: min of seven timeit
rounds and min of three controlled perf rounds; command=python -m
benchmarks.thread_lock_dispatch --micro and python -m
benchmarks.thread_lock_dispatch --instructions; fixture=CPython 3.14 with
the provisioned repository engine; commit=8fc1a4e204be4200862af7a3819a28a0d6279ea1].
"""

from __future__ import annotations

import argparse
import sys
import threading
import timeit
from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Any

from benchmarks.engine_workloads import close_engine_case, space_name_case
from benchmarks.pure import _controlled
from metta._engine import _CALL_LOCKS, _LOCK, Runtime
from metta.testing import measure_instructions

_MICRO_CALLS = 10_000_000
_MICRO_ROUNDS = 7
_INSTRUCTION_ROUNDS = 3
_ORIGINAL_THREAD_LOCK = Runtime._thread_lock


def _direct_lock() -> AbstractContextManager[Any]:
    return _LOCK


_HOME_IDENT = threading.get_ident()


def _per_call_dispatch() -> AbstractContextManager[Any]:
    return _LOCK if threading.get_ident() == _HOME_IDENT else _CALL_LOCKS.lock


def _thread_local_lock() -> AbstractContextManager[Any]:
    return _CALL_LOCKS.lock


def _minimum_ns(callable_: object) -> float:
    samples = timeit.repeat(callable_, number=_MICRO_CALLS, repeat=_MICRO_ROUNDS)
    return min(samples) * 1_000_000_000 / _MICRO_CALLS


def _micro_report() -> None:
    print(f"direct global lock: {_minimum_ns(_direct_lock):.1f} ns")
    print(f"per-call thread-id dispatch: {_minimum_ns(_per_call_dispatch):.1f} ns")
    print(f"thread-local lock read: {_minimum_ns(_thread_local_lock):.1f} ns")


def _thread_local_home(self: Runtime) -> AbstractContextManager[Any] | None:
    """The rejected A/B arm: add one TLS read to the home-engine path."""
    if threading.current_thread() is self._home_thread:
        return _CALL_LOCKS.lock
    return _ORIGINAL_THREAD_LOCK(self)


def _instruction_case(mode: str, *, controlled: bool) -> int:
    if mode == "thread-local":
        Runtime._thread_lock = _thread_local_home
    state = space_name_case()
    try:
        operation = state[1]
        return _controlled(operation) if controlled else operation()
    finally:
        close_engine_case(state)


def _instruction_report() -> None:
    samples: dict[str, list[int]] = {}
    for mode in ("direct", "thread-local"):
        samples[mode] = measure_instructions(
            [
                sys.executable,
                "-m",
                "benchmarks.thread_lock_dispatch",
                "--case",
                mode,
                "--controlled",
            ],
            rounds=_INSTRUCTION_ROUNDS,
            controlled=True,
        )
    direct = min(samples["direct"])
    thread_local = min(samples["thread-local"])
    delta = thread_local - direct
    print(f"direct: samples={samples['direct']} min={direct}")
    print(f"thread-local: samples={samples['thread-local']} min={thread_local}")
    print(f"delta: {delta:+d} instructions ({delta / direct:+.2%})")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one controlled case or report either promoted comparison."""
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--micro", action="store_true")
    action.add_argument("--instructions", action="store_true")
    action.add_argument("--case", choices=("direct", "thread-local"))
    parser.add_argument("--controlled", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.controlled and arguments.case is None:
        parser.error("--controlled applies only to --case")
    if arguments.micro:
        _micro_report()
    elif arguments.instructions:
        _instruction_report()
    else:
        completed = _instruction_case(arguments.case, controlled=arguments.controlled)
        if completed <= 0:
            msg = "space-name completed no operations"
            raise AssertionError(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
