"""Purpose: prove the stdlib phrasebook lane catches what it claims to catch.

A lane that cannot be shown failing is evidence of nothing, so these plant a
wrong answer, a silent divergence between the two sides, a bucket claimed
without a spelling, a residue row that secretly carries one, and a stale page,
and require the lane to answer correctly about each. The coverage claim itself
is checked the other way round: every name LeaTTa declares has exactly one row,
so the denominator cannot quietly shrink.

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "bindings" / "python" / "tools"))

import phrasebook as book  # noqa: E402
from phrasebook_entries import ENTRIES, Entry  # noqa: E402


def _entry(**overrides) -> Entry:
    """A minimal well-formed row, so a test changes exactly one thing."""
    fields = {
        "name": "pb-row",
        "types": ("(-> Number Number)",),
        "metatype": "Symbol",
        "section": "arith",
        "bucket": "dissolves",
        "note": "a planted row",
        "metta": "!(+ 1 2)",
        "python": "1 + 2",
    }
    fields.update(overrides)
    return Entry(**fields)


def test_the_phrasebook_covers_every_leatta_name():
    """One row per declared name, with LeaTTa's own types, and no drift."""
    names = [entry.name for entry in ENTRIES]
    assert len(names) == len(set(names)), "a name carries more than one row"
    assert len(names) == 380, f"380 distinct names were declared, the rows carry {len(names)}"
    note, findings = book.drift(list(ENTRIES))
    assert findings == [], f"{note}: {findings}"


def test_every_row_states_its_bucket_honestly():
    """The shipped rows pass their own structural rules."""
    assert book.structural(list(ENTRIES)) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"bucket": "dissolves", "python": None}, "claims bucket dissolves with no spelling"),
        ({"bucket": "absent"}, "claims to be absent yet carries a spelling"),
        ({"note": ""}, "no note"),
        ({"bucket": "invented"}, "unknown bucket"),
        ({"section": "invented"}, "unknown section"),
        ({"bucket": "absent", "python": None, "ruled": "x"}, None),
        ({"ruled": "x"}, "names a ruling"),
    ],
)
def test_a_dishonest_row_is_a_structural_finding(overrides, expected):
    """Each way a row can lie about itself, planted one at a time."""
    findings = book.structural([_entry(**overrides)])
    if expected is None:
        assert findings == []
        return
    assert any(expected in finding for finding in findings), findings


def test_a_broken_python_spelling_is_a_finding():
    """A spelling that stops answering what the record says is caught."""
    entry = _entry()
    frozen = {"leatta": ["3"], "metta": ["3"], "python": ["3"]}
    seen = {"metta": ["3"], "python": ["4"]}
    findings = book.compare(entry, frozen, seen)
    assert any("the python side now answers" in finding for finding in findings), findings


def test_a_silent_divergence_is_a_finding():
    """Two sides that disagree without saying why is a finding; saying why is not."""
    seen = {"metta": ["3"], "python": ["4"]}
    frozen = {"leatta": ["3"], "metta": ["3"], "python": ["4"]}
    quiet = book.compare(_entry(), frozen, seen)
    assert any("the two sides disagree" in finding for finding in quiet), quiet
    spoken = book.compare(_entry(differs="the engines round differently"), frozen, seen)
    assert not any("the two sides disagree" in finding for finding in spoken), spoken


def test_a_spelling_that_leaves_the_oracle_behind_is_a_finding():
    """Agreeing with this engine is not enough when the oracle says otherwise."""
    frozen = {"leatta": ["3"], "metta": ["4"], "python": ["4"]}
    findings = book.compare(_entry(), frozen, {"metta": ["4"], "python": ["4"]})
    assert any("where LeaTTa answers" in finding for finding in findings), findings


def test_a_raising_spelling_is_a_finding():
    """A spelling that raises is reported as raising, not as a wrong answer."""
    seen = {"metta": ["3"], "python": ["RAISED TypeError: planted"]}
    findings = book.compare(_entry(), {"metta": ["3"], "python": ["3"]}, seen)
    assert any("raised typeerror" in finding for finding in findings), findings


def test_the_phrasebook_page_is_up_to_date():
    """The checked-in page is what the rows produce."""
    answers = json.loads(book.ANSWERS.read_text(encoding="utf-8"))
    assert book.PAGE.read_text(encoding="utf-8") == book.page(list(ENTRIES), answers), (
        "run `python bindings/python/tools/phrasebook.py --markdown`"
    )


def test_every_answered_row_has_a_recorded_answer():
    """A row that runs carries its measurement, so nothing is claimed unmeasured."""
    answers = json.loads(book.ANSWERS.read_text(encoding="utf-8"))
    for entry in ENTRIES:
        if entry.metta is None and entry.python is None:
            continue
        record = answers.get(entry.name)
        assert record is not None, f"{entry.name} runs but has no recorded answer"
        if entry.python is not None:
            assert record.get("python") is not None, f"{entry.name} has no Python answer"


def test_a_list_is_answers_and_a_tuple_is_one_expression():
    """The rendering rule, which every row's answer column depends on."""
    import metta

    assert book.render([metta.S.a, metta.S.b]) == ("a", "b")
    assert book.render((metta.S.a, metta.S.b)) == ("(a b)",)
    assert book.render(3) == ("3",)
    assert book.render(metta.S.f(1)) == ("(f 1)",)


def test_an_answer_line_splits_on_top_level_commas_only():
    """A comma inside a form is not a separator between answers."""
    assert book.split_answers("[a, (f 1)]") == ("a", "(f 1)")
    assert book.split_answers("[]") == ()
    assert book.split_answers("[(f 1, 2)]") == ("(f 1, 2)",)


def test_alpha_text_canonicalizes_by_first_appearance():
    """One canonical text form, so a transcript records the answer not the counter.

    Two lanes need it, which is why it is one function: the differential oracle
    compares two CLI runs whose allocation histories differ by consult order,
    and the phrasebook froze `($_98110 $_98518)` and went red on a merge that
    changed no semantics, because the engine reached that point having invented
    ten fewer variables.
    """
    import alpha

    # The same answer under two allocation histories canonicalizes identically.
    assert alpha.canonical("($_98110 $_98518)") == alpha.canonical("($_98120 $_98528)")

    # Two variables never collapse into one, which is the distinction
    # alpha-equivalence makes and a blanket substitution would lose.
    assert alpha.canonical("($_1 $_2)") != alpha.canonical("($_1 $_1)")

    # Renaming is by FIRST APPEARANCE, not by the original numbering's order.
    assert alpha.canonical("($_900 $_100 $_900)") == "($_v0 $_v1 $_v0)"

    # A text with no machine variable is untouched, so an ordinary answer
    # round-trips exactly.
    assert alpha.canonical("(edge a b)") == "(edge a b)"
