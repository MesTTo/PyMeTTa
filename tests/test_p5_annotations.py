"""Purpose: pin Phase 5's Python annotation and conversion seam.

Guarantees:
  - Annotated values of one base type retain distinct matchable metadata
    claims without changing their arrow slots [tested:
    test_two_values_of_one_base_type_are_distinguishable_by_their_metadata;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - container annotation acceptance selects its own callable's declarations
    from the session space instead of assuming no earlier registration exists
    [tested: test_the_four_containers_share_one_parameterised_treatment;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import types
from collections.abc import Sequence
from dataclasses import InitVar, dataclass
from enum import Enum, Flag, IntEnum, StrEnum, auto
from typing import (
    Annotated,
    Literal,
    Never,
    NewType,
    Self,
    TypedDict,
    TypeIs,
    TypeVar,
    overload,
)

import pytest

from petta import Atom, Expression, Grounded, MeTTa, S, Symbol, Variable, ground, wire
from petta import integrate as pi
from petta.convert import build, project, register_type, unregister_type
from petta.ops import annotation_atom_for, type_atoms_for


def test_the_four_metatypes_stay_distinct_across_the_seam():
    """Prove Atom, Symbol, Variable, Expression, and Grounded map to five distinct MeTTa metatype symbols."""
    expected = {
        Atom: "Atom",
        Symbol: "Symbol",
        Variable: "Variable",
        Expression: "Expression",
        Grounded: "Grounded",
    }

    assert {
        annotation: str(type_atoms_for(annotation)[0])
        for annotation in expected
    } == expected


def test_the_four_containers_share_one_parameterised_treatment(metta):
    """Prove tuple, list, dict, and set share one parameterised projection, rebuild, and annotation treatment."""
    cases = (
        (tuple[int, str], (1, "a"), "(tuple Number String)"),
        (list[int], [1, 2], "(list Number)"),
        (dict[str, int], {"a": 1}, "(dict String Number)"),
        (set[int], {2, 1}, "(set Number)"),
    )

    for annotation, value, type_image in cases:
        projected = project(value, annotation)
        expected_metta_type = (
            "(Number String)" if annotation.__origin__ is tuple else "Expression"
        )
        assert str(type_atoms_for(annotation)[0]) == expected_metta_type
        assert str(annotation_atom_for(annotation)) == type_image
        assert isinstance(projected.atom, Expression)
        assert build(projected.atom, annotation) == value

    def container_probe(
        fixed: tuple[int, str],  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        sequence: list[int],  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        mapping: dict[str, int],  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        members: set[int],
    ) -> set[int]:
        return members

    metta.op(container_probe)
    claims = {
        str(atom)
        for atom in metta.atoms()
        if isinstance(atom, Expression)
        and atom.head == Symbol("annotation")
        and atom.args[0] == Symbol("container_probe")
    }
    assert claims == {
        "(annotation container_probe (param 1 (tuple Number String)))",
        "(annotation container_probe (param 2 (list Number)))",
        "(annotation container_probe (param 3 (dict String Number)))",
        "(annotation container_probe (param 4 (set Number)))",
        "(annotation container_probe (return (set Number)))",
    }


def test_int_str_and_flag_enums_each_project_with_their_declarations():
    """Prove IntEnum, StrEnum, and Flag values project to symbols carrying their type declarations."""

    class Count(IntEnum):
        one = 1

    class State(StrEnum):
        ready = "ready"

    class Capability(Flag):
        read = auto()
        write = auto()

    for value, symbol, type_name in (
        (Count.one, "one", "Count"),
        (State.ready, "ready", "State"),
        (Capability.read | Capability.write, "read|write", "Capability"),
    ):
        projected = project(value)
        assert projected.atom == Symbol(symbol)
        declarations = set(map(str, projected.declarations))
        assert f"(: {type_name} Type)" in declarations
        assert f"(: {symbol} {type_name})" in declarations


def test_a_typed_dict_annotation_agrees_with_its_value(metta):
    """Prove a TypedDict value projects, rebuilds, and registers with field-accurate annotation claims."""

    class Config(TypedDict):
        retries: int
        label: str

    value: Config = {"retries": 3, "label": "fast"}
    projected = project(value, Config)
    assert projected.atom == Expression([Symbol("Config"), Grounded(3), Grounded("fast")])
    assert type_atoms_for(Config) == [Symbol("Config")]
    assert "(: Config (-> Number String Config))" in set(
        map(str, projected.declarations)
    )
    assert build(projected.atom, Config) == value

    def echo_config(config: Config) -> Config:
        return config

    metta.op(echo_config)
    assert metta.eval(Expression([S.echo_config, projected.atom])) == [projected.atom]
    claims = {str(atom) for atom in metta.atoms()}
    assert "(annotation echo_config (param 1 (TypedDict Config (field retries Number) (field label String))))" in claims
    assert "(annotation echo_config (return (TypedDict Config (field retries Number) (field label String))))" in claims


def test_every_advanced_annotation_reaches_metta_as_a_target_symbol(metta):
    """Prove every advanced typing annotation lowers to its MeTTa target and registers its claims."""
    UserId = NewType("UserId", int)
    Bounded = TypeVar("Bounded", bound=int)
    Choice = TypeVar("Choice", int, str)

    expected = {
        Literal["on", "off"]: ["String"],
        UserId: ["UserId"],
        Bounded: ["Number"],
        Choice: ["Number", "String"],
        TypeIs[int]: ["Bool"],
        Never: ["Empty"],
        Self: ["$t"],
        type[int]: ["Type"],
        complex: ["Number"],
    }
    assert {
        annotation: [str(atom) for atom in type_atoms_for(annotation)]
        for annotation in expected
    } == expected

    @overload
    def overloaded(value: int) -> int: ...

    @overload
    def overloaded(value: str) -> str: ...

    def overloaded(value):
        return value

    metta.op(overloaded)
    declarations = {str(atom) for atom in metta.atoms()}
    assert "(: overloaded (-> Number Number))" in declarations
    assert "(: overloaded (-> String String))" in declarations

    def advanced(  # noqa: PLR0917 - one signature exercises every target.
        mode: Literal["on", "off"],
        user: UserId,
        bounded: Bounded,
        choice: Choice,
        guard: TypeIs[int],
        owner: type[int],
        number: complex,
    ) -> Never:
        raise AssertionError((mode, user, bounded, choice, guard, owner, number))

    metta.op(advanced)
    claims = {str(atom) for atom in metta.atoms() if "advanced" in str(atom)}
    assert "(annotation advanced (param 1 (Literal \"on\" \"off\")))" in claims
    assert "(annotation advanced (param 2 (NewType UserId Number)))" in claims
    assert any(
        claim.startswith("(annotation advanced (param 3 (TypeVar $")
        and claim.endswith(" (bound Number))))")
        for claim in claims
    )
    assert any(
        claim.startswith("(annotation advanced (param 4 (TypeVar $")
        and claim.endswith(" (one_of Number String))))")
        for claim in claims
    )
    assert "(annotation advanced (param 5 (TypeIs Number)))" in claims
    assert "(annotation advanced (param 6 (type Number)))" in claims
    assert "(annotation advanced (return Empty))" in claims


def test_two_values_of_one_base_type_are_distinguishable_by_their_metadata(metta):
    """Prove Annotated metadata keeps two values of one base type distinguishable without changing arrows."""

    def convert_units(
        metres: Annotated[int, "metres"],
        feet: Annotated[int, "feet"],
    ) -> int:
        return metres + feet

    metta.op(convert_units)
    declarations = {str(atom) for atom in metta.atoms()}
    assert "(: convert_units (-> Number Number Number))" in declarations
    assert (
        '(annotation convert_units (param 1 (Annotated Number "metres")))'
        in declarations
    )
    assert (
        '(annotation convert_units (param 2 (Annotated Number "feet")))'
        in declarations
    )

    def current_space(engine: Annotated[MeTTa, "engine"]):
        return engine

    metta.op(current_space, name="annotated-engine")
    ((answer,),) = metta.run("!(annotated-engine)")
    assert isinstance(answer, Grounded)
    assert isinstance(answer.value, MeTTa)
    assert answer.value.self.name == metta.name


def test_dunder_metta_is_read_off_the_class_not_the_instance():
    """Prove projection reads __metta__ off the class, so instance hooks and properties never run."""
    looked_up: list[str] = []

    class Proxy:
        def __getattr__(self, name):
            looked_up.append(name)
            return lambda: S.wrong

    proxy = Proxy()
    assert project(proxy).atom == ground(proxy)
    assert wire.encode(proxy) == ground(proxy)
    assert looked_up == []

    class Tagged:
        def __metta__(self):
            return S.tagged

    assert project(Tagged()).atom == S.tagged
    assert wire.encode(Tagged()) == S.tagged

    class PropertyTrap:
        @property
        def __metta__(self):
            looked_up.append("property")
            return S.wrong

    trapped = PropertyTrap()
    assert project(trapped).atom == ground(trapped)
    assert wire.encode(trapped) == ground(trapped)
    assert looked_up == []


def test_a_slots_dataclass_registration_follows_the_new_class_or_refuses():
    """Prove projecting a dataclass(slots=True) instance registered on its pre-slots class refuses with guidance."""
    registered = []

    def capture(cls):
        registered.append(register_type(cls))
        return cls

    @dataclass(slots=True)
    @capture
    class SlottedRegistrationProbe:
        value: int

    try:
        with pytest.raises(
            ValueError,
            match=r"dataclass\(slots=True\).*register_type outside",
        ):
            project(SlottedRegistrationProbe(1))
    finally:
        unregister_type(registered[0])


def test_each_remaining_annotation_shape_refuses_or_carries(metta, monkeypatch):
    """Prove each remaining annotation shape either round-trips faithfully or refuses with a named reason."""

    @dataclass
    class BareSequence:
        items: list

    sequence = BareSequence([Expression([S.item, Grounded(1)])])
    sequence_atom = project(sequence).atom
    assert build(sequence_atom, BareSequence) == sequence
    assert build(project([1, 2], Sequence[int]).atom, Sequence[int]) == [1, 2]

    payload = bytearray(b"abc")
    buffer_atom = project(payload).atom
    assert isinstance(buffer_atom, Expression) and buffer_atom.head == S.Buffer
    metadata = {child.head: child.args for child in buffer_atom.args[1:]}
    assert metadata == {
        S.shape: (Grounded(3),),
        S.format: (Grounded("B"),),
        S.itemsize: (Grounded(1),),
        S.ndim: (Grounded(1),),
        S.strides: (Grounded(1),),
        S.readonly: (Grounded(False),),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        S["c-contiguous"]: (Grounded(True),),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    }
    assert build(buffer_atom) is payload
    assert build(project(memoryview(payload)).atom).obj is payload

    @dataclass
    class RequiredInitVar:
        value: int
        seed: InitVar[int]

    with pytest.raises(TypeError, match=r"RequiredInitVar.*seed.*default"):
        project(RequiredInitVar(1, 2))

    @dataclass
    class DefaultedInitVar:
        value: int
        seed: InitVar[int] = 0

    defaulted = DefaultedInitVar(1)
    assert build(project(defaulted).atom, DefaultedInitVar) == defaulted

    def kwargs(value: int, **options) -> int:
        return value + len(options)

    with pytest.raises(TypeError, match=r"\*\*options.*unreachable"):
        metta.op(kwargs)

    class Choice(Enum):
        first = 1

    def choose() -> Choice:
        return Choice.first

    metta.op(choose)
    assert "(: choose (-> Choice))" in {str(atom) for atom in metta.atoms()}

    installed: list[str] = []

    class Target:
        def __init__(self, name, requires=()):
            self.name = name
            self.PETTA_REQUIRES = requires

        def install(self, _metta):
            installed.append(self.name)

    def entry(name, target):
        return types.SimpleNamespace(name=name, load=lambda: target)

    base = Target("p5-order-base")
    child = Target("p5-order-child", ("p5-order-base",))
    monkeypatch.setattr(
        pi.metadata,
        "entry_points",
        lambda *, group: (entry("p5-order-child", child), entry("p5-order-base", base)),  # noqa: ARG005  -- the test double preserves entry_points' keyword-only signature its caller invokes by name
    )
    assert pi.discover(metta) == ["p5-order-base", "p5-order-child"]
    assert installed == ["p5-order-base", "p5-order-child"]

    left = Target("p5-cycle-left", ("p5-cycle-right",))
    right = Target("p5-cycle-right", ("p5-cycle-left",))
    monkeypatch.setattr(
        pi.metadata,
        "entry_points",
        lambda *, group: (entry("p5-cycle-left", left), entry("p5-cycle-right", right)),  # noqa: ARG005  -- the test double preserves entry_points' keyword-only signature its caller invokes by name
    )
    with pytest.raises(
        pi.PettaError,
        match=r"dependency cycle: p5-cycle-left -> p5-cycle-right -> p5-cycle-left",
    ):
        pi.discover(metta)

    duplicate = Target("p5-duplicate")
    monkeypatch.setattr(
        pi.metadata,
        "entry_points",
        lambda *, group: (entry("p5-duplicate", duplicate),) * 2,  # noqa: ARG005  -- the test double preserves entry_points' keyword-only signature its caller invokes by name
    )
    with pytest.raises(pi.PettaError, match=r"duplicate.*p5-duplicate"):
        pi.discover(metta)
