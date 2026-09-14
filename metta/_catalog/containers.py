"""Purpose: define the one parameterized-container table used to project
Python annotations, project matching values, and rebuild those values.
Guarantees:
  - tuple, list, dict, and set hooks receive the full parameterized type on
    every route [tested: test_the_four_containers_share_one_parameterised_treatment;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - TypedDict fields drive both its constructor declaration and its value
    image, with optional or mismatched keys refused before data is lost
    [tested: test_a_typed_dict_annotation_agrees_with_its_value;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - bare and abstract sequence, mapping, and set annotations select the same
    full-annotation hooks as their builtin concrete forms
    [tested: test_each_remaining_annotation_shape_refuses_or_carries;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - mapping hooks reconstruct native key/value rows through their structural
    inverse, refusing malformed rows and duplicate decoded keys [tested:
    test_mapping_spaces_follow_annotations_and_native_edits,
    test_mapping_images_refuse_keys_that_reconstruct_as_duplicates;
    commit=a8e3fc42306377adf7cae0a331f3d92fbf190304]
Decides:
  - structural container values use bare expressions; mappings contain
    ``(entry key value)`` children and sets are ordered by the atom order for
    reproducibility. The distinct Python origin and parameters remain in the
    annotation claim and choose reconstruction on the return route.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import functools
import typing
from collections import abc
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from metta._atoms.factories import Atom, Expression, S, _decode, order_key


@dataclass(frozen=True)
class ParameterizedHook:
    """Annotation, value images and inverses owned by one container kind."""

    type_atom: Callable[[Any, Callable[[Any], list[Atom]]], Atom]
    annotation_atom: Callable[[Any, Callable[[Any], Atom]], Atom]
    project: Callable[[Any, Any, Callable[[Any, Any], Any]], Any]
    build: Callable[[Expression, Any, Callable[[Atom, Any], Any]], Any]
    declarations: Callable[[Any, Callable[[Any], list[Atom]]], tuple[Expression, ...]] | None = None
    matches: Callable[[Expression, Any], bool] | None = None
    space_image: Callable[[list[Atom], Any], Expression] | None = None


def _arguments(annotation: Any) -> tuple[Any, ...]:
    return typing.get_args(annotation)


def _container_type(annotation: Any, recurse: Callable[[Any], list[Atom]]) -> Atom:
    origin = _container_origin(annotation)
    arguments = _arguments(annotation)
    if origin is tuple and arguments and arguments[-1] is not Ellipsis:
        return Expression([recurse(argument)[0] for argument in arguments])
    return S["Expression"]


def _container_annotation(
    annotation: Any, recurse: Callable[[Any], Atom]
) -> Atom:
    origin = _container_origin(annotation)
    arguments = _arguments(annotation)
    #Annotated, because the exact bracket door answers a Symbol and the
    #recursion below appends an Atom; inference used to widen this list
    #only because the first element was untyped.
    children: list[Atom] = [S[origin.__name__]]
    for argument in arguments:
        if argument is Ellipsis:
            children.append(S["..."])
        else:
            children.append(recurse(argument))
    return Expression(children)


def _sequence_project(value: Any, annotation: Any, recurse: Callable) -> tuple:
    origin = _container_origin(annotation)
    arguments = _arguments(annotation)
    if origin is tuple and arguments and arguments[-1] is not Ellipsis:
        item_types = arguments
        if len(value) != len(item_types):
            msg = (
                f"{annotation!r} requires {len(item_types)} item(s), "
                f"but the value carries {len(value)}"
            )
            raise TypeError(msg)
    else:
        item_type = arguments[0] if arguments else Any
        item_types = (item_type,) * len(value)
    parts = [
        recurse(item, item_type)
        for item, item_type in zip(value, item_types, strict=True)
    ]
    return Expression([part.atom for part in parts]), parts


def _mapping_project(value: dict, annotation: Any, recurse: Callable) -> tuple:
    padded = (*_arguments(annotation), Any, Any)
    key_type, value_type = padded[:2]
    pairs: list[Atom] = []
    parts: list[Any] = []
    for key, item in value.items():
        projected_key = recurse(key, key_type)
        projected_value = recurse(item, value_type)
        parts.extend((projected_key, projected_value))
        pairs.append(Expression([S.entry, projected_key.atom, projected_value.atom]))
    return Expression(pairs), parts


def _set_project(value: set, annotation: Any, recurse: Callable) -> tuple:
    element_type = _arguments(annotation)[0] if _arguments(annotation) else Any
    parts = [recurse(item, element_type) for item in value]
    atoms = sorted((part.atom for part in parts), key=order_key)
    return Expression(atoms), parts


def _sequence_build(atom: Expression, annotation: Any, recurse: Callable) -> Any:
    origin = _container_origin(annotation)
    arguments = _arguments(annotation)
    children = atom.children
    if origin is tuple and arguments and arguments[-1] is not Ellipsis:
        if len(children) != len(arguments):
            msg = (
                f"{annotation!r} requires {len(arguments)} item(s), "
                f"but {atom} carries {len(children)}"
            )
            raise TypeError(msg)
        return tuple(
            recurse(child, item_type)
            for child, item_type in zip(children, arguments, strict=True)
        )
    element_type = arguments[0] if arguments else Any
    built = [recurse(child, element_type) for child in children]
    return tuple(built) if origin is tuple else built


def _mapping_build(atom: Expression, annotation: Any, recurse: Callable) -> dict:
    padded = (*_arguments(annotation), Any, Any)
    key_type, value_type = padded[:2]
    entries = atom.children
    result: dict[Any, Any] = {}
    for entry in entries:
        if not isinstance(entry, Expression) or entry.head != S.entry or len(entry.args) != 2:
            msg = f"{atom} is not a dict of (entry key value) expressions"
            raise TypeError(msg)
        key, value = entry.args
        decoded_key = recurse(key, key_type)
        _require_unique_key(result, decoded_key)
        result[decoded_key] = recurse(value, value_type)
    return result


def _require_unique_key(mapping: dict, key: Any) -> None:
    if key in mapping:
        msg = f"duplicate reconstructed mapping key: {key!r}"
        raise TypeError(msg)


def _mapping_matches(atom: Expression, _annotation: Any) -> bool:
    return all(isinstance(entry, Expression) and entry.head == S.entry
               for entry in atom.children)


def _mapping_row(row: Atom) -> tuple[Atom, Atom]:
    if not isinstance(row, Expression) or len(row.children) != 2:
        msg = f"{row} is not a key/value mapping row"
        raise TypeError(msg)
    key, value = row.children
    return key, value


def _mapping_space_image(rows: list[Atom], _annotation: Any) -> Expression:
    return Expression([Expression([S.entry, *_mapping_row(row)]) for row in rows])


def _set_build(atom: Expression, annotation: Any, recurse: Callable) -> set:
    element_type = _arguments(annotation)[0] if _arguments(annotation) else Any
    return {recurse(child, element_type) for child in atom.children}


def _typed_dict_fields(annotation: Any) -> tuple[tuple[str, Any], ...]:
    optional: frozenset[str] = getattr(
        annotation, "__optional_keys__", frozenset()
    )
    if optional:
        names = ", ".join(sorted(optional))
        msg = (
            f"{annotation.__name__} has optional TypedDict field(s) {names}; "
            "the constructor image cannot distinguish absent from omitted"
        )
        raise TypeError(msg)
    hints = typing.get_type_hints(annotation, include_extras=True)
    return tuple(hints.items())


def _typed_dict_type(annotation: Any, _recurse: Callable) -> Atom:
    return S[annotation.__name__]


def _typed_dict_annotation(annotation: Any, recurse: Callable[[Any], Atom]) -> Atom:
    fields = [Expression([S.field, S[name], recurse(kind)]) for name, kind in _typed_dict_fields(annotation)]
    return Expression([S.TypedDict, S[annotation.__name__], *fields])


def _typed_dict_project(value: Any, annotation: Any, recurse: Callable) -> tuple:
    fields = _typed_dict_fields(annotation)
    names = tuple(name for name, _kind in fields)
    if not isinstance(value, dict):
        msg = f"{annotation.__name__} requires a dict value"
        raise TypeError(msg)
    _require_typed_dict_keys(annotation, names, value)
    parts = [recurse(value[name], kind) for name, kind in fields]
    return Expression([S[annotation.__name__], *(part.atom for part in parts)]), parts


def _require_typed_dict_keys(annotation: Any, names: tuple[str, ...], value: dict) -> None:
    missing = sorted(set(names) - value.keys())
    extra = sorted(value.keys() - set(names), key=repr)
    if missing or extra:
        msg = (
            f"{annotation.__name__} keys disagree with its annotation "
            f"(missing={missing}, extra={extra})"
        )
        raise TypeError(msg)


def _typed_dict_matches(atom: Expression, annotation: Any) -> bool:
    return atom.head == S[annotation.__name__]


def _typed_dict_space_image(rows: list[Atom], annotation: Any) -> Expression:
    names = tuple(name for name, _kind in _typed_dict_fields(annotation))
    entries: dict[Any, Atom] = {}
    for row in rows:
        key, value = _mapping_row(row)
        decoded_key = _decode(key)
        _require_unique_key(entries, decoded_key)
        entries[decoded_key] = value
    _require_typed_dict_keys(annotation, names, entries)
    return Expression([S[annotation.__name__], *(entries[name] for name in names)])


def _typed_dict_build(atom: Expression, annotation: Any, recurse: Callable) -> dict:
    fields = _typed_dict_fields(annotation)
    if atom.head != S[annotation.__name__]:
        msg = f"expected a ({annotation.__name__} ...) image, got {atom}"
        raise TypeError(msg)
    if len(atom.args) != len(fields):
        msg = (
            f"{annotation.__name__} requires {len(fields)} field(s), "
            f"but {atom} carries {len(atom.args)}"
        )
        raise TypeError(msg)
    return {
        name: recurse(child, kind)
        for child, (name, kind) in zip(atom.args, fields, strict=True)
    }


def _typed_dict_declarations(annotation: Any, recurse: Callable) -> tuple[Expression, ...]:
    fields = _typed_dict_fields(annotation)
    field_types = [recurse(kind)[0] for _name, kind in fields]
    name = S[annotation.__name__]
    return (Expression([S[":"], name, Expression([S["->"], *field_types, name])]),)


TYPED_DICT_HOOK = ParameterizedHook(
    _typed_dict_type,
    _typed_dict_annotation,
    _typed_dict_project,
    _typed_dict_build,
    _typed_dict_declarations,
    matches=_typed_dict_matches,
    space_image=_typed_dict_space_image,
)


CONTAINER_HOOKS: dict[type, ParameterizedHook] = {
    tuple: ParameterizedHook(
        _container_type, _container_annotation, _sequence_project, _sequence_build
    ),
    list: ParameterizedHook(
        _container_type, _container_annotation, _sequence_project, _sequence_build
    ),
    dict: ParameterizedHook(
        _container_type, _container_annotation, _mapping_project, _mapping_build,
        matches=_mapping_matches, space_image=_mapping_space_image,
    ),
    set: ParameterizedHook(
        _container_type, _container_annotation, _set_project, _set_build
    ),
}


def _container_origin(annotation: Any) -> Any:
    return typing.get_origin(annotation) or annotation


def _container_hook(origin: Any) -> ParameterizedHook | None:
    direct = CONTAINER_HOOKS.get(origin)
    if direct is not None or not isinstance(origin, type):
        return direct
    if origin in (abc.Mapping, abc.MutableMapping):
        return CONTAINER_HOOKS[dict]
    if origin in (abc.Set, abc.MutableSet):
        return CONTAINER_HOOKS[set]
    if origin in (abc.Sequence, abc.MutableSequence):
        return CONTAINER_HOOKS[list]
    return None


@functools.cache
def hook_for(annotation: Any) -> ParameterizedHook | None:
    """Return the specialised hook selected by the complete annotation."""
    if typing.is_typeddict(annotation):
        return TYPED_DICT_HOOK
    return _container_hook(_container_origin(annotation))


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
