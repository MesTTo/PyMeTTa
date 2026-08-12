"""Purpose: the four-image translator: defaults on sight, registration in
the pytree shape, declarations, and the reverse rebuilding real objects.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

import pytest

from petta import S, V, Gnd, Sym, expr, val
from petta.convert import build, declarations, project, register_type


class Color(Enum):
    red = 1
    green = 2
    blue = 3


@dataclass
class Person:
    name: str
    age: int


class Point(NamedTuple):
    x: float
    y: float


def test_enum_projects_to_symbols_with_declarations():
    projected = project(Color.red)
    assert projected.atom == Sym("red")
    decls = set(map(str, projected.declarations))
    assert "(: Color Type)" in decls
    assert "(: red Color)" in decls and "(: blue Color)" in decls


def test_dataclass_projects_to_constructor_expression():
    projected = project(Person("Ada", 36))
    assert projected.atom == expr(S.Person, "Ada", 36)
    assert "(: Person (-> String Number Person))" in set(map(str, projected.declarations))


def test_namedtuple_projects_like_a_dataclass():
    assert project(Point(1.0, 2.0)).atom == expr(S.Point, 1.0, 2.0)


def test_nesting_is_the_pytree_rule():
    @dataclass
    class Team:
        lead: Person
        colour: Color

    projected = project(Team(Person("Ada", 36), Color.blue))
    assert projected.atom == expr(S.Team, expr(S.Person, "Ada", 36), S.blue)
    decls = set(map(str, projected.declarations))
    assert "(: Color Type)" in decls
    assert any(d.startswith("(: Team") for d in decls)


def test_unregistered_object_stays_a_handle():
    class Opaque:
        pass

    thing = Opaque()
    projected = project(thing)
    assert isinstance(projected.atom, Gnd)
    assert projected.atom.value is thing
    assert projected.declarations == ()


def test_build_reverses_the_projection():
    person = Person("Ada", 36)
    rebuilt = build(project(person).atom)
    assert isinstance(rebuilt, Person) and rebuilt == person


def test_build_rebuilds_enums_with_the_class():
    assert build(Sym("green"), Color) is Color.green


def test_registered_custom_type_round_trips():
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
    assert atom == expr(S.Interval, 1, 5)
    assert build(atom) == Interval(1, 5)


def test_metta_dunder_hooks_work_unregistered():
    class Tagged:
        def __init__(self, label):
            self.label = label

        def __metta__(self):
            return expr(S.Tagged, self.label)

        @classmethod
        def __from_metta__(cls, label):
            return cls(label)

    atom = project(Tagged("x")).atom
    assert atom == expr(S.Tagged, "x")
    rebuilt = build(atom, Tagged)
    assert isinstance(rebuilt, Tagged) and rebuilt.label == "x"


def test_declarations_without_an_instance():
    assert "(: Color Type)" in set(map(str, declarations(Color)))


def test_projected_facts_reason_in_the_engine(metta):
    space = metta.fresh_space()
    projected = project(Person("Ada", 36))
    space.add(*projected.declarations, projected.atom)
    space.add(project(Person("Bob", 41)).atom)
    rows = space.query(S.Person(V.name, V.age))
    assert {(str(r.name), int(r.age)) for r in rows} == {('"Ada"', 36), ('"Bob"', 41)}
    people = [build(a) for a in space.atoms() if str(a).startswith("(Person")]
    assert Person("Ada", 36) in people and Person("Bob", 41) in people


def test_grounded_and_container_projections():
    assert project(3).atom == Gnd(3)
    assert project([1, 2]).atom == expr(1, 2)
    assert isinstance(val({"a": 1}), Gnd)
