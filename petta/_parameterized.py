"""Purpose: define the one parameterized-container table used to project
Python annotations, project matching values, and rebuild those values.
Guarantees:
  - tuple, list, dict, and set hooks receive the full parameterized type on
    every route [tested: test_the_four_containers_share_one_parameterised_treatment;
    commit=1b1aa89517584ce3b4abe1024b7a9f85e2c1263d]
  - TypedDict fields drive both its constructor declaration and its value
    image, with optional or mismatched keys refused before data is lost
    [tested: test_a_typed_dict_annotation_agrees_with_its_value;
    commit=1b1aa89517584ce3b4abe1024b7a9f85e2c1263d]
Decides:
  - container values use MeTTa's one bare-expression image; mappings contain
    ``(entry key value)`` children and sets are ordered by the atom order for
    reproducibility. The distinct Python origin and parameters remain in the
    annotation claim and choose reconstruction on the return route
"""

from __future__ import annotations

import functools
import typing
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .atoms import Atom, Expr, S, order_key


@dataclass(frozen=True)
class ParameterizedHook:
    """The three directions owned by one full-annotation hook factory."""

    type_atom: Callable[[Any, Callable[[Any], list[Atom]]], Atom]
    annotation_atom: Callable[[Any, Callable[[Any], Atom]], Atom]
    project: Callable[[Any, Any, Callable[[Any, Any], Any]], Any]
    build: Callable[[Expr, Any, Callable[[Atom, Any], Any]], Any]
    declarations: Callable[[Any, Callable[[Any], list[Atom]]], tuple[Expr, ...]] | None = None


def _arguments(annotation: Any) -> tuple[Any, ...]:
    return typing.get_args(annotation)


def _container_type(annotation: Any, recurse: Callable[[Any], list[Atom]]) -> Atom:
    origin = typing.get_origin(annotation)
    arguments = _arguments(annotation)
    if origin is tuple and arguments and arguments[-1] is not Ellipsis:
        return Expr([recurse(argument)[0] for argument in arguments])
    return S.Expression


def _container_annotation(
    annotation: Any, recurse: Callable[[Any], Atom]
) -> Atom:
    origin = typing.get_origin(annotation)
    arguments = _arguments(annotation)
    children = [S[origin.__name__]]
    for argument in arguments:
        if argument is Ellipsis:
            children.append(S["..."])
        else:
            children.append(recurse(argument))
    return Expr(children)


def _sequence_project(value: Any, annotation: Any, recurse: Callable) -> tuple:
    origin = typing.get_origin(annotation)
    arguments = _arguments(annotation)
    if origin is tuple and arguments and arguments[-1] is not Ellipsis:
        item_types = arguments
        if len(value) != len(item_types):
            raise TypeError(
                f"{annotation!r} requires {len(item_types)} item(s), "
                f"but the value carries {len(value)}"
            )
    else:
        item_type = arguments[0] if arguments else Any
        item_types = (item_type,) * len(value)
    parts = [
        recurse(item, item_type)
        for item, item_type in zip(value, item_types, strict=True)
    ]
    return Expr([part.atom for part in parts]), parts


def _mapping_project(value: dict, annotation: Any, recurse: Callable) -> tuple:
    padded = (*_arguments(annotation), Any, Any)
    key_type, value_type = padded[:2]
    pairs: list[Atom] = []
    parts: list[Any] = []
    for key, item in value.items():
        projected_key = recurse(key, key_type)
        projected_value = recurse(item, value_type)
        parts.extend((projected_key, projected_value))
        pairs.append(Expr([S.entry, projected_key.atom, projected_value.atom]))
    return Expr(pairs), parts


def _set_project(value: set, annotation: Any, recurse: Callable) -> tuple:
    element_type = _arguments(annotation)[0] if _arguments(annotation) else Any
    parts = [recurse(item, element_type) for item in value]
    atoms = sorted((part.atom for part in parts), key=order_key)
    return Expr(atoms), parts


def _sequence_build(atom: Expr, annotation: Any, recurse: Callable) -> Any:
    origin = typing.get_origin(annotation)
    arguments = _arguments(annotation)
    children = atom.children
    if origin is tuple and arguments and arguments[-1] is not Ellipsis:
        if len(children) != len(arguments):
            raise TypeError(
                f"{annotation!r} requires {len(arguments)} item(s), "
                f"but {atom} carries {len(children)}"
            )
        return tuple(
            recurse(child, item_type)
            for child, item_type in zip(children, arguments, strict=True)
        )
    element_type = arguments[0] if arguments else Any
    built = [recurse(child, element_type) for child in children]
    return tuple(built) if origin is tuple else built


def _mapping_build(atom: Expr, annotation: Any, recurse: Callable) -> dict:
    padded = (*_arguments(annotation), Any, Any)
    key_type, value_type = padded[:2]
    entries = atom.children
    result = {}
    for entry in entries:
        if not isinstance(entry, Expr) or entry.head != S.entry or len(entry.args) != 2:
            raise TypeError(f"{atom} is not a dict of (entry key value) expressions")
        key, value = entry.args
        result[recurse(key, key_type)] = recurse(value, value_type)
    return result


def _set_build(atom: Expr, annotation: Any, recurse: Callable) -> set:
    element_type = _arguments(annotation)[0] if _arguments(annotation) else Any
    return {recurse(child, element_type) for child in atom.children}


def _typed_dict_fields(annotation: Any) -> tuple[tuple[str, Any], ...]:
    optional: frozenset[str] = getattr(
        annotation, "__optional_keys__", frozenset()
    )
    if optional:
        names = ", ".join(sorted(optional))
        raise TypeError(
            f"{annotation.__name__} has optional TypedDict field(s) {names}; "
            "the constructor image cannot distinguish absent from omitted"
        )
    hints = typing.get_type_hints(annotation, include_extras=True)
    return tuple(hints.items())


def _typed_dict_type(annotation: Any, _recurse: Callable) -> Atom:
    return S[annotation.__name__]


def _typed_dict_annotation(annotation: Any, recurse: Callable[[Any], Atom]) -> Atom:
    fields = [Expr([S.field, S[name], recurse(kind)]) for name, kind in _typed_dict_fields(annotation)]
    return Expr([S.TypedDict, S[annotation.__name__], *fields])


def _typed_dict_project(value: Any, annotation: Any, recurse: Callable) -> tuple:
    fields = _typed_dict_fields(annotation)
    names = tuple(name for name, _kind in fields)
    if not isinstance(value, dict):
        raise TypeError(f"{annotation.__name__} requires a dict value")
    missing = sorted(set(names) - value.keys())
    extra = sorted(value.keys() - set(names))
    if missing or extra:
        raise TypeError(
            f"{annotation.__name__} keys disagree with its annotation "
            f"(missing={missing}, extra={extra})"
        )
    parts = [recurse(value[name], kind) for name, kind in fields]
    return Expr([S[annotation.__name__], *(part.atom for part in parts)]), parts


def _typed_dict_build(atom: Expr, annotation: Any, recurse: Callable) -> dict:
    fields = _typed_dict_fields(annotation)
    if atom.head != S[annotation.__name__]:
        raise TypeError(
            f"expected a ({annotation.__name__} ...) image, got {atom}"
        )
    if len(atom.args) != len(fields):
        raise TypeError(
            f"{annotation.__name__} requires {len(fields)} field(s), "
            f"but {atom} carries {len(atom.args)}"
        )
    return {
        name: recurse(child, kind)
        for child, (name, kind) in zip(atom.args, fields, strict=True)
    }


def _typed_dict_declarations(annotation: Any, recurse: Callable) -> tuple[Expr, ...]:
    fields = _typed_dict_fields(annotation)
    field_types = [recurse(kind)[0] for _name, kind in fields]
    name = S[annotation.__name__]
    return (Expr([S[":"], name, Expr([S["->"], *field_types, name])]),)


TYPED_DICT_HOOK = ParameterizedHook(
    _typed_dict_type,
    _typed_dict_annotation,
    _typed_dict_project,
    _typed_dict_build,
    _typed_dict_declarations,
)


CONTAINER_HOOKS: dict[type, ParameterizedHook] = {
    tuple: ParameterizedHook(
        _container_type, _container_annotation, _sequence_project, _sequence_build
    ),
    list: ParameterizedHook(
        _container_type, _container_annotation, _sequence_project, _sequence_build
    ),
    dict: ParameterizedHook(
        _container_type, _container_annotation, _mapping_project, _mapping_build
    ),
    set: ParameterizedHook(
        _container_type, _container_annotation, _set_project, _set_build
    ),
}


@functools.cache
def hook_for(annotation: Any) -> ParameterizedHook | None:
    """Return the specialised hook selected by the complete annotation."""
    if typing.is_typeddict(annotation):
        return TYPED_DICT_HOOK
    return CONTAINER_HOOKS.get(typing.get_origin(annotation))


def runtime_annotation(value: Any) -> Any | None:
    """The least-specific full annotation for a supported runtime container."""
    origin = type(value)
    if origin not in CONTAINER_HOOKS:
        return None
    if origin is dict:
        return dict[Any, Any]
    if origin is tuple:
        return tuple[Any, ...]
    return origin[Any]
