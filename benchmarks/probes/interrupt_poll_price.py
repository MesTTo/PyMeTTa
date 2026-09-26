"""Purpose: price the engine's interrupt poll in time: what its crossings cost
a spinning loop, and how late a signal handler runs after its signal.
Assumes: `metta` imports (PYTHONPATH=extensions/python) and the engine boots on
  a host carrying swi-heartbeat-fires-only-at-exits.patch; run as
  `python extensions/python/benchmarks/probes/interrupt_poll_price.py` from the
  repository root. ROUNDS (default 9) and STEPS (default 20,000,000) size the
  cost rows.
Guarantees: prints, for an exit-free last-call loop and a failure-driven loop
  of STEPS iterations, the process CPU time with the poll never due and at
  intervals of 100,000, 10,000 and 1,000, the minimum of ROUNDS interleaved
  rounds, with the cost of one crossing derived from each; then the lateness
  of twenty SIGALRM handlers raised into a spinning goal at 100,000 and 10,000
  [measured 2026-09-26T23:35:22+10:00: a crossing costs under a
  microsecond, read at 1,000 where the crossings outweigh the noise (0.88
  and 0.74), so the poll costs under 0.1% of a 40M inferences/s loop at
  100,000, where one interval is 2.5 ms, and handlers ran a median 0.20 ms
  late at 100,000 and 0.04 ms at 10,000].
Fails when: the box is loaded enough that one round's noise exceeds the
  crossings at 100,000 and 10,000; read the per-crossing figure at 1,000.
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import signal
import sys
import time

import janus_swi

from benchmarks import decide_width
from metta import Space

ROUNDS = int(os.environ.get("ROUNDS", "9"))
STEPS = int(os.environ.get("STEPS", "20000000"))
#: Never due: the flag is armed and checked exactly as at any interval.
OFF = 10**15
INTERVALS = (100_000, 10_000, 1_000)
SHAPES = {"last-call": f"spin_to(0, {STEPS})", "fail-driven": f"fail_to({STEPS})"}


def run(goal: str) -> tuple[float, int]:
    """Process CPU seconds and inferences one goal spends."""
    before = janus_swi.query_once("statistics(inferences, I)")["I"]
    started = time.process_time()
    janus_swi.query_once(goal)
    spent = time.process_time() - started
    after = janus_swi.query_once("statistics(inferences, I)")["I"]
    return spent, after - before


def cost_rows() -> None:
    """The minimum CPU time per shape and interval, rounds interleaved."""
    best: dict[tuple[str, int], float] = {}
    counts: dict[str, int] = {}
    for _ in range(ROUNDS):
        for interval in (OFF, *INTERVALS):
            janus_swi.query_once("set_prolog_flag(heartbeat, I)", {"I": interval})
            for shape, goal in SHAPES.items():
                spent, count = run(goal)
                best[shape, interval] = min(best.get((shape, interval), spent), spent)
                counts[shape] = count
    for shape in SHAPES:
        base = best[shape, OFF]
        rate = counts[shape] / base
        print(f"{shape}: {counts[shape]} inferences, never due {base * 1e3:.1f} ms "
              f"({rate / 1e6:.1f}M inferences/s)")
        for interval in INTERVALS:
            extra = best[shape, interval] - base
            print(f"  every {interval}: {best[shape, interval] * 1e3:.1f} ms, "
                  f"{extra / base * 100:+.2f}%, {extra / (counts[shape] / interval) * 1e6:.2f} us "
                  f"a crossing, one interval {interval / rate * 1e3:.2f} ms")


def lateness_rows() -> None:
    """How late a raising SIGALRM handler runs after its timer is due."""
    fired = [0.0]

    def stop(*_: object) -> None:
        fired[0] = time.perf_counter()
        msg = "stop"
        raise RuntimeError(msg)

    previous = signal.signal(signal.SIGALRM, stop)
    try:
        for interval in INTERVALS[:2]:
            janus_swi.query_once("set_prolog_flag(heartbeat, I)", {"I": interval})
            late = []
            for k in range(20):
                due = 0.05 + 0.01 * k
                started = time.perf_counter()
                signal.setitimer(signal.ITIMER_REAL, due)
                try:
                    janus_swi.query_once("forever")
                except Exception:  # noqa: BLE001  -- a raw janus call raises the seat's signal as PrologError
                    late.append(fired[0] - (started + due))
            late.sort()
            print(f"late at {interval}: min {late[0] * 1e3:.2f} ms, median "
                  f"{late[len(late) // 2] * 1e3:.2f} ms, max {late[-1] * 1e3:.2f} ms "
                  f"over {len(late)} signals")
    finally:
        signal.signal(signal.SIGALRM, previous)


def main() -> int:
    """Print both tables and restore the shipped interval."""
    decide_width("measures")
    with Space("&poll-price"):
        janus_swi.consult("poll_price", data="""
            spin_to(N, N) :- !.
            spin_to(I, N) :- I1 is I+1, spin_to(I1, N).
            fail_to(N) :- ( between(1, N, _), fail ; true ).
            forever :- forever.
        """)
        try:
            cost_rows()
            lateness_rows()
        finally:
            janus_swi.query_once("set_prolog_flag(heartbeat, 100000)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
