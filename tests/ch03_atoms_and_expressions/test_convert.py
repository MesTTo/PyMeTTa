"""Purpose: the four-image translator: defaults on sight, registration in
the pytree shape, typed declarations, lossless rebuilds, and explicit
refusals for unrepresentable state and type-name collisions.
Owns:
  - test_registration_collisions_are_serialized joins both registry workers
    before checking the unique owner [tested test_registration_collisions_are_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, make_dataclass
from enum import Enum, IntEnum, StrEnum
from typing import NamedTuple

import pytest

from metta import Expression, Grounded, S, Symbol, V, ground
from metta.convert import (
    _is_plain_class,
    build,
    declarations,
    project,
    register_type,
    unregister_type,
)
from metta.vocabularies import EffectClass


class Color(Enum):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    red = 1
    green = 2
    blue = 3


@dataclass
class Person:  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    name: str
    age: int


class CoordinateTuple(NamedTuple):  # noqa: D101  -- the local test double is documented by the scenario that constructs it
    x: float
    y: float


def test_enum_projects_to_symbols_with_declarations():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    projected = project(Color.red)
    assert projected.atom == Symbol("red")
    decls = set(map(str, projected.declarations))
    assert "(: Color Type)" in decls
    assert "(: red Color)" in decls and "(: blue Color)" in decls


def test_dataclass_projects_to_constructor_expression():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    projected = project(Person("Ada", 36))
    assert projected.atom == Expression(S.Person, "Ada", 36)
    assert "(: Person (-> String Number Person))" in set(map(str, projected.declarations))


def test_namedtuple_projects_like_a_dataclass():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert project(CoordinateTuple(1.0, 2.0)).atom == Expression(
        S.CoordinateTuple, 1.0, 2.0
    )


def test_nesting_is_the_pytree_rule():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @dataclass
    class Team:
        lead: Person
        colour: Color

    projected = project(Team(Person("Ada", 36), Color.blue))
    assert projected.atom == Expression(S.Team, Expression(S.Person, "Ada", 36), S.blue)
    decls = set(map(str, projected.declarations))
    assert "(: Color Type)" in decls
    assert any(d.startswith("(: Team") for d in decls)


def test_unregistered_object_stays_a_handle():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Opaque:
        pass

    thing = Opaque()
    projected = project(thing)
    assert isinstance(projected.atom, Grounded)
    assert projected.atom.value is thing
    assert projected.declarations == ()


def test_build_reverses_the_projection():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    person = Person("Ada", 36)
    rebuilt = build(project(person).atom)
    assert isinstance(rebuilt, Person) and rebuilt == person


def test_build_rebuilds_enums_with_the_class():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert build(Symbol("green"), Color) is Color.green


def test_registered_custom_type_round_trips():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Interval:
        def __init__(self, lo, hi):
            self.lo, self.hi = lo, hi

        def __eq__(self, other):
            return (self.lo, self.hi) == (other.lo, other.hi)

    register_type(
        Interval,
        image="expression",
        to_atom=lambda i: (i.lo, i.hi),
        from_atom=lambda lo, hi: Interval(lo, hi),
    )
    atom = project(Interval(1, 5)).atom
    assert atom == Expression(S.Interval, 1, 5)
    assert build(atom) == Interval(1, 5)


def test_type_registration_can_be_removed_and_its_name_reclaimed():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class FirstConversion:
        def __init__(self, value):
            self.value = value

    class SecondConversion:
        def __init__(self, value):
            self.value = value

    register_type(
        FirstConversion,
        name="RemovableConversionProbe",
        to_atom=lambda value: (value.value,),
        from_atom=FirstConversion,
        fields=("value",),
    )
    atom = project(FirstConversion(7)).atom
    rebuilt = build(atom)
    assert isinstance(rebuilt, FirstConversion) and rebuilt.value == 7
    unregister_type(FirstConversion)

    unregistered = FirstConversion(7)
    assert project(unregistered).atom == ground(unregistered)
    register_type(
        SecondConversion,
        name="RemovableConversionProbe",
        to_atom=lambda value: (value.value,),
        from_atom=SecondConversion,
        fields=("value",),
    )
    try:
        rebuilt = build(project(SecondConversion(9)).atom)
        assert isinstance(rebuilt, SecondConversion) and rebuilt.value == 9
    finally:
        unregister_type(SecondConversion)

    with pytest.raises(KeyError, match="FirstConversion"):
        unregister_type(FirstConversion)


def test_metta_dunder_hooks_work_unregistered():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Tagged:
        def __init__(self, label):
            self.label = label

        def __metta__(self):
            return Expression(S.Tagged, self.label)

        @classmethod
        def __from_metta__(cls, label):
            return cls(label)

    atom = project(Tagged("x")).atom
    assert atom == Expression(S.Tagged, "x")
    rebuilt = build(atom, Tagged)
    assert isinstance(rebuilt, Tagged) and rebuilt.label == "x"


def test_a_hook_outranks_an_encoder_inherited_from_a_base():
    """A class that says how to encode itself beats a base class's encoder.

    encode's fast table is keyed on the EXACT class, so a subclass misses it
    and used to fall to a singledispatch that resolves by MRO: a str subclass
    reached the str encoder and its own __metta__ was never asked. Seven of
    the eight shapes below were wrong that way, IntEnum encoding as a repr,
    and every StrEnum vocabgen.py emits was among them.

    Every shape, not one. Special-casing StrEnum, or registering an encoder
    for Enum, makes the reported case pass and leaves NamedTuple and every
    list subclass broken, which is why this is a table.
    """
    def hook(_self):
        return Symbol("HOOKED")

    class SubStr(str):
        __metta__ = hook

    class SubInt(int):
        __metta__ = hook

    class SubFloat(float):
        __metta__ = hook

    class SubList(list):
        __metta__ = hook

    class SubTuple(tuple):
        __metta__ = hook

    class SubNamedTuple(NamedTuple):
        x: int
        __metta__ = hook

    class SubEnum(Enum):
        A = 1
        __metta__ = hook

    class SubIntEnum(IntEnum):
        A = 1
        __metta__ = hook

    class SubStrEnum(StrEnum):
        A = "a"
        __metta__ = hook

    hooked = (SubStr("v"), SubInt(1), SubFloat(1.5), SubList([1]), SubTuple((1,)),
              SubNamedTuple(1), SubEnum.A, SubIntEnum.A, SubStrEnum.A)
    for value in hooked:
        assert project(value).atom == Symbol("HOOKED"), type(value).__name__


def test_a_value_without_a_hook_encodes_exactly_as_before():
    """The other half of the control: the fast path must not have moved.

    A fix that made every subclass reach __metta__ by weakening the exact-class
    table would pass the table above and change what a plain str costs and
    means. These are the shapes that must be untouched.
    """
    assert project("v").atom == "v"
    assert project(1).atom == 1
    assert project(1.5).atom == 1.5
    assert project([1, 2]).atom == Expression(1, 2)
    assert project((1, 2)).atom == Expression(1, 2)


def test_a_hook_outranks_a_default_derived_from_the_shape():
    """project() memoizes a default for an Enum, dataclass or NamedTuple, and
    a default is what applies when the author has NOT said otherwise.

    The hook was consulted only below a registration existing at all, so a
    NamedTuple carrying __metta__ projected as its constructor expression and
    an Enum as its member name. An EXPLICIT register_type still wins, because
    that is the author speaking too and it is the more specific of the two.
    """  # noqa: D205  -- one continuous invariant, not summary-and-body prose

    def hook(_self):
        return Symbol("HOOKED")

    @dataclass
    class Hooked:
        x: int
        __metta__ = hook

    class HookedTuple(NamedTuple):
        x: int
        __metta__ = hook

    class HookedEnum(Enum):
        A = 1
        __metta__ = hook

    for value in (Hooked(1), HookedTuple(1), HookedEnum.A):
        assert project(value).atom == Symbol("HOOKED"), type(value).__name__

    # And the shapes with no hook keep the defaults the docstring promises.
    @dataclass
    class Bare:
        x: int

    class BareTuple(NamedTuple):
        x: int

    class BareEnum(Enum):
        A = 1

    assert project(Bare(1)).atom == Expression(S.Bare, 1)
    assert project(BareTuple(1)).atom == Expression(S.BareTuple, 1)
    assert project(BareEnum.A).atom == S.A


def test_a_shipped_vocabulary_member_encodes_as_its_symbol():
    """llms.txt says each member IS its wire word and encodes as its symbol.

    Every class vocabgen.py writes is a StrEnum, so that sentence was false for
    all of them until the precedence above was fixed.
    """
    member = next(iter(EffectClass))
    assert project(member).atom == Symbol(member.value)


def test_declarations_without_an_instance():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert "(: Color Type)" in set(map(str, declarations(Color)))


def test_projected_facts_reason_in_the_engine(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._new_space()
    projected = project(Person("Ada", 36))
    space.add(*projected.declarations, projected.atom)
    space.add(project(Person("Bob", 41)).atom)
    rows = space.match(S.Person(V.name, V.age))
    assert {(str(r.name), int(r.age)) for r in rows} == {('"Ada"', 36), ('"Bob"', 41)}
    people = [build(a) for a in space.atoms() if str(a).startswith("(Person")]
    assert Person("Ada", 36) in people and Person("Bob", 41) in people


def test_grounded_and_container_projections():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert project(3).atom == Grounded(3)
    assert project([1, 2]).atom == Expression(1, 2)
    assert isinstance(ground({"a": 1}), Grounded)


def test_pydantic_models_project_like_dataclasses():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    pydantic = pytest.importorskip("pydantic")

    class Reading(pydantic.BaseModel):
        sensor: str
        value: float

    projected = project(Reading(sensor="t1", value=21.5))
    assert projected.atom == Expression(S.Reading, "t1", 21.5)
    assert "(: Reading (-> String Number Reading))" in set(
        map(str, projected.declarations)
    )
    rebuilt = build(projected.atom, Reading)
    assert isinstance(rebuilt, Reading) and rebuilt.value == 21.5
    # The rebuild runs through the model itself, so validation runs where
    # pydantic runs it: a field refusing its type is pydantic's own error.
    with pytest.raises(pydantic.ValidationError):
        build(Expression(S.Reading, "t1", S.tall), Reading)


def test_pydantic_alias_fields_rebuild(metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    pydantic = pytest.importorskip("pydantic")

    class Wire(pydantic.BaseModel):
        internal: int = pydantic.Field(alias="external")
        model_config = pydantic.ConfigDict(populate_by_name=True)

    projected = project(Wire(external=7))
    rebuilt = build(projected.atom, Wire)
    assert isinstance(rebuilt, Wire) and rebuilt.internal == 7


def test_parameterized_field_annotations_rebuild_nested_enums():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @dataclass
    class Palette:
        colours: list[Color]
        favourite: Color | None

    projected = project(Palette([Color.red, Color.blue], Color.red))
    rebuilt = build(projected.atom, Palette)
    assert rebuilt == Palette([Color.red, Color.blue], Color.red)
    assert isinstance(rebuilt.colours[0], Color)
    assert isinstance(rebuilt.favourite, Color)


def test_plain_class_detection_never_mistakes_a_generic_alias_for_a_class():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert _is_plain_class(list) is True
    assert _is_plain_class(list[Color]) is False


def test_enum_typed_field_uses_the_enum_in_constructor_declarations():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class ConversionShade(Enum):
        RED = 1
        BLUE = 2

    @dataclass
    class EnumPaint:
        shade: ConversionShade

    projected = project(EnumPaint(ConversionShade.RED))
    assert "(: EnumPaint (-> ConversionShade EnumPaint))" in set(
        map(str, projected.declarations)
    )
    assert build(projected.atom, EnumPaint) == EnumPaint(ConversionShade.RED)


def test_pydantic_extra_fields_are_refused_by_name():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    pydantic = pytest.importorskip("pydantic")

    class ExtraRejectModel(pydantic.BaseModel):
        value: int
        model_config = pydantic.ConfigDict(extra="allow")

    value = ExtraRejectModel(value=1, retained=2, also_retained=3)
    with pytest.raises(
        TypeError, match=r"extra fields would be lost \(also_retained, retained\)"
    ):
        project(value)


def test_keyword_only_dataclass_rebuilds_by_field_name():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @dataclass(kw_only=True)
    class KeywordOnlyRecord:
        required: int
        optional: int = 7

    original = KeywordOnlyRecord(required=1)
    assert build(project(original).atom, KeywordOnlyRecord) == original


def test_init_false_dataclass_requires_an_explicit_reverse():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @dataclass
    class DerivedStateRecord:
        value: int
        cached: int = field(default=9, init=False)

    original = DerivedStateRecord(1)
    with pytest.raises(TypeError, match=r"init=False state.*cached"):
        project(original)

    def rebuild(value, cached):
        rebuilt = DerivedStateRecord(value)
        rebuilt.cached = cached
        return rebuilt

    register_type(
        DerivedStateRecord,
        to_atom=lambda item: (item.value, item.cached),
        from_atom=rebuild,
        fields=("value", "cached"),
    )
    assert build(project(original).atom, DerivedStateRecord) == original


def test_type_name_collision_is_refused_and_build_honors_requested_class():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    first_cls = make_dataclass("ConversionCollision", [("left", int)])
    second_cls = make_dataclass("ConversionCollision", [("right", int)])
    first = first_cls(7)
    atom = project(first).atom

    with pytest.raises(ValueError, match=r"type name 'ConversionCollision'.*already"):
        project(second_cls("later"))
    with pytest.raises(TypeError, match=r"belongs to .*not"):
        build(atom, second_cls)
    assert build(atom, first_cls) == first


def test_invalid_namedtuple_fields_are_refused():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class InvalidTuple(tuple):
        _fields = object()

    with pytest.raises(TypeError, match="invalid NamedTuple fields"):
        project(InvalidTuple())

def test_registration_collisions_are_serialized():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    first = make_dataclass("ConcurrentOwnerProbe", [("value", int)])
    second = make_dataclass("ConcurrentOwnerProbe", [("value", int)])

    def attempt(cls):
        try:
            register_type(cls)
        except ValueError:
            return "collision"
        return "owner"

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = sorted(workers.map(attempt, (first, second)))

    assert outcomes == ["collision", "owner"]


def test_union_build_selects_by_shape_and_surfaces_reverse_errors():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert build(Grounded(3), str | int) == 3

    class BrokenReverse:
        pass

    def reject(_value):
        msg = "selected reverse failed"
        raise TypeError(msg)

    register_type(
        BrokenReverse,
        name="BrokenReverseProbe",
        to_atom=lambda value: (value,),
        from_atom=reject,
        fields=("value",),
    )
    with pytest.raises(TypeError, match="selected reverse failed"):
        build(Expression(S.BrokenReverseProbe, 1), BrokenReverse | str)
