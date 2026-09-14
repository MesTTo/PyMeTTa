"""Purpose: project field values and their native read and write contracts.

Guarantees:
  - arguments retain their Python container identity until assignment selects
    the field's storage representation [tested:
    test_constructor_arguments_are_borrowed_until_field_assignment; commit=WORKTREE]
  - generated query outputs evaluate the lookup before returning stored atom
    data [tested: test_generated_syntax_field_queries_return_the_stored_value,
    test_generated_class_variable_queries_return_the_stored_atom; commit=397a0df18bea23dee8774a721c2bdcd7dfc38c5e]
  - container aliases survive reads and replacement; native expressions are
    adopted once on writing [tested: test_container_fields_keep_python_aliases,
    test_native_container_fields_are_adopted_once; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - Annotated constraints govern both native and retained host alternatives
    [tested: test_container_refinements_guard_native_and_host_field_writes;
    commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
Decides:
  - adoption uses the existing Grounded host boundary and an oracleIO operation;
    whole-field replacement follows engine rollback, while Python container
    mutations follow the host-effect contract [tested:
    test_field_replacement_rolls_back_but_external_mutation_is_a_host_effect;
    commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
"""

from __future__ import annotations

import types
import typing
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, _expr
from metta._catalog.annotations import runtime_type_atoms, type_atoms_for
from metta._catalog.build import build
from metta._catalog.call_values import argument
from metta._catalog.containers import hook_for
from metta._catalog.project import project
from metta._catalog.refinements import refinement_atom
from metta.vocabularies import EffectClass


def container_annotations(annotation: Any) -> tuple[Any, ...]:
    """Read container alternatives through Annotated and union wrappers."""
    origin = typing.get_origin(annotation)
    if origin in (typing.Annotated, typing.Required, typing.NotRequired):
        return container_annotations(typing.get_args(annotation)[0])
    if isinstance(annotation, typing.TypeVar):
        choices = annotation.__constraints__ or (annotation.__bound__ or Any,)
        return tuple(candidate for choice in choices for candidate in container_annotations(choice))
    if annotation in (Any, object):
        return (Any,)
    if origin in (typing.Union, types.UnionType):
        return tuple(candidate for member in typing.get_args(annotation)
                     for candidate in container_annotations(member))
    return (annotation,) if hook_for(annotation) is not None else ()


def type_atoms(annotation: Any, *, retained: bool) -> list[Atom]:
    """Describe the native expression and retained host container at this field."""
    if typing.get_origin(annotation) is typing.Annotated:
        base, *metadata = typing.get_args(annotation)
        alternatives = type_atoms(base, retained=retained)
        refinements = [atom for item in metadata if (atom := refinement_atom(item)) is not None]
        return [_expr(S.Annotated, atom, *refinements) for atom in alternatives] if refinements else alternatives
    unique = list(dict.fromkeys(runtime_type_atoms(annotation) if retained else type_atoms_for(annotation)))
    return [_expr(S["|"], *unique)] if len(unique) > 1 else unique


def query_result_type(type_: Atom) -> Atom:
    """Allow a generated query to run before returning an unconstrained atom."""
    # Atom quotes an equation's body; Undefined admits the same values after
    # evaluating that body. Field storage and writer input types stay intact.
    return S["%Undefined%"] if type_ == S.Atom else type_


def encode(plan: Any, value: Any) -> Atom:
    # Copying a property loses mutation and aliasing. Retain the host reference:
    # https://github.com/pybind/pybind11/blob/f5fbe867d2d26e4a0a9177a51f6e568868ad3dc8/docs/advanced/cast/stl.rst#L106-L159
    return argument(value) if plan.grain != "value" else project(value).atom


def adopted(plan: Any, field: Any, value: Atom) -> Atom:
    """Choose the field's storage image once, when its value is assigned."""
    choices = container_annotations(field.annotation)
    if not choices or (plan.grain != "value" and all(choice is Any for choice in choices)):
        return value
    if plan.field_adopter is None:
        name = f"_{plan.name}-adopt-field"

        def adopt(name_atom: Any, atom: Any) -> Any:
            if plan.grain == "value":
                return project(atom.value).atom if isinstance(atom, Grounded) else atom
            if not isinstance(atom, Expression):
                return atom
            choices = tuple(choice for choice in container_annotations(plan.field(name_atom.value).annotation) if choice is not Any)
            for index, annotation in enumerate(choices):
                try:
                    return Grounded(build(atom, annotation))
                except TypeError:
                    if index == len(choices) - 1:
                        raise
            msg = "a field adopter requires a container annotation"
            raise AssertionError(msg)

        plan.operation(adopt, name=name, effect=EffectClass.oracleIO, arities=[2],
                       declarations=[_expr(S.arguments, Symbol(name), S.atoms)])
        plan.field_adopter = Symbol(name)
        plan.space.add(_expr(S.internal, plan.field_adopter))
    return _expr(S.evalc, _expr(plan.field_adopter, Grounded(field.name), value), Symbol(plan.space.name))
