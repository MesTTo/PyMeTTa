"""Purpose: the two rows a refusal carries beside its message, as data.

Remedy and Ground: what they admit, what they refuse at construction, and
the atom each projects to and reads back from.

Guarantees:
  - every act, and both spellings of replace, survive as_atom/from_atom, and
    a row that is not one refuses by name [tested:
    test_a_remedy_round_trips_through_its_atom,
    test_a_ground_round_trips_through_its_atom,
    test_a_malformed_remedy_row_is_refused_by_name; commit=3fc5479961fd591b1884af118528c9a64a1afbb7]
  - a machine or maybe Remedy naming no act, an unknown kind, an unknown
    applicability and an unknown ground kind each refuse with the admitted set
    named [tested:
    test_a_remedy_that_names_no_act_refuses_naming_the_three_fields,
    test_an_unknown_classifier_names_what_is_admitted; commit=3fc5479961fd591b1884af118528c9a64a1afbb7]
  - a prose Remedy may be its title alone, and round trips that way, which is
    advice with no mechanical edit [tested:
    test_a_prose_remedy_may_be_its_title_alone; commit=WORKTREE]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import pickle

import pytest

from metta import Grounded, S, V
from metta.errors import APPLICABILITIES, GROUND_KINDS, REMEDY_KINDS, Ground, Remedy

_TITLE = Grounded("t")


def test_a_remedy_round_trips_through_its_atom():
    """Every act, and both spellings of replace, survive the projection."""
    for remedy in (
        Remedy("add it", "quickfix", "machine", edit=S.fact(S.a)),
        Remedy("rewrite it", "refactor", "maybe", replace=(S.old(V.x), S.new(V.x))),
        Remedy("drop it", "quickfix", "machine", replace=(S.old(V.x), None)),
        Remedy("run it", "source", "prose", python="m.run(source)"),
        Remedy("decide it yourself", "quickfix", "prose"),
        Remedy("both", "quickfix", "machine", edit=S.a, python="m.add(S.a)"),
    ):
        assert Remedy.from_atom(remedy.as_atom()) == remedy


def test_a_ground_round_trips_through_its_atom():
    """One row per admitted authority, and the citation stays text."""
    for ground in (
        Ground("host-reference", "Python Language Reference section 6.3.4, Calls"),
        Ground("metta-law", "EffectSafety: a reified world admits only a covered plan"),
        Ground("arbiter", "upstream PeTTa: tests/conformance/petta/HEADS.json"),
    ):
        assert Ground.from_atom(ground.as_atom()) == ground
        assert str(ground) == f"{ground.kind}: {ground.citation}"


def test_a_remedy_that_names_no_act_refuses_naming_the_three_fields():
    """A repair promised as applicable and naming none is a defect.

    `machine` and `maybe` both promise something an editor can apply, so a
    remedy at either level with no act is refused with all three fields named
    and the level it claimed.
    """
    for level in ("machine", "maybe"):
        with pytest.raises(ValueError, match="names no act") as refused:
            Remedy("say nothing", "quickfix", level)
        message = str(refused.value)
        assert level in message
        assert "edit=" in message
        assert "replace=" in message
        assert "python=" in message


def test_a_prose_remedy_may_be_its_title_alone():
    """Advice with no mechanical edit is a repair, and reads back as one.

    Nine of the thirteen refusal kinds in the `&metta` catalog are this shape,
    because their repair is a decision; PostgreSQL's `errhint()` and clang's
    `note:` carry the same category.
    """
    advice = Remedy("correct the claim, or the equations it reads", "quickfix", "prose")
    assert advice.edit is None
    assert advice.replace is None
    assert advice.python is None
    assert Remedy.from_atom(advice.as_atom()) == advice
    assert str(advice.as_atom()) == (
        '(remedy "correct the claim, or the equations it reads" quickfix prose)'
    )


def test_an_unknown_classifier_names_what_is_admitted():
    """Each closed set refuses with its own members printed, never a bare no."""
    with pytest.raises(ValueError, match="unknown remedy kind") as kind:
        Remedy("t", "rewrite", "machine", python="x")
    assert all(word in str(kind.value) for word in REMEDY_KINDS)
    with pytest.raises(ValueError, match="unknown remedy applicability") as level:
        Remedy("t", "quickfix", "certain", python="x")
    assert all(word in str(level.value) for word in APPLICABILITIES)
    with pytest.raises(ValueError, match="unknown refusal-ground kind") as ground:
        Ground("oracle", "somewhere")
    assert all(word in str(ground.value) for word in GROUND_KINDS)
    with pytest.raises(ValueError, match="nonempty citation"):
        Ground("metta-law", "   ")
    with pytest.raises(ValueError, match="nonempty title"):
        Remedy("  ", "quickfix", "prose", python="x")


def test_a_malformed_remedy_row_is_refused_by_name():
    """from_atom is total: anything that is not the row refuses, loudly."""
    not_a_remedy_row = r"is not a \(remedy \.\.\.\) row"
    not_a_ground_row = r"is not a \(ground \.\.\.\) row"
    with pytest.raises(ValueError, match=not_a_remedy_row):
        Remedy.from_atom(S.fix(S.a))
    with pytest.raises(ValueError, match="is not a remedy act"):
        Remedy.from_atom(S.remedy(_TITLE, S.quickfix, S.machine, S.rewrite(S.a)))
    with pytest.raises(ValueError, match="names no act"):
        Remedy.from_atom(S.remedy(_TITLE, S.quickfix, S.machine))
    with pytest.raises(ValueError, match="then any acts"):
        Remedy.from_atom(S.remedy(_TITLE, S.quickfix))
    with pytest.raises(ValueError, match="the title is text"):
        Remedy.from_atom(S.remedy(S.t, S.quickfix, S.machine, S.python(_TITLE)))
    with pytest.raises(ValueError, match="the python text is text"):
        Remedy.from_atom(S.remedy(_TITLE, S.quickfix, S.machine, S.python(S.x)))
    with pytest.raises(ValueError, match="the remedy kind is a symbol"):
        Remedy.from_atom(
            S.remedy(_TITLE, Grounded("quickfix"), S.machine, S.python(_TITLE))
        )
    with pytest.raises(ValueError, match=not_a_ground_row):
        Ground.from_atom(S.remedy(_TITLE, S.quickfix, S.machine))
    with pytest.raises(ValueError, match="row carries 2 parts"):
        Ground.from_atom(S.ground(S["host-reference"]))


def test_both_rows_are_frozen_slotted_and_pattern_matchable():
    """They are values: nothing on one changes, and match reads them."""
    remedy = Remedy("drop it", "quickfix", "machine", replace=(S.old, None))
    with pytest.raises(AttributeError):
        remedy.title = "other"  # type: ignore[misc]  -- the refusal IS the contract
    #: Slotted, so there is nowhere for a stray attribute to go. Asked as the
    #: absence of __dict__ rather than by assigning one: a frozen slots
    #: dataclass answers a non-field assignment with dataclasses' own
    #: super() TypeError rather than an AttributeError.
    assert not hasattr(remedy, "__dict__")
    match remedy:
        case Remedy(title, kind, applicability):
            assert (title, kind, applicability) == ("drop it", "quickfix", "machine")
        case _:  # pragma: no cover  -- the first arm is exhaustive for a Remedy
            pytest.fail("a Remedy did not match its own positional pattern")
    assert pickle.loads(pickle.dumps(remedy)) == remedy
    ground = Ground("metta-law", "HostLaws: a host call is an effect")
    assert pickle.loads(pickle.dumps(ground)) == ground
    assert not hasattr(ground, "__dict__")
