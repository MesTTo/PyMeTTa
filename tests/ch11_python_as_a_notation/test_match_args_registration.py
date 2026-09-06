"""Purpose: a class stating its positional fields through __match_args__ crosses by default.

It destructures field-wise both ways, with the positional constructor as the reverse.
Guarantees:
  - a plain class and an attrs class project to a constructor expression and
    rebuild through cls(*parts) with no registration
    [tested: test_a_plain_class_with_match_args_destructures_by_default,
    test_an_attrs_class_destructures_by_default; commit=WORKTREE]
  - hidden state is refused rather than lost, __metta__ outranks the default,
    and pydantic models and atoms keep their own images
    [tested: test_match_args_registration_refuses_hidden_state,
    test_dunder_metta_outranks_the_match_args_default,
    test_pydantic_and_atoms_are_untouched_by_the_match_args_default;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from metta import convert
from metta.atoms import S, Symbol


class MatchArgsPoint:
    """A plain class stating its positional fields and their types."""

    __match_args__ = ("x", "y")
    x: int
    y: int

    def __init__(self, x: int, y: int) -> None:
        """Hold the two coordinates."""
        self.x = x
        self.y = y


def test_a_plain_class_with_match_args_destructures_by_default():
    """The projection is the constructor expression and build is cls(*parts)."""
    try:
        projected = convert.project(MatchArgsPoint(1, 2))
        assert str(projected.atom) == "(MatchArgsPoint 1 2)"
        assert "(: MatchArgsPoint (-> Number Number MatchArgsPoint))" in {
            str(d) for d in projected.declarations
        }
        rebuilt = convert.build(projected.atom, MatchArgsPoint)
        assert isinstance(rebuilt, MatchArgsPoint)
        assert (rebuilt.x, rebuilt.y) == (1, 2)
        assert isinstance(convert.build(projected.atom), MatchArgsPoint)
    finally:
        convert.unregister_type(MatchArgsPoint)


def test_an_attrs_class_destructures_by_default():
    """The attrs library sets __match_args__ for every define()d class, so it crosses unasked."""
    attrs = pytest.importorskip("attrs")

    @attrs.define
    class SensorReading:
        sensor: str
        value: float

    try:
        projected = convert.project(SensorReading("t1", 2.5))
        assert str(projected.atom) == '(SensorReading "t1" 2.5)'
        assert convert.build(projected.atom, SensorReading) == SensorReading("t1", 2.5)
    finally:
        convert.unregister_type(SensorReading)


def test_match_args_registration_refuses_hidden_state():
    """State the tuple does not name would be lost, so it is refused by name."""
    attrs = pytest.importorskip("attrs")

    @attrs.define
    class LabelledSample:
        value: int
        label: str = attrs.field(default="x", kw_only=True)

    with pytest.raises(TypeError, match=r"keeps attrs state its __match_args__ does not name \(label\)"):
        convert.project(LabelledSample(1))

    class HiddenSecond:
        __match_args__ = ("first",)

        def __init__(self, first, second):
            self.first = first
            self.second = second

    with pytest.raises(TypeError, match=r"requires constructor state its __match_args__ does not name \(second\)"):
        convert.project(HiddenSecond(1, 2))


def test_dunder_metta_outranks_the_match_args_default():
    """The author's own hook is the more specific declaration."""

    class TaggedByHook:
        __match_args__ = ("value",)

        def __init__(self, value):
            self.value = value

        def __metta__(self):
            return S.tagged(self.value)

    assert str(convert.project(TaggedByHook(3)).atom) == "(tagged 3)"
    # The hook is the author speaking, so no default is memoised beside it and
    # the class claims no type name.
    with pytest.raises(TypeError, match="has no default image"):
        convert.ensure_registered(TaggedByHook)


def test_pydantic_and_atoms_are_untouched_by_the_match_args_default():
    """A pydantic model keeps its own registration and an atom has no default image."""
    with pytest.raises(TypeError, match="has no default image"):
        convert.ensure_registered(Symbol)
    pydantic = pytest.importorskip("pydantic")

    class MatchArgsModel(pydantic.BaseModel):
        name: str
        count: int = 1

    try:
        projected = convert.project(MatchArgsModel(name="a"))
        assert str(projected.atom) == '(MatchArgsModel "a" 1)'
        assert convert.build(projected.atom, MatchArgsModel) == MatchArgsModel(name="a")
    finally:
        convert.unregister_type(MatchArgsModel)
