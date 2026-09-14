"""Purpose: rebuild Python values from atoms using registrations and annotations.
Guarantees:
  - recursive annotation conversion carries a native callable's lexical
    context through containers and record fields [tested:
    test_callable_conversion_keeps_nested_lexical_context; commit=ec999c898a35a79e88d4d9d3e7192abfe043f928]
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
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - buffer projections rebuild the exact carried exporter rather than copying
    or discarding its layout
    [tested: test_each_remaining_annotation_shape_refuses_or_carries;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a container annotation leaves unsupported symbols unchanged and unwraps
    grounded values without recursively retrying the same conversion [tested:
    test_container_build_handles_non_expression_atoms; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - type annotations reconstruct a declared class from its canonical constructor
    image and keep ordinary factories distinct [tested:
    test_constructor_image_is_distinct_from_an_ordinary_factory; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
  - mapping annotations read registered namespaces without declaring names
    or evaluating rows, retaining the caller's lexical context [tested:
    test_mapping_space_images_use_native_identity,
    test_mapping_space_conversion_preserves_nested_callable_context;
    commit=a8e3fc42306377adf7cae0a331f3d92fbf190304]
  - structural conversion does not start an engine and explicit spaces retain
    their runtime owner [tested: test_mapping_conversion_keeps_runtime_ownership;
    commit=a8e3fc42306377adf7cae0a331f3d92fbf190304]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import types
import typing
from collections import abc
from enum import Enum
from functools import partial
from typing import Any, overload

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, _atom_from_wire, _decode
from metta._atoms.registry import (
    _class_label,
    _default_registration,
    _is_plain_class,
    _lookup,
    _record_registration,
    _Registration,
    constructor_for,
    explicitly_registered,
)
from metta._catalog.call_values import rebuild as _callable_value
from metta._catalog.containers import ParameterizedHook
from metta._catalog.containers import hook_for as _parameterized_hook
from metta._lazy import lazy

_UNHANDLED = object()


@overload
def build[BuildT](atom: Atom, cls: type[BuildT], *, space: Any = None) -> BuildT: ...


@overload
def build(atom: Atom, cls: None = None, *, space: Any = None) -> Any: ...


@overload
def build(atom: Atom, cls: Any, *, space: Any = None) -> Any: ...


def build(atom: Atom, cls: Any = None, *, space: Any = None) -> Any:
    """Rebuild the Python value an atom describes, optionally by annotation.

    An atom this cannot rebuild comes back unchanged, which is how every
    unhandled shape already behaved; cast() is the spelling that refuses.
    The sentinel is module-private and must never reach a caller, so it is
    translated here rather than at each of the branches that produce it.
    """
    members = _annotation_members(cls)
    if len(members) > 1:
        return _build_union(atom, members, space)
    cls = members[0]
    callable_value = _build_callable(atom, cls, space)
    if callable_value is not None:
        return callable_value
    rebuilt = (
        _build_annotated(atom, cls, space)
        if cls is not None
        and (_parameterized_hook(cls) is not None or not _is_plain_class(cls))
        else _build_plain(atom, cls, space)
    )
    return atom if rebuilt is _UNHANDLED else rebuilt


def _build_callable(atom: Atom, annotation: Any, space: Any) -> Any:
    if annotation is type or typing.get_origin(annotation) is type:
        native = _callable_value(atom, Any, space)
        if native is not None:
            owner = lazy('metta._declare.classes').declaration(native.__signature__.return_annotation)
            if owner is not None and native.atom.alpha_eq(lazy('metta._declare.constructors').image(owner)):
                return owner.cls
        return None
    if typing.get_origin(annotation) is abc.Callable or annotation is abc.Callable or (
        annotation in (None, Any, object) and isinstance(atom, Expression) and (
            atom.head == S["|->"] or (atom.head == S.noeval and len(atom.args) == 1 and isinstance(atom.args[0], Expression) and atom.args[0].head == S["|->"])
        )
    ):
        return _callable_value(atom, annotation, space)
    return None


def _build_plain(atom: Atom, cls: type | None, space: Any = None) -> Any:
    if isinstance(atom, Grounded):
        return _decode(atom)
    if isinstance(atom, Symbol):
        return _build_symbol(atom, cls) if cls is not None else atom
    if isinstance(atom, Expression):
        rebuilt = _build_expression(atom, cls, space)
        if rebuilt is not _UNHANDLED:
            return rebuilt
        return _build_hook(atom, cls, space)
    return atom


def _build_symbol(atom: Symbol, cls: type) -> Any:
    if cls is type:
        constructor = constructor_for(atom.name)
        return constructor[0] if constructor is not None else _UNHANDLED
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


def _build_expression(atom: Expression, cls: type | None, space: Any) -> Any:
    if not atom.children or not isinstance(atom.head, Symbol):
        return _UNHANDLED
    if atom.head == Symbol("Buffer"):
        return _build_buffer(atom, cls)
    resolved = _resolve_constructor(atom, cls)
    if resolved is None:
        return _UNHANDLED
    target_cls, registration = resolved
    return _rebuild_registered(atom, target_cls, registration, space)


def _build_buffer(atom: Expression, cls: type | None) -> Any:
    if len(atom.args) != 8 or not isinstance(atom.args[0], Grounded):
        msg = f"{atom} is not a complete Buffer image"
        raise TypeError(msg)
    value = _decode(atom.args[0])
    if cls is not None and not isinstance(value, cls):
        msg = f"the Buffer image carries {type(value).__name__}, not {cls.__name__}"
        raise TypeError(msg)
    return value


def _build_hook(atom: Expression, cls: type | None, space: Any) -> Any:
    if cls is None:
        return atom
    hook = getattr(cls, "__from_metta__", None)
    if hook is None:
        return atom
    return hook(*(build(child, space=space) for child in atom.args))


def _resolve_constructor(atom: Expression, cls: type | None) -> tuple[type, _Registration] | None:
    head = atom.head
    if not isinstance(head, Symbol):
        return None
    resolved = constructor_for(head.name)
    if resolved is not None:
        _require_requested_owner(head, cls, resolved[0])
        return resolved
    return _resolve_default_constructor(head, cls)


def _resolve_default_constructor(head: Symbol, cls: type | None) -> tuple[type, _Registration] | None:
    if cls is None:
        return None
    registration = _lookup(cls) or _default_registration(cls)
    if registration is None or registration.type_name != head.name:
        return None
    if not explicitly_registered(cls):
        _record_registration(cls, registration)
    return cls, registration


def _require_requested_owner(head: Symbol, requested: type | None, owner: type) -> None:
    if requested is None or owner is requested:
        return
    msg = (
        f"({head.name} ...) belongs to {_class_label(owner)}, "
        f"not {_class_label(requested)}; build() will not substitute a different "
        f"class with the same type name"
    )
    raise TypeError(
        msg
    )


def _rebuild_registered(atom: Expression, target_cls: type, registration: _Registration, space: Any) -> Any:
    _require_complete_parts(atom, target_cls, registration)
    kinds = registration.field_types or tuple(None for _ in atom.args)
    parts = [build(child, kind, space=space) for child, kind in zip(atom.args, kinds, strict=True)]
    return _call_reverse(target_cls, registration, parts)


def _require_complete_parts(atom: Expression, target_cls: type, registration: _Registration) -> None:
    if registration.fields and len(atom.args) != len(registration.fields):
        msg = (
            f"({registration.type_name} ...) carries {len(atom.args)} part(s); "
            f"{target_cls.__name__} has {len(registration.fields)} field(s). "
            f"Rebuilding would drop or invent values."
        )
        raise TypeError(
            msg
        )


def _call_reverse(target_cls: type, registration: _Registration, parts: list[Any]) -> Any:
    if registration.from_atom is not None:
        return registration.from_atom(*parts)
    hook = getattr(target_cls, "__from_metta__", None)
    if hook is None:
        msg = (
            f"{target_cls.__name__} has no from_atom and no __from_metta__; "
            f"register the reverse to rebuild it"
        )
        raise TypeError(
            msg
        )
    return hook(*parts)


def _annotation_members(annotation: Any) -> tuple[Any, ...]:
    """Select value annotations through wrappers and type-variable bounds."""
    origin = typing.get_origin(annotation)
    if origin in (typing.Annotated, typing.Required, typing.NotRequired):
        return _annotation_members(typing.get_args(annotation)[0])
    if isinstance(annotation, typing.TypeVar):
        if annotation.__constraints__:
            return tuple(member for constraint in annotation.__constraints__
                         for member in _annotation_members(constraint))
        return _annotation_members(Any if annotation.__bound__ is None else annotation.__bound__)
    if origin in (typing.Union, types.UnionType):
        return tuple(member for option in typing.get_args(annotation)
                     for member in _annotation_members(option))
    return (annotation,)


def _build_annotated(atom: Atom, annotation: Any, space: Any) -> Any:
    if typing.get_origin(annotation) is type:
        return _build_plain(atom, type, space)
    hook = _parameterized_hook(annotation)
    if hook is not None:
        image = _container_image(atom, annotation, hook, space)
        if image is not None:
            return hook.build(image, annotation, partial(build, space=space))
    if isinstance(annotation, type):
        return _build_plain(atom, annotation, space)
    return build(atom, space=space)


def _container_image(atom: Atom, annotation: Any, hook: ParameterizedHook, space: Any) -> Expression | None:
    if hook.space_image is not None:
        rows = _space_rows(atom, space)
        if rows is not None:
            return hook.space_image(rows, annotation)
    return atom if isinstance(atom, Expression) else None


def _space_rows(atom: Atom, space: Any) -> list[Atom] | None:
    handle = lazy('metta._spaces.handle').SpaceHandle
    if isinstance(atom, handle):
        return atom.atoms()
    if not isinstance(atom, (Symbol, Expression)):
        return None
    runtime = space._rt if isinstance(space, handle) else lazy('metta._binding.runtime').active_runtime()
    if runtime is None:
        return None
    row = runtime.once(
        "metta_py_decode_shared(Wire,_Name,_),ground(_Name),"
        "metta_space_registered(_Name),metta_py_atoms(_Name,Rows)",
        Wire=atom.to_wire(),
    )
    return [_atom_from_wire(wire) for wire in row["Rows"]] if row else None


def _build_union(atom: Atom, members: tuple[Any, ...], space: Any) -> Any:
    for member in members:
        if member is not type(None):
            callable_value = _build_callable(atom, member, space)
            if callable_value is not None:
                return callable_value
            hook = _parameterized_hook(member)
            if hook is not None:
                image = _container_image(atom, member, hook, space)
                if image is not None:
                    if hook.matches is None or hook.matches(image, member):
                        return hook.build(image, member, partial(build, space=space))
                    continue
            kind = dict if typing.is_typeddict(member) else typing.get_origin(member) or member
            if _class_matches(atom, kind):
                return build(atom, member, space=space)
    return build(atom, space=space)


def _class_matches(atom: Atom, annotation: Any) -> bool:
    if annotation in (Any, object):
        return True
    if not isinstance(annotation, type):
        return False
    if isinstance(atom, Grounded):
        return isinstance(_decode(atom), annotation)
    if isinstance(atom, Symbol):
        return _symbol_annotation_matches(atom, annotation)
    if isinstance(atom, Expression):
        return _expression_annotation_matches(atom, annotation)
    return False


def _symbol_annotation_matches(atom: Symbol, annotation: type) -> bool:
    return issubclass(annotation, Enum) and atom.name in annotation.__members__


def _expression_annotation_matches(atom: Expression, annotation: type) -> bool:
    if not atom.children or not isinstance(atom.head, Symbol):
        return False
    registration = _lookup(annotation) or _default_registration(annotation)
    return registration is not None and registration.type_name == atom.head.name
