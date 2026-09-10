"""Purpose: verify native bound watches through completion and engine destruction.

Guarantees: nested commit, failure and exception rollback keep the mirror
suspended until the outer transaction ends, and destroying the yielded engine
does not enter a listener on a discarded query frame [tested:
test_bound_watches_transfer_until_outer_completion; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
Owns resources: each isolated child destroys its yielded native engine and
drops its MeTTa space; the parent joins every child.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def _assert_suspended(value: int) -> None:
    import threading

    from metta._catalog import bounds

    assert set(bounds._PENDING_TRANSACTIONS) == {threading.get_ident()}
    assert bounds.config.display_rows == value
    assert not bounds._MIRROR


def _probe(mode: str, depth: int) -> dict:
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    sys.path.insert(0, str(ROOT / "extensions/python"))
    from _workspace import on_path

    on_path()
    import janus_swi as janus

    from metta import MeTTa
    from metta._catalog import bounds

    with MeTTa():
        original = bounds.config.display_rows
        events = []
        started = bounds.bound_transaction_started
        finished = bounds.bound_transaction_finished

        def start():
            events.append("start")
            started()

        def finish():
            events.append("finish")
            finished()

        bounds.bound_transaction_started = start
        bounds.bound_transaction_finished = finish
        # The observer reads through Python while the native transaction is
        # active, so an early cache fill or retirement is observable here.
        janus.consult("bound_transaction_frames", data=r'''
            :- meta_predicate bound_frames_outer(+,0), bound_frames_exit(+,0).
            bound_frames_suspended(Value) :-
                nb_current('$metta_bound_transaction', _),
                py_call(MODULE:'_assert_suspended'(Value), _).
            bound_frames_write(Value) :-
                'add-atom'('&metta',[limit,'display-rows',Value],_),
                bound_frames_suspended(Value).
            bound_frames_nested(0) :- !, bound_frames_write(7).
            bound_frames_nested(Depth) :-
                Next is Depth-1,
                transaction((bound_frames_nested(Next),
                             bound_frames_suspended(7))).
            bound_frames_exit(commit, Goal) :- transaction(Goal).
            bound_frames_exit(fail, Goal) :-
                \+ transaction((call(Goal), fail)).
            bound_frames_exit(throw, Goal) :-
                catch(transaction((call(Goal), throw(bound_frames))),
                      bound_frames, true).
            bound_frames_outer(plain, Goal) :- transaction(Goal).
            bound_frames_outer(options, Goal) :- transaction(Goal, []).
            bound_frames_outer(constraint, Goal) :-
                transaction(Goal, true, bound_frames).
            bound_frames_outer(snapshot, Goal) :- snapshot(Goal).
            bound_frames_case(nested, Depth, _) :-
                bound_frames_nested(Depth).
            bound_frames_case(rollback(Mode), _, Original) :-
                transaction((bound_frames_exit(Mode, bound_frames_write(7)),
                             bound_frames_suspended(Original),
                             bound_frames_write(9))).
            bound_frames_case(outer(Mode), _, _) :-
                bound_frames_outer(Mode,
                    (bound_frames_nested(1), bound_frames_suspended(7))).
            bound_frames_case(engines(Mode), _, Original) :-
                bound_frames_exit(Mode, bound_frames_engines(Original)).
            bound_frames_engines(Original) :-
                bound_frames_write(7),
                setup_call_cleanup(
                    engine_create(ready,
                        (transaction((
                            'add-atom'('&metta',[limit,'chunk-cap',8],_),
                            py_call(MODULE:'_assert_suspended'(Original),_))),
                         engine_yield(ready)), Inner),
                    engine_next(Inner, ready), engine_destroy(Inner)),
                bound_frames_suspended(7).
            bound_frames_probe(Mode, Depth, Original) :-
                setup_call_cleanup(
                    engine_create(ready,
                        (bound_frames_case(Mode, Depth, Original),
                         \+ nb_current('$metta_bound_transaction', _),
                         engine_yield(ready)), Engine),
                    engine_next(Engine, ready),
                    engine_destroy(Engine)),
                \+ nb_current('$metta_bound_transaction', _).
        '''.replace("MODULE", repr(__name__)))
        try:
            result = janus.query_once(
                f"bound_frames_probe({mode},Depth,Original)",
                {"Depth": depth, "Original": original},
            )
            assert result["truth"]
            assert events == (["start", "start", "finish", "finish"]
                              if mode.startswith("engines") else ["start", "finish"])
            assert not bounds._PENDING_TRANSACTIONS
            expected = (original if mode in {"outer(snapshot)", "engines(fail)", "engines(throw)"}
                        else 9 if mode.startswith("rollback") else 7)
            assert bounds.config.display_rows == expected
            assert bounds._MIRROR["display_rows"] == expected
            if mode.startswith("engines"):
                assert bounds.config.chunk_cap == 8
            return {"mode": mode, "depth": depth, "events": events, "value": expected}
        finally:
            bounds.bound_transaction_started = started
            bounds.bound_transaction_finished = finished


@pytest.mark.parametrize("mode,depth", [
    *(("nested", depth) for depth in range(1, 5)),
    *((f"rollback({mode})", 1) for mode in ("fail", "throw")),
    *((f"outer({mode})", 1) for mode in ("plain", "options", "constraint", "snapshot")),
    *((f"engines({mode})", 1) for mode in ("commit", "fail", "throw")),
])
def test_bound_watches_transfer_until_outer_completion(mode, depth):
    """A real limit write survives the reported finish, yield, destroy order."""
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), mode, str(depth)],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert (receipt["mode"], receipt["depth"]) == (mode, depth)


if __name__ == "__main__":
    print(json.dumps(_probe(sys.argv[1], int(sys.argv[2]))))
