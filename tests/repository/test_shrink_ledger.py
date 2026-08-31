"""Purpose: gate the Python surface's shrink ledger, and prove it can fail.

`KERNEL.md` is the engine's ledger of which head is primitive and which is
derived, and it requires every derived form still fused into the compiler to
say why. The library had 110 public doors and no such ledger, so a door that
became expressible by another could sit there indefinitely: ten declaration
doors did exactly that, each rewriting a helper's body longhand and each
losing the loop and the transaction that helper has
[measured 2026-08-31, a stale `(emits &s fair)` row survived a redeclaration].

Assumes:
  - the classification is DERIVED FROM THE CODE. A hand-maintained list of
    which doors are derived would be the thing that rots, so `ledger.py` walks
    the class and this file only checks the reasons.
Guarantees:
  - every derived door has exactly one row and every row names a live derived
    door [tested: test_the_shrink_ledger_covers_every_derived_door]
  - the checked-in page equals what the tool renders [tested:
    test_the_shrink_ledger_page_is_up_to_date]
  - the gate DISCRIMINATES: a planted door with no row is a finding, a planted
    row for no door is a finding, and an empty reason is a finding [tested:
    test_the_shrink_ledger_catches_a_planted_gap]
  - a reason says what the caller GETS, not that the door is shorter [tested:
    test_every_ledger_row_states_what_its_door_buys]
Fails when: read as a count. A named face of one mechanism is derived and
  should stay; the ledger refuses a derived door with no ANSWER, not a derived
  door.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "extensions" / "python" / "tools"))

import ledger  # noqa: E402
from ledger_entries import DERIVED  # noqa: E402


def _rows():
    from metta._space import Space

    return ledger.classify(Space)


def test_the_shrink_ledger_covers_every_derived_door():
    """One row per derived door, and no row for a door that is not."""
    rows = _rows()
    derived = {name for name, (kind, _) in rows.items() if kind == "derived"}
    assert derived, "the classifier found no derived doors, so it is not working"
    assert derived == set(DERIVED), (
        f"unrowed: {sorted(derived - set(DERIVED))}; "
        f"stale rows: {sorted(set(DERIVED) - derived)}"
    )
    assert not ledger.findings(rows)


def test_every_ledger_row_states_what_its_door_buys():
    """A reason is about the CALLER, so it cannot be 'it is shorter'."""
    for door, reason in DERIVED.items():
        assert len(reason.split()) >= 8, f"{door}: too short to be a reason"
        assert "shorter" not in reason, f"{door}: brevity is not what a door buys"


def test_the_shrink_ledger_catches_a_planted_gap():
    """A lane that cannot be shown failing is evidence of nothing."""
    rows = _rows()
    derived = next(name for name, (kind, _) in rows.items() if kind == "derived")

    # A derived door with no row.
    without = {name: text for name, text in DERIVED.items() if name != derived}
    original = dict(DERIVED)
    DERIVED.clear()
    DERIVED.update(without)
    try:
        assert any(derived in finding for finding in ledger.findings(rows))
        # A row for a door that is not derived.
        DERIVED["a-door-that-is-not-derived"] = "buys nothing, because it is not a door"
        assert any(
            "a-door-that-is-not-derived" in finding for finding in ledger.findings(rows)
        )
        # An empty reason.
        DERIVED.clear()
        DERIVED.update(original)
        DERIVED[derived] = "   "
        assert any("says nothing" in finding for finding in ledger.findings(rows))
    finally:
        DERIVED.clear()
        DERIVED.update(original)
    assert not ledger.findings(rows), "the plants were not fully unwound"


def test_the_shrink_ledger_page_is_up_to_date():
    """The page is generated, so it cannot drift from the class."""
    rows = _rows()
    assert ledger.PAGE.read_text(encoding="utf-8") == ledger.page(rows), (
        "run `python extensions/python/tools/ledger.py --write`"
    )
