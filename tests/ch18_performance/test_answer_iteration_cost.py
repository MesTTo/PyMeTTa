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

import gc
import weakref

from benchmarks.answer_iteration_cost import driver, rows
from metta.results import Answers


def test_answer_iteration_benchmark_reuses_one_warmed_view():
    """Position derivation is one preprocessing cost, not one scan per loop."""
    shallow, deep = rows(calls=1_000, paddings=(0, 1_000), rounds=3)

    assert deep.positions > 150 * shallow.positions
    assert deep.nanoseconds < 3 * shallow.nanoseconds, (
        f"iteration rose from {shallow.nanoseconds:.1f} ns at "
        f"{shallow.positions} positions to {deep.nanoseconds:.1f} ns at "
        f"{deep.positions}; the call site is still scanned per iteration"
    )


def test_answer_position_cache_does_not_own_generated_code():
    """A cached call site expires with its generated code object."""
    drive, _positions = driver(37)
    code = drive.__code__
    reference = weakref.ref(code)

    assert drive(Answers([1], space="&answer-position-lifetime"), 1) == 1
    del drive, code
    gc.collect()

    assert reference() is None
