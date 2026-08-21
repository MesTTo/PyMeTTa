"""Purpose: pin Phase 5's Python annotation and conversion seam.

Guarantees:
  - Annotated values of one base type retain distinct matchable metadata
    claims without changing their arrow slots [tested:
    test_two_values_of_one_base_type_are_distinguishable_by_their_metadata;
    commit=6fbd5872cc0ff7abf9c99b90f915f8a31470a861]
  - container annotation acceptance selects its own callable's declarations
    from the session space instead of assuming no earlier registration exists
    [tested: test_the_four_containers_share_one_parameterised_treatment;
    commit=5bdbd59f32e078187c9adf5bb3a507affd84852b]
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

from petta import Atom, Expr, Gnd, MeTTa, S, Sym, Var, encode, val
from petta import integrate as pi
from petta.convert import build, project, register_type, unregister_type
from petta.ops import annotation_atom_for, type_atoms_for


def test_the_four_metatypes_stay_distinct_across_the_seam():
    """Prove Atom, Sym, Var, Expr, and Gnd map to five distinct MeTTa metatype symbols."""
    expected = {
        Atom: "Atom",
        Sym: "Symbol",
        Var: "Variable",
        Expr: "Expression",
        Gnd: "Grounded",
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
        assert isinstance(projected.atom, Expr)
        assert build(projected.atom, annotation) == value

    def container_probe(
        fixed: tuple[int, str],  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        sequence: list[int],  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        mapping: dict[str, int],  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        members: set[int],
    ) -> set[int]:
        return members

    metta.register_op(container_probe)
    claims = {
        str(atom)
        for atom in metta.atoms()
        if isinstance(atom, Expr)
        and atom.head == Sym("annotation")
        and atom.args[0] == Sym("container_probe")
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
        assert projected.atom == Sym(symbol)
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
    assert projected.atom == Expr([Sym("Config"), Gnd(3), Gnd("fast")])
    assert type_atoms_for(Config) == [Sym("Config")]
    assert "(: Config (-> Number String Config))" in set(
        map(str, projected.declarations)
    )
    assert build(projected.atom, Config) == value

    def echo_config(config: Config) -> Config:
        return config

    metta.register_op(echo_config)
    assert metta.eval(Expr([S.echo_config, projected.atom])) == [projected.atom]
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

    metta.register_op(overloaded)
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

    metta.register_op(advanced)
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

    metta.register_op(convert_units)
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

    metta.register_op(current_space, name="annotated-engine")
    ((answer,),) = metta.run("!(annotated-engine)")
    assert isinstance(answer, Gnd)
    assert isinstance(answer.value, MeTTa)
    assert answer.value.space_name == metta.space_name


def test_dunder_metta_is_read_off_the_class_not_the_instance():
    """Prove projection reads __metta__ off the class, so instance hooks and properties never run."""
    looked_up: list[str] = []

    class Proxy:
        def __getattr__(self, name):
            looked_up.append(name)
            return lambda: S.wrong

    proxy = Proxy()
    assert project(proxy).atom == val(proxy)
    assert encode(proxy) == val(proxy)
    assert looked_up == []

    class Tagged:
        def __metta__(self):
            return S.tagged

    assert project(Tagged()).atom == S.tagged
    assert encode(Tagged()) == S.tagged

    class PropertyTrap:
        @property
        def __metta__(self):
            looked_up.append("property")
            return S.wrong

    trapped = PropertyTrap()
    assert project(trapped).atom == val(trapped)
    assert encode(trapped) == val(trapped)
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

    sequence = BareSequence([Expr([S.item, Gnd(1)])])
    sequence_atom = project(sequence).atom
    assert build(sequence_atom, BareSequence) == sequence
    assert build(project([1, 2], Sequence[int]).atom, Sequence[int]) == [1, 2]

    payload = bytearray(b"abc")
    buffer_atom = project(payload).atom
    assert isinstance(buffer_atom, Expr) and buffer_atom.head == S.Buffer
    metadata = {child.head: child.args for child in buffer_atom.args[1:]}
    assert metadata == {
        S.shape: (Gnd(3),),
        S.format: (Gnd("B"),),
        S.itemsize: (Gnd(1),),
        S.ndim: (Gnd(1),),
        S.strides: (Gnd(1),),
        S.readonly: (Gnd(False),),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        S["c-contiguous"]: (Gnd(True),),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
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
        metta.register_op(kwargs)

    class Choice(Enum):
        first = 1

    def choose() -> Choice:
        return Choice.first

    metta.register_op(choose)
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
