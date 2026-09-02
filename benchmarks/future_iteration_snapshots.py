"""Purpose: count whole-space reads while a FutureSpace iterator waits.

The fixture starts a future whose one engine answer is held behind a space
write, preloads a fixed answer bag, and releases the computation after an
exact number of quiet subscription waits. The former iterator fetched and
decoded the complete bag before every wait, making P waits over N answers
cost theta(P*N). The target is theta(P+N): constant work per quiet wait and
each answer decoded a bounded number of times.

Run from ``extensions/python``::

    python -m benchmarks.future_iteration_snapshots

Guarantees:
  - ``polls`` is controlled by the subscription boundary rather than elapsed
    wall time [tested: test_future_iteration_does_not_resnapshot_per_quiet_wait;
    commit=WORKTREE]
  - every row verifies the complete ordered answer bag, so fewer reads cannot
    hide a lost or duplicated occurrence [tested:
    test_future_iteration_does_not_resnapshot_per_quiet_wait;
    commit=WORKTREE]
  - at 512 preloaded answers and 4/16/64 quiet waits, the former iterator made
    6/18/66 full reads and transported 3,074/9,218/33,794 atoms; the snapshot
    watermark implementation makes 2 full reads and transports 1,025 atoms at
    every wait count [measured: exact full-read and decoded-atom counts;
    command=cd extensions/python && PYTHONPATH=.
    /home/user/Dev/.venv-pypetta/bin/python -m
    benchmarks.future_iteration_snapshots 4 16 64 --atoms 512;
    fixture=512 preloaded atoms plus one released engine answer;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import itertools
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from metta import Atom, MeTTa, S, spawn
from metta.parallel import FutureSpace
from metta.subscribe import Subscription

POLLS = (4, 16, 64)
ATOMS = 512
_SERIALS = itertools.count()


@dataclass(frozen=True)
class Row:
    """One wait count and the complete snapshots it caused."""

    polls: int
    atoms: int
    snapshots: int
    transported: int
    milliseconds: float


def measure(polls: int, atoms: int = ATOMS) -> Row:
    """Iterate one blocked future after exactly ``polls`` quiet waits."""
    if polls < 1 or atoms < 1:
        msg = f"polls and atoms must be positive, got {polls} and {atoms}"
        raise ValueError(msg)

    owner = MeTTa().self
    gate = owner._new_space()
    expected = [S.future_item(index) for index in range(atoms)]
    original_atoms = FutureSpace.atoms
    original_wait = Subscription.wait
    snapshot_method = getattr(FutureSpace, "_iteration_snapshot", None)
    snapshots = 0
    transported = 0
    waits = 0

    with owner:
        future = spawn(S["peek-atom"](gate, S.future_release()))
    future.add(*expected)

    def counted_atoms(subject: FutureSpace) -> list[Atom]:
        nonlocal snapshots, transported
        answer = original_atoms(subject)
        if subject is future:
            snapshots += 1
            transported += len(answer)
        return answer

    def paced_wait(subject: Subscription, timeout: float | None = None) -> Any:
        nonlocal waits
        if subject.space != future.name:
            return original_wait(subject, timeout)
        waits += 1
        if waits == polls:
            gate.add(S.future_release())
        return original_wait(subject, 0 if waits < polls else timeout)

    def counted_snapshot(subject: FutureSpace) -> tuple[list[Atom], int]:
        nonlocal snapshots, transported
        if snapshot_method is None:
            msg = "FutureSpace has no consistent iteration snapshot"
            raise RuntimeError(msg)
        answer, watermark = snapshot_method(subject)
        if subject is future:
            snapshots += 1
            transported += len(answer)
        return answer, watermark

    FutureSpace.atoms = counted_atoms  # type: ignore[method-assign, assignment]
    Subscription.wait = paced_wait  # type: ignore[method-assign, assignment]
    if snapshot_method is not None:
        FutureSpace._iteration_snapshot = counted_snapshot  # type: ignore[method-assign, assignment]
    started = time.perf_counter_ns()
    try:
        observed = list(future)
    finally:
        FutureSpace.atoms = original_atoms  # type: ignore[method-assign]
        Subscription.wait = original_wait  # type: ignore[method-assign]
        if snapshot_method is not None:
            FutureSpace._iteration_snapshot = snapshot_method  # type: ignore[method-assign]
        gate.drop()
    elapsed = time.perf_counter_ns() - started

    wanted = [*expected, S.future_release()]
    if observed != wanted:
        msg = f"future yielded {observed!r}, expected {wanted!r}"
        raise AssertionError(msg)
    if waits < polls:
        msg = f"future settled after {waits} waits, before the requested {polls}"
        raise AssertionError(msg)
    return Row(polls, atoms + 1, snapshots, transported, elapsed / 1_000_000)


def rows(
    polls: Sequence[int] = POLLS,
    atoms: int = ATOMS,
) -> list[Row]:
    """Measure each quiet-wait count with the same initial answer bag."""
    return [measure(count, atoms) for count in polls]


def main(argv: Sequence[str] | None = None) -> int:
    """Print full reads and transported atoms for each wait count."""
    parser = argparse.ArgumentParser()
    parser.add_argument("polls", type=int, nargs="*", default=POLLS)
    parser.add_argument("--atoms", type=int, default=ATOMS)
    arguments = parser.parse_args(argv)
    for row in rows(arguments.polls, arguments.atoms):
        print(
            f"polls={row.polls:3d} atoms={row.atoms:4d} "
            f"snapshots={row.snapshots:3d} transported={row.transported:7d} "
            f"elapsed={row.milliseconds:9.3f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
