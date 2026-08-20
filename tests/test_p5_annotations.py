"""Purpose: pin Phase 5's Python annotation and conversion seam."""

from enum import Flag, IntEnum, StrEnum, auto
from typing import TypedDict

from petta import Atom, Expr, Gnd, S, Sym, Var
from petta.convert import build, project
from petta.ops import annotation_atom_for, type_atoms_for


def test_the_four_metatypes_stay_distinct_across_the_seam():
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
        fixed: tuple[int, str],
        sequence: list[int],
        mapping: dict[str, int],
        members: set[int],
    ) -> set[int]:
        return members

    metta.register_op(container_probe)
    claims = {
        str(atom)
        for atom in metta.atoms()
        if isinstance(atom, Expr) and atom.head == Sym("annotation")
    }
    assert claims == {
        "(annotation container_probe (param 1 (tuple Number String)))",
        "(annotation container_probe (param 2 (list Number)))",
        "(annotation container_probe (param 3 (dict String Number)))",
        "(annotation container_probe (param 4 (set Number)))",
        "(annotation container_probe (return (set Number)))",
    }


def test_int_str_and_flag_enums_each_project_with_their_declarations():
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
