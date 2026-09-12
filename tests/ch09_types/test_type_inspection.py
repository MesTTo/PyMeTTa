"""Purpose: asking for a type is a question about an expression, not a reason
to run it.
Guarantees:
  - get-type and get-type-space leave their argument unevaluated, so an
    effectful operation named inside one does not fire [tested
    test_get_type_does_not_run_its_arguments_effects]
  - get-type answers a function application from its DECLARATION, which is
    what the arbiter answers [tested
    test_get_type_of_an_application_answers_the_declared_return_type]
  - an expression no arrow types reads element-wise, and the tuple it reads is
    %Undefined% as soon as one member's type is [tested
    test_one_untyped_component_makes_the_whole_expressions_type_undefined]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import dataclasses
import enum
from typing import NamedTuple

from metta import MeTTa, S, V, ground, typed


def _counting_engine():
    """An engine whose (metta-effectful) op records every call it gets."""
    m = MeTTa().self
    fired: list[int] = []

    def effectful():
        fired.append(1)
        return 1

    m.op(effectful, name="metta-effectful", effect="writesState")
    return m, fired


def test_get_type_does_not_run_its_arguments_effects():
    """Measured before this: the op FIRED, the counter went 0 to 1, and the
    answer was Number, the type of the value it returned. Every linter walk
    and every REPL inspection was invisibly effectful.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m, fired = _counting_engine()
    answer = m.run("!(get-type (metta-effectful))")
    assert fired == [], f"get-type ran its argument {len(fired)} time(s)"
    # Number was the old answer, and it could only come from the value the
    # op returned; nothing declares the expression itself.
    answers = [str(a) for group in answer for a in group]
    assert "Number" not in answers, answers

    m, fired = _counting_engine()
    m.run("!(get-type-space &self (metta-effectful))")
    assert fired == [], "get-type-space ran its argument"


def test_get_type_of_an_application_answers_the_declared_return_type():
    """The answer comes from the declaration, so it is the same whether or not
    the body would reduce; `[Atom]` was recorded from both an earlier reference
    interpreter and hyperon 0.2.10.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa().self
    m.run("(: literal-return (-> Number Atom))")
    m.run("(= (literal-return $x) (+ $x 1))")
    assert [str(a) for g in m.run("!(get-type (literal-return 2))") for a in g] == ["Atom"]
    # A value still types as itself, and an undeclared head is still undefined.
    assert [str(a) for g in m.run("!(get-type 1)") for a in g] == ["Number"]
    # A builtin application still types by its arrow rather than element-wise,
    # which is the same route that answers ErrorType for (Error Foo Boo).
    assert [str(a) for g in m.run("!(get-type (+ 1 2))") for a in g] == ["Number"]
    assert [str(a) for g in m.run("!(get-type (Error Foo Boo))") for a in g] == ["ErrorType"]


def test_one_untyped_component_makes_the_whole_expressions_type_undefined():
    """An expression no arrow types is read element-wise, and the tuple it
    reads is %Undefined% as soon as one member's type is: nothing is known
    about a tuple one of whose components is unknown, so reporting the shape
    while a hole sits inside it claims more than was derived.

    Measured 2026-08-19 on hyperon 0.2.10 and on an earlier reference
    interpreter, byte-identical across both. Before this,
    `!(get-type (aa))` answered `(%Undefined%)`, a one-element tuple.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa().self
    m.run("(: typed-sym Number)")

    def answer(query):
        return [str(a) for g in m.run("!" + query) for a in g]

    # Every member typed: the tuple stands, and nests.
    assert answer("(get-type (typed-sym))") == ["(Number)"]
    assert answer("(get-type (typed-sym typed-sym))") == ["(Number Number)"]
    assert answer("(get-type (1))") == ["(Number)"]
    assert answer("(get-type (typed-sym (typed-sym typed-sym)))") == [
        "(Number (Number Number))"
    ]

    # One member undeclared, in any position, and nothing is known.
    for hole in (
        "(get-type (aa))",
        "(get-type (aa bb))",
        "(get-type (typed-sym aa))",
        "(get-type (aa typed-sym))",
    ):
        assert answer(hole) == ["%Undefined%"], hole

    # The collapse is recursive because the walk is bottom-up: the inner
    # tuple is %Undefined% first, which makes the outer one %Undefined% too.
    assert answer("(get-type (typed-sym (typed-sym aa)))") == ["%Undefined%"]

    # A call whose head has equations but no declaration is the same shape,
    # and it is the one a program hits most.
    m.run("(= (nullary) 42)")
    assert answer("(get-type (nullary))") == ["%Undefined%"]


def test_pythons_type_in_a_compiled_body_is_the_metatype_accessor(metta):
    """One question, one word on both sides of the decorator.

    Outside a compiled body `type(atom)` answers the atom's Python class, and
    the four classes are named exactly as the four metatype symbols. Inside
    one, the values ARE engine values, so the same word lowers to
    `get-metatype` rather than running Python's `type` over the crossing.
    """
    m = metta._new_space()

    @m.define
    def kind(a):
        """Every atom's metatype."""
        return type(a)

    assert str(kind.body) == "(get-metatype $a)"
    for atom in (S.foo(1, 2), ground(1), V.x, S.a):
        assert list(kind(atom)) == [S[type(atom).__name__]]


def test_the_three_argument_type_stays_a_host_island(metta):
    """Python's class constructor is a different function of the same name."""
    m = metta._new_space()

    @m.define
    def make_class():
        """Build a Python class at application time."""
        return type("Made", (), {})

    assert "get-metatype" not in str(make_class.body)
    assert "HostIsland" in str(make_class.body)


def test_a_declared_class_hierarchy_writes_its_subtype_edges(metta):
    """Python's class hierarchy IS a subtype relation, so declaring says it.

    Only DECLARED classes count as supertypes, so a base the space was never
    told about names nothing; `:<` widening is transitive, so one edge per
    direct base to its nearest declared ancestor is the whole chain.
    """
    m = metta._new_space()

    @dataclasses.dataclass
    class Animal:
        """A declared base."""

        name: str

    @dataclasses.dataclass
    class Dog(Animal):
        """Its subclass."""

    @dataclasses.dataclass
    class Puppy(Dog):
        """And one more level."""

    for cls in (Animal, Dog, Puppy):
        m.define(cls)
    edges = sorted(str(atom) for atom in m.atoms() if str(atom).startswith("(:< "))
    assert edges == ["(:< Dog Animal)", "(:< Puppy Dog)"]

    m += typed(S.Rex, S.Dog)
    assert list(m.fn.get_type(S.Rex)) == [S.Dog, S.Animal]
    m += typed(S.Fido, S.Puppy)
    assert list(m.fn.get_type(S.Fido)) == [S.Puppy, S.Dog, S.Animal]


def test_a_subtype_edge_waits_for_the_base_and_skips_an_undeclared_one(metta):
    """The set is recomputed from what the space knows, so order does not decide.

    A base the program never declared is not a MeTTa type here, which is what
    keeps `object`, a NamedTuple's `tuple` and an enum's `Enum` out.
    """
    m = metta._new_space()

    @dataclasses.dataclass
    class Vehicle:
        """Declared second."""

        wheels: int

    @dataclasses.dataclass
    class Car(Vehicle):
        """Declared first."""

    m.define(Car)
    assert [atom for atom in m.atoms() if str(atom).startswith("(:< ")] == []
    m.define(Vehicle)
    assert [str(atom) for atom in m.atoms() if str(atom).startswith("(:< ")] == [
        "(:< Car Vehicle)"
    ]

    other = metta._new_space()

    class Point(NamedTuple):
        """Its tuple base is nobody's declaration."""

        x: float
        y: float

    class Colour(enum.Enum):
        """And an enum's Enum base likewise."""

        red = 1

    other.define(Point)
    other.define(Colour)
    assert [atom for atom in other.atoms() if str(atom).startswith("(:< ")] == []


def test_multiple_inheritance_answers_one_edge_per_direct_base(metta):
    """Two declared bases are two edges, and get-type reads all three types."""
    m = metta._new_space()

    @dataclasses.dataclass
    class Walks:
        """One base."""

        legs: int

    @dataclasses.dataclass
    class Swims:
        """The other."""

        fins: int

    @dataclasses.dataclass
    class Otter(Walks, Swims):
        """Both."""

    for cls in (Walks, Swims, Otter):
        m.define(cls)
    assert sorted(str(atom) for atom in m.atoms() if str(atom).startswith("(:< ")) == [
        "(:< Otter Swims)",
        "(:< Otter Walks)",
    ]
    m += typed(S.Ollie, S.Otter)
    assert list(m.fn.get_type(S.Ollie)) == [S.Otter, S.Walks, S.Swims]


def test_declaring_a_subclass_gives_it_its_own_type_name(metta):
    """A declared class is a type THERE, so it answers its own name.

    ensure_registered walks the MRO, so a subclass adding nothing projected
    through its base's entry: declaring it restated the BASE's declaration and
    left no subtype at all.
    """
    m = metta._new_space()

    @dataclasses.dataclass
    class Base:
        """The registered base."""

        value: int

    @dataclasses.dataclass
    class Derived(Base):
        """Adds nothing, and is still its own type."""

    m.define(Base)
    m.define(Derived)
    from metta._declare.classes import declaration

    declared = {str(atom) for cls in (Base, Derived) for atom in declaration(cls).space.atoms()}
    assert "(: Derived (-> Atom Derived))" in declared
    assert "(: Base (-> Atom Base))" in declared
    assert "(: make-Derived (-> Number Derived))" in declared
    assert "(: make-Base (-> Number Base))" in declared
    assert list(m.fn.get_type(Derived(3))) == [S.Derived, S.Base]
