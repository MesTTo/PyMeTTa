"""Purpose: show the engine's interrupt poll staying out of a measurement: the
same evaluation measured many times over, with the poll off, at the shipped
interval and dense, through stats() and through the raw counter.
Assumes: `metta` imports (PYTHONPATH=extensions/python) and the engine boots,
  which it does only on a host carrying
  swi-heartbeat-inferences-charged-to-the-program.patch; run as
  `python extensions/python/benchmarks/probes/interrupt_poll_accounting.py`
  from the repository root.
Guarantees: prints what the poll's ticks add to a fixed loop's count, what a
  thread this one joins or only waits beside adds to its counter, the cost of
  an empty stats() block with the thread's tick record and without it, and
  one row per poll interval with the distinct readings of one identical
  evaluation through stats() and through statistics/2, and the ticks the
  stats() readings absorbed
  [measured 2026-09-26T23:30:44+10:00: the poll added 0 inferences to a
  51,200-inference loop over 51 ticks; a joined 2,000,000-inference thread
  moved this counter by 2,000,015 and a detached one by 6; an empty block
  read 7, and 8 in a thread without a tick record; 4,000 measurements of one
  evaluation read one value at each of 0, 100,000 and 1,000, 666 through
  stats() and 665 raw, absorbing 0, 26 and 2,604 ticks].
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


def readings(space, query, runs):
    """The distinct readings of one evaluation, through stats() and raw, and the ticks."""
    through_stats: dict[int, int] = {}
    raw: dict[int, int] = {}
    ticks = 0
    for _ in range(runs):
        with space.stats() as counters:
            space.eval(query)
        through_stats[counters.inferences] = through_stats.get(counters.inferences, 0) + 1
        ticks += counters.heartbeats
        before = janus_swi.query_once("statistics(inferences, X)")["X"]
        space.eval(query)
        count = janus_swi.query_once("statistics(inferences, X)")["X"] - before
        raw[count] = raw.get(count, 0) + 1
    return through_stats, raw, ticks


def tick_cost(iterations=25_600):
    """What the poll's ticks add to a fixed loop's count, and how many ran."""
    row = janus_swi.query_once(
        "set_prolog_flag(heartbeat, 0), "
        "statistics(inferences, _B0), forall(between(1, Iterations, _), true), "
        "statistics(inferences, _B1), "
        "set_prolog_flag(heartbeat, 1000), metta_py_heartbeat_ticks(_T0), "
        "statistics(inferences, _A0), forall(between(1, Iterations, _), true), "
        "statistics(inferences, _A1), metta_py_heartbeat_ticks(_T1), "
        "set_prolog_flag(heartbeat, 100000), "
        "Added is (_A1 - _A0) - (_B1 - _B0), Ticks is _T1 - _T0",
        {"Iterations": iterations},
    )
    return row["Added"], row["Ticks"]


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


def empty_block(space):
    """What an empty stats() block reads, warm."""
    with space.stats():
        pass
    with space.stats() as empty:
        pass
    return empty.inferences


def without_the_record(space):
    """An empty block in a thread whose tick record was never written.

    Its read is one inference dearer there, the reason control.pl starts every
    thread's record at zero; the record is put back afterwards.
    """
    held = janus_swi.query_once("nb_getval('$metta_heartbeat_ticks', Held)")["Held"]
    janus_swi.query_once("nb_delete('$metta_heartbeat_ticks')")
    try:
        return empty_block(space)
    finally:
        janus_swi.query_once("nb_setval('$metta_heartbeat_ticks', Held)", {"Held": held})


def main():
    """Print what the poll adds to a count, and what a repeated measurement reads."""
    runs = 4_000
    with MeTTa() as metta, metta.space("&poll-probe") as space:
        space.add(S.edge(1, 2), S.edge(2, 3), S.edge(3, 1))
        query = parse(FORM.format(space=space.name))
        space.eval(query)  # warm: a first evaluation compiles as well as runs
        added, ticks = tick_cost()
        print(f"the poll adds {added} inferences to a fixed loop over {ticks} ticks")
        joined, detached = thread_fold()
        print(
            f"another thread's 2,000,000 inferences move this counter by "
            f"{joined} when joined and {detached} when detached"
        )
        print(
            f"an empty stats() block: {empty_block(space)} inferences, and "
            f"{without_the_record(space)} in a thread without a tick record"
        )
        for interval in INTERVALS:
            janus_swi.query_once(f"set_prolog_flag(heartbeat, {interval})")
            try:
                seen, raw, ticks = readings(space, query, runs)
            finally:
                janus_swi.query_once("set_prolog_flag(heartbeat, 100000)")
            print(
                f"interval {interval:>7}: {runs} measurements read "
                f"{dict(sorted(seen.items()))} through stats() and "
                f"{dict(sorted(raw.items()))} raw, absorbing {ticks} ticks"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
