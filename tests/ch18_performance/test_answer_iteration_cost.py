"""Purpose: keep Answers caller-position lookup constant after one derivation.

Guarantees:
  - increasing the call site's bytecode offset by more than one hundredfold
    does not multiply steady-state Answers iteration time [tested:
    test_answer_iteration_benchmark_reuses_one_warmed_view;
    commit=0ffac1f272c65d1c3742a2bfb824538e426c264a]
  - cached position metadata does not keep generated code alive [tested:
    test_answer_position_cache_does_not_own_generated_code;
    commit=0ffac1f272c65d1c3742a2bfb824538e426c264a]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import ast
import gc
import weakref
from typing import ClassVar

import pytest

from benchmarks.answer_iteration_cost import driver
from metta import _lint_events
from metta.results import Answers


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


def test_answer_position_cache_does_not_own_generated_code():
    """A cached call site expires with its generated code object."""
    drive, _positions = driver(37)
    code = drive.__code__
    reference = weakref.ref(code)

    assert drive(Answers([1], space="&answer-position-lifetime"), 1) == 1
    del drive, code
    gc.collect()

    assert reference() is None
