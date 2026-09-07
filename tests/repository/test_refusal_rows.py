"""Purpose: the catalog's (refusal ...) rows are what every seat says about a refusal.

`tests/data/error-kinds.json` lists the kinds with each seat's own class; the
rows in `&metta` carry the seat-independent class, the authority the refusal
stands on and the repair. This file holds the two together: a seat that spells
a class differently says why, one meaning never wears two class names, the
three closed sets `metta.errors` validates against are the catalog's own, and
every listed ball thrown through this seat arrives carrying its row's ground
and its row's remedy with the holes filled from that very ball.

Guarantees:
  - the rows and the shared kind list name the same kinds
    [tested: test_the_rows_and_the_fixture_name_the_same_kinds; commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
  - each seat raises the row's class or the list says why, and no meaning
    wears two class names on either seat
    [tested: test_every_seat_raises_the_rows_class_or_says_why,
    test_one_class_per_meaning; commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
  - GROUND_KINDS, REMEDY_KINDS and APPLICABILITIES are the catalog's three
    vocabularies, compared both ways
    [tested: test_the_refusal_vocabularies_are_the_catalogs; commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
  - a thrown ball arrives carrying its row's ground and a remedy whose holes
    are filled from that ball
    [tested: test_a_thrown_ball_carries_its_rows_ground_and_remedy; commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
  - the thirteen refusals render thirteen different sentences, and the check
    sees a planted duplicate
    [tested: test_the_thirteen_refusals_are_thirteen_sentences,
    test_the_duplicate_check_sees_a_planted_duplicate; commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
  - a row rewritten in the catalog reaches this seat with no change to any
    Python source [tested: test_a_rewritten_row_reaches_this_seat_at_once; commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

from metta import MeTTa
from metta.errors import APPLICABILITIES, GROUND_KINDS, REMEDY_KINDS

#: Read at import, like its neighbour: the cases below are one test per kind
#: and parametrize runs at collection time.
KINDS = json.loads(
    (Path(__file__).resolve().parents[4] / "tests" / "data" / "error-kinds.json").read_text()
)["kinds"]

_ROW_IS_THE_NAME = (
    "the class a seat raises is the second field of the kind's (refusal ...) "
    "row in engine/spaces/catalog.pl; a seat that spells it differently "
    "carries why in tests/data/error-kinds.json beside its own spelling"
)


@pytest.fixture(scope="module")
def engine():
    """One engine for the module: every case here reads, and the one that
    writes puts the row back.
    """  # noqa: D205  -- one sentence about two halves
    with MeTTa().space("&refusal_rows_probe") as space:
        yield space


@pytest.fixture(scope="module")
def rows(engine):
    """Every (refusal ...) row, read from the running catalog."""
    answered = engine.runtime.must(
        # _-prefixed because janus converts every NAMED variable of the query
        # and a findall template's variables are still free when it answers,
        # which janus reports as "Arguments are not sufficiently instantiated".
        "findall([_Kind, _Class, _Authority, _Citation, _Title, _RemedyKind, "
        "         _Applicability], "
        "metta_host_refusal_row(_Kind, _Class, [ground, _Authority, _Citation], "
        "                       [remedy, _Title, _RemedyKind, _Applicability|_Acts]), "
        "Rows)"
    )["Rows"]
    return {
        kind: {
            "class": klass,
            "authority": authority,
            "citation": citation,
            "title": title,
            "remedy_kind": remedy_kind,
            "applicability": applicability,
        }
        for kind, klass, authority, citation, title, remedy_kind, applicability in answered
    }


def _vocabulary(engine, name):
    """One (vocabulary ...) row's members, in the catalog's own order."""
    return tuple(
        engine.runtime.must(
            "metta_catalog_row([vocabulary, Name|Members])", Name=name
        )["Members"]
    )


def test_the_rows_and_the_fixture_name_the_same_kinds(rows):
    """The catalog's rows and the shared kind list are one set of kinds."""
    assert sorted(rows) == sorted(KINDS), (
        "a kind with no (refusal ...) row carries no ground and no remedy on "
        "any seat, and a row for no kind is one nothing can raise"
    )


@pytest.mark.parametrize("name", sorted(KINDS))
@pytest.mark.parametrize("seat", ["python", "node"])
def test_every_seat_raises_the_rows_class_or_says_why(name, seat, rows):
    """A seat spells the row's class, or records what it spells instead and why."""
    listed = KINDS[name][seat]
    declared = rows[name]["class"]
    if listed["error"] == declared:
        assert "why" not in listed, f"{name} on {seat} agrees with the row and still says why"
        return
    reason = listed.get("why") or listed.get("note")
    assert reason, f"{seat} raises {listed['error']} for {name}, not {declared}; {_ROW_IS_THE_NAME}"
    assert len(reason) > 30, f"{name} on {seat}: the reason is a word, not a reason"


def test_one_class_per_meaning(rows):
    """No class name is two meanings, on the rows or on either seat."""
    for population, names in (
        ("the rows", [row["class"] for row in rows.values()]),
        ("the Python seat", [row["python"]["error"] for row in KINDS.values()]),
        ("the Node seat", [row["node"]["error"] for row in KINDS.values()]),
    ):
        repeated = [
            name for name, count in Counter(n for n in names if n).items() if count > 1
        ]
        assert repeated == [], f"{population} spells one class for {repeated}, which is two meanings"


def test_the_duplicate_check_sees_a_planted_duplicate():
    """The count that finds a repeated class finds one that is planted."""
    planted = ["EngineError", "WireError", "EngineError"]
    repeated = [name for name, count in Counter(planted).items() if count > 1]
    assert repeated == ["EngineError"]


def test_the_refusal_vocabularies_are_the_catalogs(engine):
    """metta.errors' three closed sets are the catalog's three rows, both ways."""
    assert _vocabulary(engine, "ground-kind") == GROUND_KINDS
    assert _vocabulary(engine, "remedy-kind") == REMEDY_KINDS
    assert _vocabulary(engine, "applicability") == APPLICABILITIES


@pytest.mark.parametrize("name", sorted(KINDS))
def test_a_thrown_ball_carries_its_rows_ground_and_remedy(name, engine, rows):
    """Throwing a listed ball raises an error carrying that kind's row."""
    row = rows[name]
    with pytest.raises(Exception) as failure:
        engine.runtime.must(
            "term_string(_Ball, BallText), throw(_Ball)", BallText=KINDS[name]["ball"]
        )
    raised = failure.value
    ground = getattr(raised, "ground", None)
    remedy = getattr(raised, "remedy", None)
    assert ground is not None, f"{name} arrived with no ground; {_ROW_IS_THE_NAME}"
    assert (ground.kind, ground.citation) == (row["authority"], row["citation"])
    assert remedy is not None, f"{name} arrived with no remedy"
    assert remedy.kind == row["remedy_kind"]
    assert remedy.applicability in APPLICABILITIES
    for field in KINDS[name]["expects"]:
        assert f"<{field}>" not in remedy.title, (
            f"{name} left <{field}> in its remedy although the ball carried it"
        )
    for field, value in KINDS[name]["expects"].items():
        if f"<{field}>" in row["title"]:
            assert value in remedy.title


def test_the_thirteen_refusals_are_thirteen_sentences(engine):
    """One meaning, one sentence: no two kinds render the same message."""
    said = {}
    for name, row in KINDS.items():
        with pytest.raises(Exception) as failure:
            engine.runtime.must(
                "term_string(_Ball, BallText), throw(_Ball)", BallText=row["ball"]
            )
        said[name] = str(failure.value)
    repeated = [text for text, count in Counter(said.values()).items() if count > 1]
    assert repeated == [], f"two kinds say the same thing, so a reader cannot tell them apart: {repeated}"


def test_a_rewritten_row_reaches_this_seat_at_once(engine):
    """A row rewritten in the catalog changes what this seat carries, with no
    Python change at all: the seat reads the row rather than a copy of it.
    """  # noqa: D205  -- one claim in two clauses
    shipped = _row_text(engine)
    planted = (
        '(refusal engine EngineError (ground metta-law "HostLaws: a planted row") '
        '(remedy "planted repair for <nothing>" refactor prose))'
    )
    _rewrite(engine, planted)
    try:
        raised = _thrown(engine)
        assert raised.remedy.title == "planted repair for <nothing>"
        assert raised.remedy.kind == "refactor"
        assert raised.ground.citation == "HostLaws: a planted row"
    finally:
        _rewrite(engine, shipped)
    assert _row_text(engine) == shipped
    assert _thrown(engine).remedy.title == "report the ball with the message it carries; this engine did not shape it"


def _refusalsdoc(repo_root):
    """The page generator, imported the way its neighbours import a tool."""
    sys.path.insert(0, str(repo_root / "extensions" / "python" / "tools"))
    try:
        import refusalsdoc
    finally:
        sys.path.pop(0)
    return refusalsdoc


def test_the_refusals_page_is_generated(repo_root):
    """website/reference/refusals.md is what the engine's own rows produce."""
    assert _refusalsdoc(repo_root).main([]) == 0


def test_the_page_check_sees_a_kind_on_one_side_only(repo_root):
    """A kind with a row and no shared-list entry, or the other way, is a finding."""
    doc = _refusalsdoc(repo_root)
    rowed = [{"kind": "planted"}]
    listed = {"vanished": {}}
    found = doc.findings(rowed, listed)
    assert found == [
        "planted: has a row and no entry in the shared kind list",
        "vanished: is in the shared kind list and has no row",
    ]
    assert doc.findings(rowed, {"planted": {}}) == []


def test_a_hole_is_written_as_code_on_the_page(repo_root):
    """A `<field>` hole reaches the page inside backticks, never as a tag.

    VitePress compiles markdown through Vue, which reads a bare `<line>` as a
    custom element; the site build is the lane that would catch it, and this
    is the sentence that says why the generator escapes.
    """
    assert (
        _refusalsdoc(repo_root).spelled("stopped at line <line> of <source>")
        == "stopped at line `<line>` of `<source>`"
    )


def _row_text(engine):
    """The `engine` row as its own MeTTa source, which is what puts it back."""
    return engine.runtime.must(
        "metta_catalog_row([refusal, engine|_Rest]), swrite([refusal, engine|_Rest], Text)"
    )["Text"]


def _thrown(engine):
    """The exception this seat raises for the honest-default ball."""
    with pytest.raises(Exception) as failure:
        engine.runtime.must(
            "term_string(_Ball, BallText), throw(_Ball)", BallText=KINDS["engine"]["ball"]
        )
    return failure.value


def _rewrite(engine, row_text):
    """Replace the `engine` row with one read from MeTTa source.

    Through `sread` rather than through janus keyword arguments: a row's title
    is a STRING and its class a SYMBOL, and handing both back as Python text
    loses that difference at the crossing, which the catalog's own argspec
    then refuses.
    """
    engine.runtime.must(
        "forall(metta_catalog_row([refusal, engine|_Old]), "
        "       remove_sexp('&metta', [refusal, engine|_Old])), "
        "sread(RowText, _Row), add_sexp('&metta', _Row, _)",
        RowText=row_text,
    )
