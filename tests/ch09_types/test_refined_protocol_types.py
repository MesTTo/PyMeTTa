"""Purpose: verify annotation and live protocol types use ordinary atom terms.

Guarantees:
  - atom metadata refines every annotation alternative and live protocols can
    compute expression types without losing variable identity [tested:
    test_atom_metadata_refines_annotation_alternatives,
    test_computed_protocol_types_are_live_and_removable;
    commit=WORKTREE]
"""

import contextlib
from typing import Annotated

import pytest

from metta import S, V, ground, integrate
from metta.errors import EngineError
from metta.ops import annotation_atom_for, type_atoms_for


def test_atom_metadata_refines_annotation_alternatives():
    """Type atoms are operational; Python text stays catalog metadata."""
    annotation = Annotated[int | str, S.Unit(V.unit), "documented unit"]
    assert [str(atom) for atom in type_atoms_for(annotation)] == [
        "(Annotated Number (Unit $unit))",
        "(Annotated String (Unit $unit))",
    ]
    assert str(annotation_atom_for(annotation)) == (
        '(Annotated (Union Number String) (Unit $unit) "documented unit")'
    )
    assert type_atoms_for(Annotated[int, "documented unit"]) == [S.Number]


def test_computed_protocol_types_are_live_and_removable(metta):
    """The bridge recomputes an object's type and shares each repeated variable."""
    class Reading:
        def __init__(self, count):
            self.count = count

    def predicate(value):
        return isinstance(value, Reading)

    def type_expression(value):
        return S.ReadingType(value.count, V.item, V.item)

    value = Reading(2)
    integrate.register_object_type(predicate, type_expression)
    try:
        assert metta.cast(value, S.ReadingType(2, S.Number, S.Number)) is value
        with pytest.raises(TypeError, match="does not admit type"):
            metta.cast(value, S.ReadingType(2, S.Number, S.String))
        value.count = 3
        assert metta.cast(value, S.ReadingType(3, S.String, S.String)) is value
        assert S.Reading in metta.fn.get_type(ground(value))
    finally:
        integrate.unregister_object_type(predicate, type_expression)
    with pytest.raises(TypeError, match="does not admit type"):
        metta.cast(value, S.ReadingType(3, S.Number, S.Number))


def test_protocol_type_projection_failure_is_reported(metta):
    """A bad computed type raises at its provider instead of disappearing."""
    class InvalidReading:
        pass

    def predicate(value):
        return isinstance(value, InvalidReading)

    def invalid_type(_value):
        return 42

    integrate.register_object_type(predicate, invalid_type)
    try:
        with pytest.raises(EngineError, match="must return a type Atom"):
            list(metta.fn.get_type(ground(InvalidReading())))
    finally:
        integrate.unregister_object_type(predicate, invalid_type)


@pytest.mark.parametrize("kind", [S.RegisteredReading, S.RegisteredReading(S.Number)])
def test_literal_protocol_type_atoms_are_not_called(metta, kind):
    """Atom call syntax must not turn a literal type into a provider call."""
    class ProtocolReading:
        pass

    def predicate(value):
        return isinstance(value, ProtocolReading)

    value = ProtocolReading()
    integrate.register_object_type(predicate, kind)
    try:
        assert metta.cast(value, kind) is value
    finally:
        integrate.unregister_object_type(predicate, kind)


def test_computed_protocol_removal_uses_provider_identity(metta):
    """Equal provider objects still own distinct removable registrations."""
    class Sample:
        pass

    class Provider:
        def __init__(self, count):
            self.count = count

        def __call__(self, _value):
            return S.SampleType(self.count)

        def __eq__(self, other):
            return isinstance(other, Provider)

    def predicate(value):
        return isinstance(value, Sample)

    first, second = Provider(1), Provider(2)
    integrate.register_object_type(predicate, first)
    integrate.register_object_type(predicate, second)
    try:
        integrate.unregister_object_type(predicate, first)
        value = Sample()
        assert metta.cast(value, S.SampleType(2)) is value
        with pytest.raises(TypeError, match="does not admit type"):
            metta.cast(value, S.SampleType(1))
    finally:
        for provider in (first, second):
            with contextlib.suppress(KeyError):
                integrate.unregister_object_type(predicate, provider)
