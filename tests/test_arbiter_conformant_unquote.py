"""Purpose: pin that `unquote` EVALUATING its argument is the conformant
behaviour, not a defect. An earlier alignment pass proposed removing the
`(eval $A)` from lib_he's `unquote` because `(unquote (quote (+ 1 2)))`
answers `3` rather than `(+ 1 2)`; the pinned arbiter records BOTH systems
evaluating, verdict `conforms`, so the proposal was retired and this test
is what stops it coming back as a plausible-looking fix.
Assumes:
    - bindings/python/tools/example_parity.py runs a source file through the engine
      door, which is where library imports into &self are isolated in a
      subprocess rather than shared with the suite's session engine
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "bindings" / "python" / "tools"))

import example_parity as parity  # noqa: E402


def test_unquote_evaluates_as_the_arbiter_records():
    """`(unquote (quote (+ 1 2)))` answers 3. Removing the eval would make
    this answer `(+ 1 2)` and the assertion here would name the change."""
    source = REPO / "bindings" / "python" / "tests" / "data" / "unquote_conformance.metta"
    source.write_text(
        "!(import! &self (library lib_he))\n"
        "!(unquote (quote (+ 1 2)))\n"
    )
    try:
        outcome = parity.run_engine(source, root=REPO)
    finally:
        source.unlink(missing_ok=True)
    assert outcome.error is None, outcome.error
    assert outcome.groups[-1] == "(3)", (
        f"unquote no longer evaluates: the engine answered {outcome.groups[-1]} "
        "where the arbiter records both systems answering 3"
    )
