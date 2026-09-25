"""Purpose: keep Answers caller-position lookup constant after one derivation.

Guarantees:
  - position derivation is ONE preprocessing cost rather than one scan per
    loop, so a call site's bytecode offset does not multiply iteration work.
    Stated as work rather than as time on purpose: the wall-clock form of this
    claim, and the benchmark test that carried it, were replaced because the
    same code answered a ratio of 0.9 here and 8.5 on a shared runner, so the
    bar was measuring the machine [tested:
    test_answer_iteration_derives_each_call_site_once;
    commit=0ffac1f272c65d1c3742a2bfb824538e426c264a]
  - cached position metadata does not keep generated code alive: nothing
    the position cache holds reaches a cached call site's code object
    through a strong reference [tested 2026-09-25T12:45:29+10:00:
    test_answer_position_cache_does_not_own_generated_code]
  - a collection that frees a cached code object while the storing thread
    holds the cache's lock lets that thread go on; with the weakref callback
    the cache used to carry, the thread waited on its own lock until killed
    [tested: test_a_collection_inside_the_position_store_does_not_deadlock;
    commit=1ae276864217e62c9a061685d651ebf0be65b76f]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import ast
import gc
import os
import subprocess
import sys
from typing import ClassVar

import pytest

import metta._spaces.intents as _lint_events
from benchmarks.answer_iteration_cost import driver
from metta._roots import workspace
from metta._spaces.results import Answers

# A collection forced at the cache's locked store, which is what a collection
# an allocation there starts does, while the only thing keeping a cached code
# object alive is a function and its globals referencing each other. The
# collecting cache goes in first: building it from the old one would call its
# __setitem__ per copied item and collect before any lock is held.
_COLLECTION_INSIDE_THE_STORE = '''
import gc
import sys
from collections import OrderedDict

import metta._spaces.intents as intents

gc.disable()


class CollectingCache(OrderedDict):
    def __setitem__(self, key, value):
        gc.collect()
        super().__setitem__(key, value)


intents._POSITION_CACHE = CollectingCache()
namespace = {}
exec(compile("import sys\\ndef where():\\n    return sys._getframe()\\n", "<abandoned>", "exec"), namespace)
intents._position(namespace["where"]())
del namespace
intents._position(sys._getframe())
print("returned")
'''


def test_answer_iteration_derives_each_call_site_once(monkeypatch):
    """Position derivation is one preprocessing cost, not one scan per loop.

    This asked wall clock whether the derivation had been cached, and wall
    clock does not decide anything in this tree: the same code answered a
    ratio of 0.9 here and 8.5 on a shared runner, so the bar was measuring the
    machine. Count the work instead. A per-iteration scan parses the caller's
    source every time; a cached one parses it once however many times the loop
    runs, and that is a number no runner can move.
    """
    parses = 0
    original = _lint_events.ast.parse

    def counting_parse(*arguments: object, **keywords: object) -> ast.AST:
        nonlocal parses
        parses += 1
        return original(*arguments, **keywords)

    drive, positions = driver(1_000)
    answers = Answers([1], space="&answer-iteration-cost")
    assert drive(answers, 1) == 1  # warm the cache the way a caller would
    monkeypatch.setattr(_lint_events.ast, "parse", counting_parse)
    assert drive(answers, 500) == 500

    assert positions > 1_000, "the padded driver must have many source positions"
    assert parses == 0, (
        f"a warmed call site parsed its source {parses} time(s) over 500 "
        f"iterations; the derivation is not cached"
    )


def test_resolving_a_global_name_does_not_materialise_the_caller_locals():
    """Reading f_locals copies every local, so its cost rides on the caller.

    CPython builds that snapshot on each access before PEP 667 and retains it
    on the frame, which costs time proportional to the caller's size and keeps
    every local alive until the frame dies. Neither belongs in a loop that runs
    once per answer. A frame whose f_locals raises is the only way to assert
    the snapshot was never taken; recomputing the code's own condition would
    agree with it however the code changed.
    """

    def sample(local_name: int) -> None:
        pass

    class Tripwire:
        f_code = sample.__code__
        f_globals: ClassVar[dict[str, object]] = {"module_level": "seen"}

        @property
        def f_locals(self) -> dict[str, object]:
            msg = "resolving a name materialised the caller's locals"
            raise AssertionError(msg)

    frame = Tripwire()
    # A name the caller does not own is resolved without the snapshot.
    assert _lint_events._name_in_frame(frame, "module_level", None) == "seen"
    assert _lint_events._name_in_frame(frame, "absent_everywhere", "fallback") == "fallback"
    # A name it does own still reads locals, because shadowing decides there.
    with pytest.raises(AssertionError, match="materialised the caller"):
        _lint_events._name_in_frame(frame, "local_name", None)


def _strongly_reachable(root: object) -> list[object]:
    """Every object ``root`` keeps alive, its strong references followed to the end.

    A weak reference reports only its callback to the collector, so the walk
    stops at one [measured 2026-09-25T10:05:04+10:00: on CPython 3.14.4
    gc.get_referents answers [] for weakref.ref(obj) and the callback alone
    for weakref.ref(obj, callback)].

    Time: one gc.get_referents call per object reached, about five per cached
    call site, so at most about 20,500 over the cache's 4,096 entries.
    """
    seen = {id(root)}
    frontier = [root]
    reached = []
    while frontier:
        for referent in gc.get_referents(frontier.pop()):
            if id(referent) not in seen:
                seen.add(id(referent))
                reached.append(referent)
                frontier.append(referent)
    return reached


def test_answer_position_cache_does_not_own_generated_code():
    """A cached call site holds its generated code object weakly.

    Asked of the cache, not of the code object's lifetime. Whether the code
    object dies at gc.collect() is the whole process's answer, and the gate's
    pytest lane runs under coverage, whose sys.monitoring core keeps every code
    object it has started alive so their ids stay unique [source
    2026-09-25T09:58:00+10:00: coverage 7.15.4 coverage/sysmon.py:213-215 and
    372, SysMonitor.code_objects, the default core on CPython 3.14 by
    coverage/env.py:56]. So that form failed in every gate run while passing
    alone [measured 2026-09-25T09:55:18+10:00: this file alone in one process
    under --cov fails it, the code object held by a list of 3,475 that
    SysMonitor owns]. What this module promises is narrower and exact:
    the cache is not among the code object's owners, whoever else is.
    """
    drive, _positions = driver(37)
    code = drive.__code__

    assert drive(Answers([1], space="&answer-position-lifetime"), 1) == 1
    assert any(reference() is code for reference, _ in _lint_events._POSITION_CACHE.values()), (
        "iterating did not cache the call site, so the ownership question asks nothing"
    )
    held = [owned for owned in _strongly_reachable(_lint_events._POSITION_CACHE) if owned is code]
    assert not held, "the position cache holds the generated code object strongly"


def test_a_collection_inside_the_position_store_does_not_deadlock(tmp_path):
    """Nothing the position cache holds runs at collection time.

    A weakref callback runs inside whichever collection frees its referent,
    on that collection's thread. The cache's used to take the cache's plain
    Lock, so a collection started by an allocation inside the locked store
    froze the storing thread for good. A child process, because a thread
    waiting on its own Lock cannot be interrupted from inside.
    """
    repository = workspace()
    try:
        run = subprocess.run(
            [sys.executable, "-c", _COLLECTION_INSIDE_THE_STORE],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={
                **os.environ,
                "METTA_PATH": str(repository),
                "PYTHONPATH": str(repository / "extensions" / "python"),
            },
            # The child imports metta and stores two positions; a minute is far
            # above that, and a wait on its own lock never ends at all.
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("storing a position waited on the cache's own lock inside a collection")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "returned" in run.stdout, run.stdout + run.stderr
