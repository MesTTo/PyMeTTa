"""Purpose: rebuild Python values from atoms using registrations and annotations.
Guarantees:
  - a concrete requested class remains build's static return type [tested
    test_target_type_overloads_preserve_the_requested_class]
  - registered projections round-trip without dropping fields [tested
    test_build_reverses_the_projection]
  - union selection follows the atom shape and surfaces a selected reverse's
    error [tested test_union_build_selects_by_shape_and_surfaces_reverse_errors]
  - a requested class never accepts another class's constructor spelling
    [tested test_type_name_collision_is_refused_and_build_honors_requested_class]
  - each supported container reconstructs through the same specialised hook
    that projected its full annotation
    [tested: test_the_four_containers_share_one_parameterised_treatment;
     commit=4b340e87ea282045d5bfa7c00a722353dd69a968]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import types
import typing
from collections import abc
from enum import Enum
from typing import Any, TypeVar, overload

from ._convert_registry import (
    _class_label,
    _default_registration,
    _is_plain_class,
    _lookup,
    _record_registration,
    _Registration,
    constructor_for,
    explicitly_registered,
)
from ._parameterized import hook_for as _parameterized_hook
from .atoms import Atom, Expr, Gnd, Sym, decode

_UNHANDLED = object()
_BuildT = TypeVar("_BuildT")


@overload
def build(atom: Atom, cls: type[_BuildT]) -> _BuildT: ...


@overload
def build(atom: Atom, cls: None = None) -> Any: ...


@overload
def build(atom: Atom, cls: Any) -> Any: ...


def build(atom: Atom, cls: Any = None) -> Any:
    """Rebuild the Python value an atom describes, optionally by annotation.

    An atom this cannot rebuild comes back unchanged, which is how every
    unhandled shape already behaved; cast() is the spelling that refuses.
    The sentinel is module-private and must never reach a caller, so it is
    translated here rather than at each of the branches that produce it.
    """
    rebuilt = (
        _build_annotated(atom, cls)
        if cls is not None and not _is_plain_class(cls)
        else _build_plain(atom, cls)
    )
    return atom if rebuilt is _UNHANDLED else rebuilt


def _build_plain(atom: Atom, cls: type | None) -> Any:
    if isinstance(atom, Gnd):
        return decode(atom)
    if isinstance(atom, Sym):
        return _build_symbol(atom, cls) if cls is not None else atom
    if isinstance(atom, Expr):
        rebuilt = _build_expression(atom, cls)
        if rebuilt is not _UNHANDLED:
            return rebuilt
        return _build_hook(atom, cls)
    return atom


def _build_symbol(atom: Sym, cls: type) -> Any:
    if issubclass(cls, Enum):
        return cls[atom.name]
    registration = _lookup(cls)
    if (
        registration is not None
        and registration.image == "symbol"
        and registration.from_atom is not None
    ):
        return registration.from_atom(atom.name)
    return _UNHANDLED


def _build_expression(atom: Expr, cls: type | None) -> Any:
    if not atom.children or not isinstance(atom.head, Sym):
        return _UNHANDLED
    resolved = _resolve_constructor(atom, cls)
    if resolved is None:
        return _UNHANDLED
    target_cls, registration = resolved
    return _rebuild_registered(atom, target_cls, registration)


def _build_hook(atom: Expr, cls: type | None) -> Any:
    if cls is None:
        return atom
    hook = getattr(cls, "__from_metta__", None)
    if hook is None:
        return atom
    return hook(*(build(child) for child in atom.args))


def _resolve_constructor(atom: Expr, cls: type | None) -> tuple[type, _Registration] | None:
    head = atom.head
    if not isinstance(head, Sym):
        return None
    resolved = constructor_for(head.name)
    if resolved is not None:
        _require_requested_owner(head, cls, resolved[0])
        return resolved
    return _resolve_default_constructor(head, cls)


def _resolve_default_constructor(head: Sym, cls: type | None) -> tuple[type, _Registration] | None:
    if cls is None:
        return None
    registration = _lookup(cls) or _default_registration(cls)
    if registration is None or registration.type_name != head.name:
        return None
    if not explicitly_registered(cls):
        _record_registration(cls, registration)
    return cls, registration


def _require_requested_owner(head: Sym, requested: type | None, owner: type) -> None:
    if requested is None or owner is requested:
        return
    raise TypeError(
        f"({head.name} ...) belongs to {_class_label(owner)}, "
        f"not {_class_label(requested)}; build() will not substitute a different "
        f"class with the same type name"
    )


def _rebuild_registered(atom: Expr, target_cls: type, registration: _Registration) -> Any:
    _require_complete_parts(atom, target_cls, registration)
    kinds = registration.field_types or tuple(None for _ in atom.args)
    parts = [build(child, kind) for child, kind in zip(atom.args, kinds, strict=True)]
    return _call_reverse(target_cls, registration, parts)


def _require_complete_parts(atom: Expr, target_cls: type, registration: _Registration) -> None:
    if registration.fields and len(atom.args) != len(registration.fields):
        raise TypeError(
            f"({registration.type_name} ...) carries {len(atom.args)} part(s); "
            f"{target_cls.__name__} has {len(registration.fields)} field(s). "
            f"Rebuilding would drop or invent values."
        )


def _call_reverse(target_cls: type, registration: _Registration, parts: list[Any]) -> Any:
    if registration.from_atom is not None:
        return registration.from_atom(*parts)
    hook = getattr(target_cls, "__from_metta__", None)
    if hook is None:
        raise TypeError(
            f"{target_cls.__name__} has no from_atom and no __from_metta__; "
            f"register the reverse to rebuild it"
        )
    return hook(*parts)


def _build_annotated(atom: Atom, annotation: Any) -> Any:
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _build_annotated(atom, typing.get_args(annotation)[0])
    if origin in (typing.Union, types.UnionType):
        return _build_union(atom, typing.get_args(annotation))
    hook = _parameterized_hook(annotation)
    if isinstance(atom, Expr) and hook is not None:
        return hook.build(atom, annotation, build)
    if isinstance(annotation, type):
        return build(atom, annotation)
    return build(atom)


def _build_union(atom: Atom, members: tuple[Any, ...]) -> Any:
    candidates = [
        member
        for member in members
        if member is not type(None) and _annotation_matches(atom, member)
    ]
    return build(atom, candidates[0]) if candidates else build(atom)


def _annotation_matches(atom: Atom, annotation: Any) -> bool:
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _annotation_matches(atom, typing.get_args(annotation)[0])
    if origin in (typing.Union, types.UnionType):
        return any(_annotation_matches(atom, member) for member in typing.get_args(annotation))
    if origin is not None:
        return _parameterized_matches(atom, origin)
    return _class_matches(atom, annotation)


def _parameterized_matches(atom: Atom, origin: Any) -> bool:
    if not isinstance(atom, Expr) or not isinstance(origin, type):
        return False
    return origin in (tuple, list) or issubclass(origin, abc.Sequence)


def _class_matches(atom: Atom, annotation: Any) -> bool:
    if not isinstance(annotation, type):
        return False
    if isinstance(atom, Gnd):
        return isinstance(decode(atom), annotation)
    if isinstance(atom, Sym):
        return _symbol_annotation_matches(atom, annotation)
    if isinstance(atom, Expr):
        return _expression_annotation_matches(atom, annotation)
    return False


def _symbol_annotation_matches(atom: Sym, annotation: type) -> bool:
    return issubclass(annotation, Enum) and atom.name in annotation.__members__


def _expression_annotation_matches(atom: Expr, annotation: type) -> bool:
    if not atom.children or not isinstance(atom.head, Sym):
        return False
    registration = _lookup(annotation) or _default_registration(annotation)
    return registration is not None and registration.type_name == atom.head.name


def _build_sequence(atom: Expr, origin: type, args: tuple[Any, ...]) -> Any:
    if origin is tuple:
        return _build_tuple(atom, args)
    if origin is list or issubclass(origin, abc.Sequence):
        element = args[0] if args else None
        return [build(child, element) for child in atom.children]
    return _UNHANDLED


def _build_tuple(atom: Expr, args: tuple[Any, ...]) -> tuple[Any, ...]:
    if args and args[-1] is Ellipsis:
        return _build_uniform_tuple(atom, args[0])
    if args and len(args) == len(atom.children):
        return _build_fixed_tuple(atom, args)
    return tuple(build(child) for child in atom.children)


def _build_uniform_tuple(atom: Expr, annotation: Any) -> tuple[Any, ...]:
    return tuple(build(child, annotation) for child in atom.children)


def _build_fixed_tuple(atom: Expr, annotations: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(
        build(child, annotation)
        for child, annotation in zip(atom.children, annotations, strict=True)
    )
