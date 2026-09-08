"""Purpose: verify the shrink ledger as a query over typed door rows.

Guarantees: a missing base, duplicate point, or empty contract is refused
  [tested: test_the_shrink_ledger_catches_a_planted_gap; commit=WORKTREE].
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "extensions/python/tools"))

import ledger  # noqa: E402
from doorgen import all_rows, ledger_page  # noqa: E402

from metta.doors import Owner, Sugar, Tier, validate  # noqa: E402


def test_the_shrink_ledger_covers_every_derived_door():
    """Each Space row occurs once, classified by its declared kind."""
    rows = all_rows()
    page = ledger_page(rows)
    selected = [row for row in rows if row.owner is Owner.space and Tier.sync in row.tiers]
    for row in selected:
        assert page.count(f"| `{row.python}` | {row.kind} |") == 1
    assert any(row.sugar_of for row in selected)
    assert not next(row for row in selected if row.python == "transaction").sugar_of
    assert not next(row for row in selected if row.python == "eval").sugar_of


def test_every_ledger_row_states_what_its_door_buys():
    """Every sugar declares its longhand, contract, and observable evidence."""
    rows = all_rows()
    keys = {row.key for row in rows}
    for row in rows:
        if row.sugar_of:
            assert row.sugar_of.base in keys
            assert row.sugar_of.fixed
            assert row.docs.strip() and row.evidence


def test_the_shrink_ledger_catches_a_planted_gap():
    """Invalid rows fail at the shared validator, before any page is emitted."""
    rows = all_rows()
    sugar = next(row for row in rows if row.key == "space:answers")
    with pytest.raises(ValueError, match="missing sugar base"):
        validate(tuple(replace(row, sugar_of=Sugar("space:absent", ())) if row is sugar else row for row in rows))
    with pytest.raises(ValueError, match="existing parameter point"):
        validate((*rows, replace(sugar, name="second-answers")))
    with pytest.raises(ValueError, match="documentation"):
        validate(tuple(replace(row, docs=" ") if row is sugar else row for row in rows))
    assert validate(rows) == rows


def test_the_shrink_ledger_page_is_up_to_date():
    """The checked-in page is the same row query used by door-sync."""
    assert ledger.PAGE.read_text(encoding="utf-8") == ledger_page(all_rows())
