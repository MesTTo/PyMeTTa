"""Purpose: pin two agreements between the engine door and the library door
that were reached on 2026-08-18 and left resting on the corpus. The parity
lane proves the 200 shipped examples agree, which is the outcome; neither of
these two mechanisms is named by a test of its own, so a regression in either
would show up only as a corpus example changing its mind.
Assumes:
    - extensions/python/tools/example_parity.py owns running one file through both
      doors, so this does not spawn its own subprocesses
      [source: extensions/python/tools/example_parity.py, run_engine/2 and run_library/2]
Guarantees:
    - each test fails if its mechanism regresses, shown by construction: the
      first writes the exact shape that used to fail through the library and
      the second the exact shape that used to disagree
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "extensions" / "python" / "tools"))

import example_parity as parity  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def door_fixture():
    """A .metta file INSIDE the repository, removed afterwards.

    example_parity computes each door's command relative to the repo root,
    so a file under pytest's tmp_path raises `is not in the subpath of`
    before either door runs. It lives beside the other test data rather
    than under examples/, which is the corpus the parity lane globs.
    """
    written = []

    def write(name, text):
        path = REPO / "extensions" / "python" / "tests" / "fixtures" / f"{name}.metta"
        path.write_text(text)
        written.append(path)
        return path

    yield write
    for path in written:
        path.unlink(missing_ok=True)


def test_load_pre_registers_signatures_so_a_later_definition_resolves(door_fixture):
    """P1.11. `!(memoize f)` written ABOVE the `(= (f ...) ...)` the same
    file defines used to fail through the library and work through the
    engine, because `fun/1` was not asserted yet and memoize refused the
    name. Seven shipped examples shared that one root and the fix was to
    collect every equation head BEFORE processing any form
    [source: engine/filereader.pl, prepare_parsed_forms/1].

    The pre-pass is what this names, not the corpus: a file whose only
    content is the failing shape.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    source = door_fixture(
        "signature_prepass",
        "!(memoize metta-prepass)\n(= (metta-prepass) ok)\n!(test (metta-prepass) ok)\n",
    )
    library = parity.run_library(source, root=REPO)
    assert library.error is None, (
        "the library refused a memoize written above its definition, which is "
        f"the pre-pass regressing: {library.error}"
    )
    assert library.groups, "the library ran nothing, so this proves nothing"


def test_a_forward_call_behaves_the_same_through_both_doors(door_fixture):
    """P1.12. A call to a function defined LOWER in the same file, in body
    position. Measured 2026-08-19: both doors answer `ok`. The point is the
    AGREEMENT rather than the answer, so this compares them instead of
    asserting a value, and it would fail just as loudly if the engine
    started succeeding where the library did not.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    source = door_fixture(
        "forward_call",
        "(= (metta-forward-caller) (metta-forward-callee))\n"
        "(= (metta-forward-callee) ok)\n"
        "!(test (metta-forward-caller) ok)\n",
    )
    difference = parity.compare(source, root=REPO)
    assert difference is None, f"the two doors disagree on a forward call: {difference}"


# A note on what the second test above is worth. It asserts an AGREEMENT, so it
# cannot be mutation-checked from here the way the first one can: planting a
# fault in the source breaks both doors equally and they go on agreeing, which
# is the test passing correctly rather than the test being blind. Its
# discrimination is `compare`'s, and that IS tested, by
# `test_example_parity_reports_a_planted_difference`, which plants a difference
# and requires the comparator to report it [tested 2026-08-19].
