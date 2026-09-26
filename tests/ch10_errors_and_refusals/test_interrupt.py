"""Purpose: a signal stops a running evaluation wherever it runs, and the
process and its engine carry on afterwards.

The runtime arms the engine's interrupt poll at startup (control.pl's
prolog:heartbeat/0), which crosses into Python every heartbeat interval of
engine work so CPython can run the handlers it has queued: Ctrl-C raises
KeyboardInterrupt, and a handler of the program's own raises its own
exception, from the evaluation it interrupted.

Assumes: a POSIX host, and an engine host carrying
  swi-heartbeat-fires-only-at-exits.patch, which delivers the poll in loops
  that exit nothing, swi-engine-leaves-a-freed-signal-stack.patch, without
  which a Ctrl-C after a cursor corrupts the heap, and
  janus-conversion-drops-a-raised-exception.patch, without which a handler
  raising during a conversion crashes the process.
Guarantees:
  - Ctrl-C and a raising SIGALRM handler each stop an exit-free self-call,
    the consumer's runaway closure (its finding 3), a loop that exits, a
    streaming cursor, which runs in an engine, and a transaction body, within
    LATENCY of the signal; the process then evaluates (+ 1 2) and exits 0,
    and a stopped transaction leaves no atom it added
    [tested 2026-09-26T23:30:48+10:00: test_a_signal_stops_every_workload]
  - under a time bound as well, whichever of the signal and the bound comes
    first stops the evaluation and the rest of the guarantee above holds
    [tested 2026-09-26T23:30:48+10:00: test_signals_and_time_bounds_compose]
Owns resources: one child process per case, each joined or killed.
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

import contextlib
import json
import os
import signal
import subprocess
import sys
import textwrap
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

#: Seconds from a signal to the evaluation's exception. The poll takes the
#: signal within one interval of engine work, about 2 ms at the default, and
#: the rest is unwinding the stopped evaluation, which for the runaway closure
#: is millions of frames, and whatever else this box is running.
LATENCY = 2.0

#: The child: set up the five workloads, say READY, run one, report.
CHILD = textwrap.dedent(
    """
    import json, os, signal, sys, time
    from metta import MeTTa, S, V, equation

    workload, kind, bound = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    m = MeTTa().space("&interrupt-probe")
    m.run("(= (loop-forever $n) (loop-forever $n))")
    m.run("(= (count-down $n) (if (== $n 0) done (count-down (- $n 1))))")
    m.add(S.item(1))
    m.add(S.SUB(S.dog, S.mammal))

    @m.rules
    def closure(a, b, c):
        yield equation(S.subo(a, b)).to(S.SUB(a, b))
        yield equation(S.subo(a, b)).to(S["and"](S.SUB(a, c), S.subo(c, b)))

    def raise_alarm(*_):
        raise RuntimeError("alarm")

    if kind == "alarm":
        signal.signal(signal.SIGALRM, raise_alarm)
    limits = {} if bound is None else {"timeout": bound}
    workloads = {
        "exit-free": lambda: m.eval(S["loop-forever"](1), **limits),
        "finding-3": lambda: m.eval(S.subo(S.dog, V.y), **limits),
        "exits": lambda: m.eval(S["count-down"](10**12), **limits),
        "cursor": lambda: bool(m.match(S.item(V.x), where=S["loop-forever"](V.x),
                                       **limits)),
        "transaction": lambda: m.transaction(
            lambda: (m.add(S.marker(1)), m.eval(S["loop-forever"](1), **limits))),
    }
    print("READY", os.getpid(), flush=True)
    try:
        workloads[workload]()
        outcome, message = "finished", ""
    except BaseException as error:
        outcome, message = type(error).__name__, str(error)
    stopped = time.time()
    # A signal that lands after the workload stopped is the parent's late
    # delivery, not something this evaluation owes an answer to.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGALRM, signal.SIG_IGN)
    print(json.dumps({
        "outcome": outcome, "message": message, "stopped": stopped,
        "answers": m.eval(S["+"](1, 2)) == [3],
        "marker": bool(m.match(S.marker(V.x))),
    }), flush=True)
    """
)

WORKLOADS = ("exit-free", "finding-3", "exits", "cursor", "transaction")
SIGNALS = {"sigint": (signal.SIGINT, "KeyboardInterrupt"),
           "alarm": (signal.SIGALRM, "RuntimeError")}


def stop(workload, kind, delay, bound=None):
    """Run one workload in a child, signal it after `delay`, read its report.

    The signal goes to the pid the child reports rather than to the process
    this starts, which conftest.py wraps in bounded.sh.
    """
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, workload, kind, json.dumps(bound)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        ready = child.stdout.readline().split()
        assert ready[:1] == ["READY"], child.stderr.read()
        time.sleep(delay)
        sent = time.time()
        with contextlib.suppress(ProcessLookupError):  # a bound stopped it first
            os.kill(int(ready[1]), SIGNALS[kind][0])
        out, err = child.communicate(timeout=60)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()
    assert child.returncode == 0, f"exit {child.returncode}\n{out}\n{err}"
    report = json.loads(out.strip().splitlines()[-1])
    return report, report["stopped"] - sent


@pytest.mark.parametrize("kind", sorted(SIGNALS))
@pytest.mark.parametrize("workload", WORKLOADS)
def test_a_signal_stops_every_workload(workload, kind):
    """The signal's exception stops the workload, and the process carries on."""
    report, latency = stop(workload, kind, delay=0.3)
    assert report["outcome"] == SIGNALS[kind][1], report
    assert latency < LATENCY, f"stopped {latency:.2f}s after the signal"
    assert report["answers"], "the engine did not answer after the stop"
    assert not report["marker"], "a stopped transaction left its write"


@settings(max_examples=12, deadline=None)
@given(
    workload=st.sampled_from(WORKLOADS),
    kind=st.sampled_from(sorted(SIGNALS)),
    delay=st.floats(min_value=0.05, max_value=1.2),
    bound=st.one_of(st.none(), st.floats(min_value=0.2, max_value=1.5)),
)
def test_signals_and_time_bounds_compose(workload, kind, delay, bound):
    """Whichever of a signal and a time bound comes first stops the run.

    Each is late by its own path: the signal by up to one poll interval and
    the unwinding, the time bound by stack shifts, which hold signals back
    while they move the stacks. So the outcome is decided only where one
    comes first by more than LATENCY, and the process, its engine and the
    transaction's space are checked either way.
    """
    report, _ = stop(workload, kind, delay, bound)
    signalled = SIGNALS[kind][1]
    assert report["outcome"] in {signalled, "TimeLimitError"}, report
    if bound is None or delay + LATENCY < bound:
        assert report["outcome"] == signalled, report
    elif bound + LATENCY < delay:
        assert report["outcome"] == "TimeLimitError", report
    assert report["answers"], "the engine did not answer after the stop"
    assert not report["marker"], "a stopped transaction left its write"
