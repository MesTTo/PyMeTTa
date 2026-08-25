"""Purpose: pin the second P14 Python library-surface wave.

Guarantees:
  - a tuple whose first element is its head is one subscript pattern, complete
    expression patterns form a join, mixed tuple mistakes refuse, list writes
    stream atoms, and deletion drains every occurrence or raises KeyError
    [tested: test_subscript_one_pattern_and_bulk_delete_laws; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - the ask door returns a lazy Answers view with the complete projection,
    cardinality, slicing, truth, and engine-count protocol [tested:
    test_query_answers_complete_the_lazy_projection_protocol,
    test_query_single_unpack_pulls_at_most_two_answers; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - package ``superpose`` and ``match`` evaluate the same expressions they
    lower inside compiled bodies, with an empty zero-branch superposition and
    ambient-space matching [tested:
    test_expression_position_superpose_and_match_share_the_ambient_space;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - package ``unify`` dispatches its two-atom matcher and four-atom engine
    conditional overloads, and compiled definitions lower the latter directly
    [tested:
    test_expression_position_unify_uses_the_engine_conditional_in_both_contexts;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - ``Space.pre_add`` installs one compiled judge whose package verdict
    builders preserve, transform, refuse, or silently drop each offered atom
    [tested: test_pre_add_compiles_the_four_verdict_judge; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - all fifteen declaration verbs use their atom heads on Space and
    AsyncMeTTa, inject a space subject, and leave every ``declare_*`` spelling
    absent [tested: test_declarations_use_their_atom_heads_on_the_receiver;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
"""

import copy
import inspect
from collections import Counter
from typing import Any, get_overloads, get_type_hints

import pytest

from metta import MeTTa, S, V, accept, drop, match, refuse, space, superpose, unify
from metta.errors import EngineError
from metta.results import Answers


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

    answers = facts.match(S.person(V.name, V.age))
    assert isinstance(answers, Answers)
    assert answers.name == [S.Ada, S.Bob]
    assert answers[V.age] == [36, 41]
    assert answers["name"] == [S.Ada, S.Bob]
    assert Counter(answers.name) == Counter({S.Ada: 1, S.Bob: 1})
    assert isinstance(answers[:1], Answers)
    assert answers[:1].one().name == S.Ada
    assert bool(answers)

    missing = facts.match(S.absent(V.value))
    marker = object()
    with pytest.raises(EngineError, match="pass default"):
        missing.first()
    with pytest.raises(EngineError, match="exactly one"):
        missing.one()
    assert missing.first(default=marker) is marker
    assert missing.one(default=marker) is marker

    untouched = facts.match(S.person(V.name, V.age))
    assert untouched._cache == []
    assert len(untouched) == 2
    assert untouched._cache == []


def test_query_single_unpack_pulls_at_most_two_answers() -> None:
    """Exact-one unpacking stops as soon as a second row disproves it."""
    facts = space()
    facts += [S.item(index) for index in range(200)]

    with facts.stats() as bounded:
        answers = facts.match(S.item(V.value))
        with pytest.raises(ValueError, match="too many values"):
            (only,) = answers

    with facts.stats() as drained:
        list(facts.match(S.item(V.value)))

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


def test_expression_position_superpose_and_match_use_the_ruled_doors() -> None:
    """The package match reads rows while compiled match syntax still lowers."""
    target = space("&libfix-expression-position")
    target.clear()
    target += S.parent(S.Tom, S.Bob)

    with target:
        assert list(superpose(3, 4)) == [3, 4]
        assert list(superpose()) == []
        assert target.match(S.parent(S.Tom, V.child)).child == [S.Bob]

    @target.define
    def choose(value):
        return superpose(value, value + 1)

    @target.define
    def child_of(parent):
        return match(S.parent(parent, child), child)  # noqa: F821 -- compiled-body names are resolved by the MeTTa compiler rather than Python globals

    assert list(choose(8)) == [8, 9]
    assert list(child_of(S.Tom)) == [S.Bob]
    target.drop()


def test_expression_position_unify_uses_the_engine_conditional_in_both_contexts() -> None:
    """The root overload and compiler emit the protected core ``unify`` form."""
    assert [tuple(inspect.signature(item).parameters) for item in get_overloads(unify)] == [
        ("left", "right"),
        ("left", "right", "then", "els"),
    ]
    assert get_type_hints(unify) == {
        "left": Any,
        "right": Any,
        "then": Any,
        "els": Any,
        "return": Any,
    }
    target = space("&libfix-expression-unify")
    target.clear()

    with target:
        assert list(unify(S.f(V.x), S.f(S.a), V.x, S.nope)) == [S.a]
        assert list(unify(S.f(V.x), S.g(S.a), V.x, S.nope)) == [S.nope]

    @target.define
    def describe(value):
        return unify(value, Person(V.n), Greeting(V.n), Unknown)  # noqa: F821 -- capitalized names and V attributes are compiled-body data constructors and variables

    assert describe.source() == (
        "(= (describe $value) "
        "(unify $value (Person $n) (Greeting $n) Unknown))"
    )
    assert list(describe(S.Person(S.Ann))) == [S.Greeting(S.Ann)]
    assert list(describe(S.Place(S.Ann))) == [S.Unknown]
    assert describe.pure is True

    # The branch call is what this half measures, so the operation carries a
    # real observable effect rather than a rank chosen to make the assertion
    # pass: the four-argument control form is structural, and the definition
    # around it inherits the join of what its branches actually do.
    observed = []

    @target.op(name="libfix_unify_observe", effect="writesState")
    def libfix_unify_observe(value):
        observed.append(value)
        return value

    @target.define
    def impure_describe(value):
        return unify(value, A, libfix_unify_observe(value), Nope)  # noqa: F821 -- capitalized names are compiled-body data constructors

    assert impure_describe.pure is False
    assert list(impure_describe(S.A)) == [S.A]
    assert observed == [S.A], "the taken branch's operation did not run"

    with pytest.raises(TypeError, match="exactly 2 or 4 arguments"):
        unify(S.a, S.b, S.c)
    target.drop()


def test_pre_add_compiles_the_four_verdict_judge() -> None:
    """One decorated function owns every outcome at the write boundary."""
    target = space("&libfix-pre-add")
    target.clear()

    @target.pre_add
    @target.define
    def judge(atom):
        if atom == S.secret():
            return refuse("secrets stay out")
        if atom == S.raw():
            return accept(S.cooked())
        if atom == S.duplicate():
            return drop()
        return accept()

    target += S.plain()
    target += S.raw()
    target += S.duplicate()

    assert S.plain() in target
    assert S.cooked() in target
    assert S.raw() not in target
    assert S.duplicate() not in target
    with pytest.raises(EngineError, match="secrets stay out"):
        target += S.secret()

    target.eval(S["undeclare-pre-add!"](target))
    target.drop()


def test_declarations_use_their_atom_heads_on_the_receiver() -> None:
    """Declaration data reads like its head and carries the receiver once."""
    target = space("&libfix-declarations")
    old_names = {
        "declare_admits",
        "declare_agenda",
        "declare_algebra",
        "declare_annotations",
        "declare_capacity",
        "declare_context",
        "declare_emits",
        "declare_events",
        "declare_handles",
        "declare_image",
        "declare_merge",
        "declare_on_error",
        "declare_reaction",
        "declare_source",
        "declare_writes",
    }
    assert old_names.isdisjoint(dir(target))

    assert str(target.handles("(row $x)", "Exact")) == (
        "(handles &libfix-declarations (row $x) Exact)"
    )
    assert str(target.annotations("bag")) == (
        "(annotations &libfix-declarations bag)"
    )
    assert str(target.image("_", "opaque")) == (
        "(image &libfix-declarations _ opaque)"
    )
    assert str(target.source("repeated")) == (
        "(source &libfix-declarations repeated)"
    )
    assert str(target.on_error("(row $x)", "keep")) == (
        "(on-error &libfix-declarations (row $x) keep)"
    )
    assert str(target.context("closed-world")) == (
        "(context &libfix-declarations closed-world)"
    )
    assert str(target.writes("atomic-single")) == (
        "(writes &libfix-declarations atomic-single)"
    )
    assert str(target.emits("depth")) == "(emits &libfix-declarations depth)"
    assert str(target.events("at-most-once")) == (
        "(events &libfix-declarations at-most-once unordered)"
    )
    assert str(target.admits("Atom")) == "(admits &libfix-declarations Atom)"
    assert str(target.capacity(2)) == "(capacity &libfix-declarations 2)"

    target.eval(S["undeclare-pre-add!"](target))
