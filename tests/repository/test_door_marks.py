"""Purpose: verify function marks and receiver collections follow Python binding.

Guarantees: marks retain function identity and overloads; class collections
respect descriptor and MRO shadowing without evaluating annotations
[tested: this file; commit=WORKTREE].
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, get_overloads, overload

import pytest

from metta import Answers, Rows
from metta.doors import DoorOwner, Kind, door
from metta.remote import RemoteCursor, RemoteSpace

if TYPE_CHECKING:
    from pathlib import Path


def test_a_mark_preserves_the_function_and_its_overload_registry():
    """A marker adds metadata without introducing a callable wrapper."""
    @overload
    def identity(value: int) -> int: ...

    @overload
    def identity(value: str) -> str: ...

    def identity(value):
        return value

    declarations = get_overloads(identity)
    signature = inspect.signature(identity)
    marked = door(Kind.query)(identity)
    assert marked is identity
    assert get_overloads(marked) == declarations
    assert len(declarations) == 2
    assert inspect.signature(marked) == signature


def test_class_marks_unwrap_descriptors_without_resolving_annotation_names():
    """Class creation observes functions without calling descriptor accessors."""
    class Receiver(DoorOwner):
        @staticmethod
        @door(Kind.query)
        def static(value: Path):
            return value

        @classmethod
        @door(Kind.query)
        def class_method(cls, value):
            return cls, value

        @property
        @door(Kind.query)
        def value(self):
            msg = "the descriptor must not be evaluated"
            raise AssertionError(msg)

    members = Receiver.__door_members__
    assert set(members) == {"static", "class_method", "value"}
    assert "Path" not in globals()
    assert inspect.get_annotations(members["static"], eval_str=False) == {"value": "Path"}
    for name in ("static", "class_method"):
        assert members[name] is vars(Receiver)[name].__func__
    assert members["value"] is vars(Receiver)["value"].fget
    with pytest.raises(TypeError):
        members["extra"] = lambda: None


@pytest.mark.parametrize("replacement", [None, lambda _self: 1, property(lambda _self: 1)])
def test_an_unmarked_override_removes_the_inherited_mark(replacement):
    """The visible class member determines whether its name is still marked."""
    class Parent(DoorOwner):
        @door(Kind.query)
        def value(self):
            return 0

    class Child(Parent):
        value = replacement

    assert set(Parent.__door_members__) == {"value"}
    assert Child.__door_members__ == {}


def test_multiple_inheritance_follows_the_class_mro_and_keeps_empty_owners():
    """A diamond uses the same first visible definition as attribute lookup."""
    class Left(DoorOwner):
        @door(Kind.query)
        def value(self):
            return "left"

    class Right(DoorOwner):
        @door(Kind.query)
        def value(self):
            return "right"

    class Child(Left, Right):
        pass

    class Empty(DoorOwner):
        pass

    assert Child.__door_members__["value"] is Left.value
    assert Empty.__door_members__ == {}


@pytest.mark.parametrize("receiver", [Rows, Answers, RemoteSpace, RemoteCursor])
def test_shipped_receiver_collections_name_their_actual_marked_functions(receiver):
    """Every shipped class collector exposes immutable live function identities."""
    members = receiver.__door_members__
    assert members
    for name, function in members.items():
        visible = inspect.getattr_static(receiver, name)
        if isinstance(visible, property):
            visible = visible.fget
        elif isinstance(visible, (classmethod, staticmethod)):
            visible = visible.__func__
        assert function is visible
        assert hasattr(function, "__metta_door__")
