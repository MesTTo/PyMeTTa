"""Purpose: pin the second P14 Python library-surface wave.

Guarantees:
  - a tuple whose first element is its head is one subscript pattern, complete
    expression patterns form a join, mixed tuple mistakes refuse, list writes
    stream atoms, and deletion drains every occurrence or raises KeyError
    [tested: test_subscript_one_pattern_and_bulk_delete_laws; commit=WORKTREE]
  - the ask door returns a lazy Answers view with the complete projection,
    cardinality, slicing, truth, and engine-count protocol [tested:
    test_query_answers_complete_the_lazy_projection_protocol,
    test_query_single_unpack_pulls_at_most_two_answers; commit=WORKTREE]
"""

import copy
from collections import Counter

import pytest

from petta import MeTTa, S, V, space
from petta.errors import EngineError
from petta.results import Answers


def test_subscript_one_pattern_and_bulk_delete_laws() -> None:
    """Subscript dispatch follows pattern shape instead of flattening facts."""
    facts = space()
    facts += [
        (S.Parent, S.Tom, S.Bob),
        (S.Parent, S.Pam, S.Bob),
        (S.Female, S.Pam),
        (S.Tag,),
    ]

    parents = facts[(S.Parent, V.person, S.Bob)]
    assert parents.person == [S.Tom, S.Pam]
    assert facts[(V.only,)].only == [S.Tag]

    joined = facts[
        S.Parent(V.person, S.Bob),
        S.Female(V.person),
    ]
    assert joined.person == [S.Pam]

    with pytest.raises(TypeError, match=r"one pattern.*join"):
        _ = facts[S.Parent(V.person, S.Bob), S.Female]

    del facts[(S.Parent, V.person, S.Bob)]
    assert facts[(S.Parent, V.person, S.Bob)] == []
    with pytest.raises(KeyError):
        del facts[(S.Parent, V.person, S.Bob)]


def test_query_answers_complete_the_lazy_projection_protocol() -> None:
    """Every query projection shares one lazy answer stream."""
    facts = space()
    facts += [S.person(S.Ada, 36), S.person(S.Bob, 41)]

    answers = facts.query(S.person(V.name, V.age))
    assert isinstance(answers, Answers)
    assert answers.name == [S.Ada, S.Bob]
    assert answers[V.age] == [36, 41]
    assert answers["name"] == [S.Ada, S.Bob]
    assert Counter(answers.name) == Counter({S.Ada: 1, S.Bob: 1})
    assert isinstance(answers[:1], Answers)
    assert answers[:1].one().name == S.Ada
    assert bool(answers)

    missing = facts.query(S.absent(V.value))
    marker = object()
    with pytest.raises(EngineError, match="pass default"):
        missing.first()
    with pytest.raises(EngineError, match="exactly one"):
        missing.one()
    assert missing.first(default=marker) is marker
    assert missing.one(default=marker) is marker

    untouched = facts.query(S.person(V.name, V.age))
    assert untouched._cache == []
    assert len(untouched) == 2
    assert untouched._cache == []


def test_query_single_unpack_pulls_at_most_two_answers() -> None:
    """Exact-one unpacking stops as soon as a second row disproves it."""
    facts = space()
    facts += [S.item(index) for index in range(200)]

    with facts.stats() as bounded:
        answers = facts.query(S.item(V.value))
        with pytest.raises(ValueError, match="too many values"):
            (only,) = answers

    with facts.stats() as drained:
        list(facts.query(S.item(V.value)))

    assert bounded.inferences * 5 < drained.inferences


def test_define_accepts_a_plain_annotated_data_class() -> None:
    """A plain annotated class gets constructor, fields, and replacement."""
    target = MeTTa().space()

    @target.define
    class InventoryLine:
        sku: str
        quantity: int = 1

    one = InventoryLine("bolts")
    two = one.__replace__(quantity=2)

    assert InventoryLine.__match_args__ == ("sku", "quantity")
    assert (one.sku, one.quantity) == ("bolts", 1)
    assert (two.sku, two.quantity) == ("bolts", 2)
    assert str(one.__metta__()) == '(InventoryLine "bolts" 1)'
    assert str(target.eval(S.InventoryLine(one.sku, one.quantity))[0]) == (
        '(InventoryLine "bolts" 1)'
    )
    assert target.eval(S["InventoryLine-quantity"](two))[0] == 2
    if hasattr(copy, "replace"):
        assert copy.replace(two, quantity=3).quantity == 3
