"""Purpose: retain worker ownership after a nonwaiting or failed pool close.

Guarantees:
  - close(wait=True) joins even after an earlier nonwaiting close
    [tested: test_waiting_close_joins_after_nonwaiting_close; commit=089bc6036ae5039bce3963d8b4e80ecaf04dfb49]
"""

import threading

import janus_swi

from metta.parallel import EnginePool


def test_waiting_close_joins_after_nonwaiting_close(monkeypatch):
    """Cancellation of queued work does not erase ownership of worker detach."""
    entered = threading.Event()
    release_work = threading.Event()
    detaching = threading.Event()
    release_detach = threading.Event()
    detached = threading.Event()
    close_started = threading.Event()
    close_finished = threading.Event()
    failures = []
    original = janus_swi.detach_engine

    def detach():
        detaching.set()
        release_detach.wait()
        original()
        detached.set()

    def work():
        entered.set()
        release_work.wait()

    monkeypatch.setattr(janus_swi, "detach_engine", detach)
    pool = EnginePool(1)
    running = pool.submit(work)
    assert entered.wait(2)
    cancelled = pool.submit(lambda: None)
    assert cancelled.cancel()
    pool.close(wait=False)
    release_work.set()
    assert detaching.wait(2)

    def close():
        close_started.set()
        try:
            pool.close()
        except BaseException as exc:
            failures.append(exc)
        finally:
            close_finished.set()

    closer = threading.Thread(target=close)
    closer.start()
    try:
        assert close_started.wait(2)
        assert not close_finished.wait(0.1), (
            "a later waiting close must join workers after close(wait=False)"
        )
    finally:
        release_work.set()
        release_detach.set()
        closer.join(2)
        for worker in pool._started:  # Ensure the red control also releases its engines.
            worker.join(2)
    assert not failures
    assert detached.is_set()
    assert running.done() and cancelled.cancelled()
    assert close_finished.is_set()
