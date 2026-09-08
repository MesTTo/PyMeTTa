"""Purpose: price the engine's interrupt poll and show what it did to a
measurement, so the counter door's subtraction is read from numbers rather than
argued: the same evaluation measured many times over, with the poll off, at the
shipped interval and dense, before and after the correction.
Assumes: `metta` imports (PYTHONPATH=extensions/python) and the engine boots;
  run as `python extensions/python/benchmarks/probes/interrupt_poll_accounting.py`
  from the repository root. `--raw` reports what the counters read WITHOUT the
  correction, which is what the tree measured before this door existed.
Guarantees: prints the calibrated charge, what a tick costs the counter as the
  VM spends it, the cost of an empty stats() block, and one row per poll
  interval with the distinct readings of one identical evaluation and the ticks
  those readings absorbed
  [measured 2026-09-08: at the shipped 100,000-inference interval, 20,000
  measurements of one 658-inference evaluation read ONE value with the
  correction and two without it, 37 of 3,000 landing 2 high; a tick costs 6
  inferences and an empty block 7, against 5 before the poll was accounted;
  the citations in extensions/python/metta/shim.pl's poll section and in
  _space_objects.py's _without_the_interrupt_poll read this probe;
  commit=5f92ecfb105f7a11d8f3b1a4c0a7e3b6d4b656a6].
Fails when: the interval is left where the probe put it -- it restores the
  shipped one on the way out, and a KeyboardInterrupt during a dense arm leaves
  the poll dense for the rest of the process.
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import sys

import janus_swi

from metta import MeTTa, S, parse

FORM = "(match {space} (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))"
#: The intervals the rows report: off, the shipped default, and dense enough
#: that a tick lands inside most measurements.
INTERVALS = (0, 100_000, 1_000)


def readings(space, query, runs, *, raw):
    """The distinct inference readings of one evaluation, and the ticks seen."""
    seen: dict[int, int] = {}
    ticks = 0
    for _ in range(runs):
        if raw:
            before = janus_swi.query_once("statistics(inferences, X)")["X"]
            space.eval(query)
            after = janus_swi.query_once("statistics(inferences, X)")["X"]
            count = after - before
            absorbed = 0
        else:
            with space.stats() as counters:
                space.eval(query)
            count, absorbed = counters.inferences, counters.heartbeats
        seen[count] = seen.get(count, 0) + 1
        ticks += absorbed
    return seen, ticks


def tick_cost(iterations=25_600):
    """What one tick costs the counter, as the VM itself spends it."""
    row = janus_swi.query_once(
        "set_prolog_flag(heartbeat, 0), "
        f"metta_py_heartbeat_bracket({iterations}, Bare, _), "
        "set_prolog_flag(heartbeat, 1000), "
        f"metta_py_heartbeat_bracket({iterations}, Armed, Ticks), "
        "set_prolog_flag(heartbeat, 100000), Spent is Armed - Bare"
    )
    return row["Spent"] / row["Ticks"] if row["Ticks"] else None


def direct_call_cost():
    """What the hook costs when a clause body calls it rather than the VM.

    One more than the VM spends, because a goal written `prolog:heartbeat` is
    module-qualified: the reason the charge is calibrated against the VM.
    """
    row = janus_swi.query_once(
        "set_prolog_flag(heartbeat, 0), "
        "statistics(inferences, B0), statistics(inferences, B1), Read is B1 - B0, "
        "statistics(inferences, C0), prolog:heartbeat, statistics(inferences, C1), "
        "set_prolog_flag(heartbeat, 100000), Cost is C1 - C0 - Read"
    )
    return row["Cost"]


def thread_fold(loops=1_000_000):
    """What another thread's work does to this thread's counter.

    A JOINED thread's inferences are added to the thread that joined it, and a
    detached one's are not, which is why a stats() block that waits for a
    worker counts the worker's work and one that merely overlaps a detached
    one does not.
    """
    joined = janus_swi.query_once(
        "statistics(inferences, B), "
        f"thread_create(forall(between(1, {loops}, _), true), _T, []), "
        "thread_join(_T, _), statistics(inferences, A), Delta is A - B"
    )["Delta"]
    detached = janus_swi.query_once(
        "statistics(inferences, B), message_queue_create(_Q), "
        f"thread_create(( forall(between(1, {loops}, _), true), "
        "thread_send_message(_Q, done) ), _T, [detached(true)]), "
        "thread_get_message(_Q, done), sleep(0.2), "
        "statistics(inferences, A), Delta is A - B, message_queue_destroy(_Q)"
    )["Delta"]
    return joined, detached


def main(argv):
    """Print the poll's price and what it does to a repeated measurement."""
    raw = "--raw" in argv
    runs = 4_000
    with MeTTa() as metta, metta.space("&poll-probe") as space:
        space.add(S.edge(1, 2), S.edge(2, 3), S.edge(3, 1))
        query = parse(FORM.format(space=space.name))
        space.eval(query)  # warm: a first evaluation compiles as well as runs
        charge = janus_swi.query_once("metta_py_heartbeat_charge(X)")["X"]
        print(f"calibrated charge: {charge} inferences a tick")
        print(f"measured tick cost: {tick_cost()} inferences a tick")
        print(f"a direct call of the hook: {direct_call_cost()} inferences")
        joined, detached = thread_fold()
        print(
            f"another thread's 2,000,000 inferences move this counter by "
            f"{joined} when joined and {detached} when detached"
        )
        with space.stats() as empty:
            pass
        print(f"an empty stats() block: {empty.inferences} inferences")
        for interval in INTERVALS:
            janus_swi.query_once(f"set_prolog_flag(heartbeat, {interval})")
            try:
                seen, ticks = readings(space, query, runs, raw=raw)
            finally:
                janus_swi.query_once("set_prolog_flag(heartbeat, 100000)")
            print(
                f"interval {interval:>7}: {runs} measurements read "
                f"{dict(sorted(seen.items()))}, absorbing {ticks} ticks"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
