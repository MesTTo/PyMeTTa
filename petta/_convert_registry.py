"""Purpose: own Python type registrations and default conversion metadata.
Guarantees:
  - one public type spelling has one Python owner [tested
    test_type_name_collision_is_refused_and_build_honors_requested_class]
  - malformed default metadata is refused before it enters the registry
    [tested test_invalid_namedtuple_fields_are_refused,
    test_init_false_dataclass_requires_an_explicit_reverse]
  - concurrent collisions produce one owner and one loud refusal [tested
    test_registration_collisions_are_serialized]
Guarded by:
  - _REGISTRY_LOCK protects registrations, constructors, and type owners
    [tested test_registration_collisions_are_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import sys
import threading
import typing
from collections.abc import Callable
from enum import Enum
from typing import Any, NamedTuple

IMAGES = ("symbol", "expression", "handle", "operations")


class _Registration(NamedTuple):
    image: str
    to_atom: Callable[[Any], Any] | None
    from_atom: Callable[..., Any] | None
    type_name: str
    fields: tuple[str, ...]
    field_types: tuple = ()


# type -> registration, consulted before the defaults.
_REGISTRY: dict[type, _Registration] = {}

# constructor symbol name -> (type, registration), for the reverse direction.
_CONSTRUCTORS: dict[str, tuple[type, _Registration]] = {}

# declared type name -> its one Python owner. Two unrelated classes cannot
# share a constructor/type spelling because an unannotated build has no way
# to select between them.
_TYPE_OWNERS: dict[str, type] = {}
_REGISTRY_LOCK = threading.RLock()


def _is_plain_class(value: object) -> bool:
    """Whether value is a class rather than a parameterized annotation."""
    return isinstance(value, type) and typing.get_origin(value) is None


def _class_label(cls: type) -> str:
    """One class label that still distinguishes a same-name redefinition."""
    return f"{cls.__module__}.{cls.__qualname__} (class object {id(cls):#x})"


def register_type(
    cls: type,
    *,
    image: str = "expression",
    to_atom: Callable[[Any], Any] | None = None,
    from_atom: Callable[..., Any] | None = None,
    name: str | None = None,
    fields: tuple[str, ...] = (),
) -> type:
    """Teach the translator one type, pytree-style.

        petta.convert.register_type(
            Person,
            image="expression",
            to_atom=lambda p: (p.name, p.age),
            from_atom=lambda name, age: Person(name, age),
        )

    to_atom returns the children (projected recursively); from_atom rebuilds
    from them, and IS the answer to "what should build() return for this
    atom": the reverse is yours to define, per type, and build() consults
    it whenever the constructor name matches. A class you own may carry
    __metta__ and __from_metta__ instead and skip registration. Nothing
    here is required for the common cases: an Enum, dataclass, NamedTuple
    or pydantic model translates by default, both ways, from the class
    alone. image chooses among symbol, expression, handle and operations;
    the docstring of project() states the rule for choosing. Returns cls,
    so it composes as a decorator.
    """
    if image not in IMAGES:
        raise ValueError(f"image must be one of {IMAGES}, not {image!r}")
    type_name = name or cls.__name__
    registration = _Registration(
        image=image,
        to_atom=to_atom,
        from_atom=from_atom,
        type_name=type_name,
        fields=tuple(fields),
    )
    _record_registration(cls, registration)
    return cls


def ensure_registered(cls: type) -> _Registration:
    """The registration this class projects through, defaults memoized: an
    Enum, dataclass or NamedTuple gets its default image recorded exactly
    as a first projection would record it; anything else must have been
    registered and says so."""
    registration = _lookup(cls)
    if registration is None:
        registration = _default_registration(cls)
        if registration is None:
            raise TypeError(
                f"{cls.__name__} has no default image (not an Enum, "
                f"dataclass or NamedTuple); teach the translator with "
                f"register_type(...)"
            )
        _record_registration(cls, registration)
    return registration


def _record_registration_locked(cls: type, registration: _Registration) -> None:
    """Record one registration after proving its public type name is safe."""
    current = _REGISTRY.get(cls)
    _require_stable_type_name(cls, registration, current)
    if registration.image in ("expression", "symbol"):
        _claim_type_name(cls, registration.type_name)
    _discard_old_constructor(cls, current)
    if registration.image == "expression":
        _CONSTRUCTORS[registration.type_name] = (cls, registration)
    _REGISTRY[cls] = registration


def _require_stable_type_name(
    cls: type,
    registration: _Registration,
    current: _Registration | None,
) -> None:
    if current is not None and current.type_name != registration.type_name:
        raise ValueError(
            f"{cls.__name__} is already registered as {current.type_name!r}; "
            f"changing its type name would leave existing atoms with the old "
            f"owner. Keep that name or register a distinct class."
        )


def _claim_type_name(cls: type, type_name: str) -> None:
    holder = _TYPE_OWNERS.get(type_name)
    if holder is not None and holder is not cls:
        raise ValueError(
            f"the type name {type_name!r} already has a registered class "
            f"({_class_label(holder)}); register {_class_label(cls)} with "
            f"name=... to pick a distinct spelling. Replacing the owner "
            f"would make build() return the wrong class."
        )
    _TYPE_OWNERS[type_name] = cls


def _discard_old_constructor(cls: type, current: _Registration | None) -> None:
    if current is None or current.image != "expression":
        return
    old = _CONSTRUCTORS.get(current.type_name)
    if old is not None and old[0] is cls:
        _CONSTRUCTORS.pop(current.type_name)


def _lookup_locked(cls: type) -> _Registration | None:
    for base in cls.__mro__:
        hit = _REGISTRY.get(base)
        if hit is not None:
            return hit
    return None


def _record_registration(cls: type, registration: _Registration) -> None:
    with _REGISTRY_LOCK:
        _record_registration_locked(cls, registration)


def _lookup(cls: type) -> _Registration | None:
    with _REGISTRY_LOCK:
        return _lookup_locked(cls)


def constructor_for(name: str) -> tuple[type, _Registration] | None:
    """Return the registered owner of one constructor spelling."""
    with _REGISTRY_LOCK:
        return _CONSTRUCTORS.get(name)


def explicitly_registered(cls: type) -> bool:
    """Whether cls has an explicit or memoized registry entry."""
    with _REGISTRY_LOCK:
        return cls in _REGISTRY


def _default_registration(cls: type) -> _Registration | None:
    """The image common types get without being registered."""
    if issubclass(cls, Enum):
        return _Registration("symbol", None, None, cls.__name__, ())
    # A pydantic model is a constructor expression like a dataclass, its
    # fields read from model_fields and its rebuild through the class
    # itself, so validation runs exactly where pydantic runs it. Detected
    # through sys.modules: if pydantic was never imported, no BaseModel
    # subclass can exist, and the library keeps zero dependency on it.
    pydantic = sys.modules.get("pydantic")
    if pydantic is not None and issubclass(cls, pydantic.BaseModel):
        return _pydantic_registration(cls)
    if dataclasses.is_dataclass(cls) and cls is not type(None):
        return _dataclass_registration(cls)
    if issubclass(cls, tuple) and hasattr(cls, "_fields"):  # NamedTuple
        return _named_tuple_registration(cls)
    return None


def _pydantic_registration(cls: type) -> _Registration:
    model_cls: Any = cls
    names = tuple(model_cls.model_fields.keys())

    def pydantic_parts(obj: Any) -> tuple[Any, ...]:
        extras = getattr(obj, "__pydantic_extra__", None)
        if extras:
            extra_names = ", ".join(sorted(map(str, extras)))
            raise TypeError(
                f"cannot project {cls.__name__}: its Pydantic extra fields "
                f"would be lost ({extra_names}). Declare those fields on "
                f"the model or register an explicit conversion."
            )
        return tuple(getattr(obj, name) for name in names)

    return _Registration(
        "expression",
        pydantic_parts,
        # model_validate with by_name, not cls(**...): a field declared with
        # an alias validates under the alias in the constructor, while
        # projection read attribute names, and by_name accepts them directly.
        lambda *parts: model_cls.model_validate(
            dict(zip(names, parts, strict=True)), by_name=True
        ),
        cls.__name__,
        names,
        _field_types(cls, names),
    )


def _dataclass_registration(cls: type) -> _Registration:
    data_fields = dataclasses.fields(typing.cast(Any, cls))
    non_init = tuple(field.name for field in data_fields if not field.init)
    if non_init:
        listed = ", ".join(non_init)
        raise TypeError(
            f"{cls.__name__} has init=False state that the default expression "
            f"image cannot rebuild ({listed}). Register the type explicitly "
            f"with to_atom and from_atom."
        )
    names = tuple(field.name for field in data_fields)
    return _Registration(
        "expression",
        lambda obj: tuple(getattr(obj, name) for name in names),
        lambda *parts: cls(**dict(zip(names, parts, strict=True))),
        cls.__name__,
        names,
        _field_types(cls, names),
    )


def _named_tuple_registration(cls: type) -> _Registration:
    raw_names = typing.cast(Any, cls)._fields
    if not (
        isinstance(raw_names, tuple)
        and all(isinstance(name, str) for name in raw_names)
    ):
        raise TypeError(
            f"{cls.__name__} declares invalid NamedTuple fields: {raw_names!r}"
        )
    names = typing.cast(tuple[str, ...], raw_names)
    return _Registration(
        "expression",
        tuple,
        cls,
        cls.__name__,
        names,
        _field_types(cls, names),
    )


def _field_types(cls: type, names: tuple[str, ...]) -> tuple:
    """Declared field annotations, kept WHOLE, for rebuilding parts that
    need their class: an Enum member above all, but also an Enum inside
    list[Colour] or Optional[Colour], which a bare-class filter would
    erase and leave as an unreconstructed symbol. Annotations that do not
    resolve are a hard error naming the class."""
    try:
        hints = typing.get_type_hints(cls)
    except Exception as exc:
        raise TypeError(
            f"the field annotations of {cls.__name__} do not resolve "
            f"({exc}); a declared field type must name something importable"
        ) from exc
    return tuple(hints.get(n) for n in names)
