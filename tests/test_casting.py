"""Purpose: runtime typecasting. A cast answers the value narrowed when
the engine's own typed-call acceptance admits it, raises CastError
naming the actual types otherwise, reads ':' declarations
space-relatively, spells Python types the way get-type does (bool
before int), passes the translator's unchecked targets unchecked,
reaches metatypes through the same fallback a typed call compiles, and
ducks through protocol types registered on the integrate surface.
Guarantees:
  - ``atom.cast(type_)`` uses the ambient space and agrees with the explicit
    ``space.cast(atom, type_)`` spelling [tested:
    test_atom_cast_delegates_to_the_ambient_space;
    commit=162214d7a703e9108dd2422f4f18f3b9c007d367]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import Grounded, S, V, integrate
from metta.casting import CastError, cast


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def test_ground_values_cast_to_their_own_types(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.cast(3, int) == 3
    assert m.cast(3, "Number") == 3
    assert m.cast(3.5, float) == 3.5
    assert m.cast("s", str) == "s"
    assert m.cast(True, bool) is True  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch


def test_bool_is_bool_before_int_is_number(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(CastError):
        m.cast(True, int)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch


def test_declared_symbols_cast_by_their_declarations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(: Ann Person)")
    assert m.cast(S.Ann, "Person") is S.Ann
    with pytest.raises(CastError) as caught:
        m.cast(S.Ann, "Robot")
    assert "Person" in str(caught.value)


def test_metatype_targets_reach_through_the_fallback(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.cast(S.mystery, "Symbol") is S.mystery
    with pytest.raises(CastError):
        m.cast(S.mystery, "Person")


def test_arrow_typed_expressions_cast_structurally(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(: Cons (-> Number (List Number) (List Number))) (: Nil (List Number))")
    tail = S.Cons(1, S.Nil)
    assert m.cast(tail, "(List Number)") is tail
    assert m.cast(tail, S.List(V.t)) is tail
    with pytest.raises(CastError):
        m.cast(tail, "(List String)")


def test_unchecked_targets_pass_unchecked(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.cast(S.anything, "Atom") is S.anything
    assert m.cast(Grounded(3), "%Undefined%") == 3


def test_protocol_types_duck_through_the_type_system(m, metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    integrate.register_object_type(lambda x: hasattr(x, "quack"), "Ducky")

    class Quacks:
        quack = "yes"

    class Silent:
        pass

    duck = Quacks()
    assert m.cast(duck, "Ducky") is duck
    assert m.cast(duck, Quacks) is duck
    with pytest.raises(CastError):
        m.cast(Silent(), "Ducky")


def test_declarations_are_space_relative(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as a, metta._new_space() as b:
        a.run("(: Bob Person)")
        assert a.cast(S.Bob, "Person") is S.Bob
        with pytest.raises(CastError):
            b.cast(S.Bob, "Person")


def test_atom_cast_delegates_to_the_ambient_space(metta):
    """The method keeps cast admission relative to the active space."""
    with metta._new_space() as declared, metta._new_space() as undeclared:
        declared.run("(: Bob Person)")
        with declared:
            assert S.Bob.cast("Person") is declared.cast(S.Bob, "Person")
            assert declared.cast("Atom") is declared
        with undeclared, pytest.raises(CastError):
            S.Bob.cast("Person")


def test_the_module_function_takes_the_space_first(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert cast(m, 3, "Number") == 3
    assert issubclass(CastError, TypeError)


def test_parameterized_generic_is_not_accepted_as_a_cast_class(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="cast target must be"):
        m.cast([1, 2, 3], list[int])


def test_ground_atoms_narrow_to_their_python_values(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.cast(Grounded(3), "Number") == 3
    assert isinstance(m.cast(Grounded(3), int), int)


try:
    from hypothesis import HealthCheck, given, settings
except ModuleNotFoundError:
    pass
else:
    from metta.testing import expressions

    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(expressions(max_leaves=6, ground=True))
    def test_generated_atoms_cast_to_atom_and_refuse_the_absurd(metta, atom):
        """Atom admits everything unchecked; a type name nothing
        declares refuses everything, loudly and precisely.
        """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
        with metta._new_space() as space:
            assert space.cast(atom, "Atom") is not None
            with pytest.raises(CastError) as caught:
                space.cast(atom, "Absurd987")
            assert "does not admit" in str(caught.value)
