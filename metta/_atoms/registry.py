"""Purpose: own Python type registrations and default conversion metadata.
Guarantees:
  - one public type spelling has one Python owner [tested
    test_type_name_collision_is_refused_and_build_honors_requested_class]
  - malformed default metadata is refused before it enters the registry
    [tested test_invalid_namedtuple_fields_are_refused,
    test_init_false_dataclass_requires_an_explicit_reverse]
  - concurrent collisions produce one owner and one loud refusal [tested
    test_registration_collisions_are_serialized]
  - unregister_type removes the exact class, its constructor, and its public
    type-name claim atomically [tested
    test_type_registration_can_be_removed_and_its_name_reclaimed]
  - TypedDict classes route through their annotation hook rather than the
    ordinary-class registry path
    [tested: test_a_typed_dict_annotation_agrees_with_its_value;
     commit=1b1aa89517584ce3b4abe1024b7a9f85e2c1263d]
  - a slots dataclass replacing an already registered class is refused with
    the decorator order that preserves the new class object
    [tested: test_a_slots_dataclass_registration_follows_the_new_class_or_refuses;
     commit=0bfe63082cdc62b9bb09550d563057321ab90bb6]
  - a dataclass whose required InitVar cannot be reconstructed is refused at
    registration, while a defaulted InitVar remains reconstructible
    [tested: test_each_remaining_annotation_shape_refuses_or_carries;
     commit=ff4ac16f07a6e373e79ed0eae0a4c2d64cb92550]
  - a class that states its positional fields through ``__match_args__``, a
    plain class or an attrs class, destructures field-wise by default with
    the positional constructor as its reverse; attrs state outside that
    tuple and a required constructor parameter it does not name are refused
    rather than lost, and an Atom class has no default image at all
    [tested: test_a_plain_class_with_match_args_destructures_by_default,
    test_an_attrs_class_destructures_by_default,
    test_match_args_registration_refuses_hidden_state;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
Guarded by:
  - _REGISTRY_LOCK protects registrations, constructors, and type owners
    [tested test_registration_collisions_are_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import dataclasses
import inspect
import threading
import typing
from collections.abc import Callable
from typing import Any, NamedTuple

from metta import seam
from metta._atoms.model import Atom

IMAGES = ("symbol", "expression", "handle", "operations")


class _Registration(NamedTuple):
    image: str
    to_atom: Callable[[Any], Any] | None
    from_atom: Callable[..., Any] | None
    type_name: str
    fields: tuple[str, ...]
    field_types: tuple = ()
    # An author's register_type call, as opposed to a default this module
    # memoized for an Enum, dataclass, NamedTuple or pydantic model. The
    # operation result path projects only explicit registrations, so calling
    # project() on a type somewhere never changes what an operation returning
    # that type answers.
    explicit: bool = True


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
    return (
        isinstance(value, type)
        and typing.get_origin(value) is None
        and not typing.is_typeddict(value)
    )


def _class_label(cls: type) -> str:
    """One class label that still distinguishes a same-name redefinition."""
    return f"{cls.__module__}.{cls.__qualname__} (class object {id(cls):#x})"


def register_type(
    cls: type,
    *,
    image: str | None = None,
    to_atom: Callable[[Any], Any] | None = None,
    from_atom: Callable[..., Any] | None = None,
    name: str | None = None,
    fields: tuple[str, ...] = (),
) -> type:
    """Teach the translator one type, pytree-style.

        metta.convert.register_type(
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

    Anything not given is DERIVED FROM THE CLASS, by the same rule that
    applies when nobody registers it. Registering one of those four
    explicitly therefore changes nothing, which is what a sentence saying
    registration is not required has to mean: it used to substitute the
    `expression` default for the derived image and leave `to_atom` empty,
    so `register_type(SomeEnum)` -- and the dataclass and NamedTuple cases
    with it -- replaced a working projection with a TypeError on the next
    project() [tested: test_registering_a_shape_backed_class_changes_nothing].
    """
    if image is not None and image not in IMAGES:
        msg = f"image must be one of {IMAGES}, not {image!r}"
        raise ValueError(msg)
    #Only a BARE register_type(cls) derives. Once the caller has named an
    #image or either direction of the conversion, they have said how this
    #type crosses and the shape has nothing to add. The narrow rule also
    #keeps the derivation's own refusals where they belong: an init=False
    #dataclass cannot be rebuilt by the default expression image and says so,
    #and the remedy it names is exactly a register_type carrying to_atom and
    #from_atom, which must not re-enter the derivation that refused
    #[tested: test_init_false_dataclass_requires_an_explicit_reverse].
    field_types: tuple = ()
    bare = image is to_atom is from_atom is None and not fields
    derived = _default_registration(cls) if bare else None
    if derived is None:
        image = "expression" if image is None else image
    else:
        image = derived.image
        to_atom = derived.to_atom
        from_atom = derived.from_atom
        fields = derived.fields
        field_types = derived.field_types
    type_name = name or cls.__name__
    registration = _Registration(
        image=image,
        to_atom=to_atom,
        from_atom=from_atom,
        type_name=type_name,
        fields=tuple(fields),
        field_types=field_types,
    )
    _record_registration(cls, registration)
    return cls


def unregister_type(cls: type) -> None:
    """Remove one exact class registration and release its public name.

    Raises KeyError when cls has no explicit or memoized registration.
    Existing projected atoms remain atoms, but an untyped build no longer
    selects this class until it is registered again.
    """
    with _REGISTRY_LOCK:
        registration = _REGISTRY.get(cls)
        if registration is None:
            msg = f"{_class_label(cls)} is not registered"
            raise KeyError(msg)
        _discard_old_constructor(cls, registration)
        if _TYPE_OWNERS.get(registration.type_name) is cls:
            del _TYPE_OWNERS[registration.type_name]
        del _REGISTRY[cls]
    if registration.explicit:
        _notify(cls, registration, None)


def ensure_registered(cls: type) -> _Registration:
    """The registration this class projects through, defaults memoized: an
    Enum, dataclass or NamedTuple gets its default image recorded exactly
    as a first projection would record it; anything else must have been
    registered and says so.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    registration = _lookup(cls)
    if registration is None:
        registration = _default_registration(cls)
        if registration is None:
            msg = (
                f"{cls.__name__} has no default image (not an Enum, "
                f"dataclass or NamedTuple); teach the translator with "
                f"register_type(...)"
            )
            raise TypeError(
                msg
            )
        _record_registration(cls, registration)
    return registration


def ensure_own_registration(cls: type) -> _Registration:
    """The registration for THIS exact class, its default memoized for it.

    ``ensure_registered`` walks the MRO, so a subclass of a registered class
    projects through the BASE's entry and answers the base's type name. That is
    right for CONVERSION, where a subclass adding nothing converts as its base,
    and wrong for DECLARATION: declaring a class into a space says it is a type
    THERE, and a type has its own name. Declaring `Dog(Animal)` used to restate
    `(: Animal (-> String Animal))`, which the engine reported as a duplicate
    declaration, and left no `Dog` type to be below `Animal` at all.

    A class with no default image of its own keeps the inherited answer, which
    is what ``ensure_registered`` already gives it, refusal included.
    """
    with _REGISTRY_LOCK:
        own = _REGISTRY.get(cls)
    if own is not None:
        return own
    default = _default_registration(cls)
    if default is None:
        return ensure_registered(cls)
    _record_registration(cls, default)
    return default


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
        msg = (
            f"{cls.__name__} is already registered as {current.type_name!r}; "
            f"changing its type name would leave existing atoms with the old "
            f"owner. Keep that name or register a distinct class."
        )
        raise ValueError(
            msg
        )


def _claim_type_name(cls: type, type_name: str) -> None:
    holder = _TYPE_OWNERS.get(type_name)
    if holder is not None and holder is not cls:
        if (
            holder.__module__ == cls.__module__
            and holder.__qualname__ == cls.__qualname__
            and dataclasses.is_dataclass(cls)
            and "__slots__" in cls.__dict__
        ):
            msg = (
                f"dataclass(slots=True) replaced the registered {cls.__qualname__} "
                "class object; place register_type outside the dataclass "
                "decorator so it receives the replacement class"
            )
            raise ValueError(msg)
        msg = (
            f"the type name {type_name!r} already has a registered class "
            f"({_class_label(holder)}); register {_class_label(cls)} with "
            f"name=... to pick a distinct spelling. Replacing the owner "
            f"would make build() return the wrong class."
        )
        raise ValueError(
            msg
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


# Registration listeners let an engine reflect explicit
# registrations as atoms without this module knowing engines exist. Each
# callback receives (cls, old, new), new None on unregister; only EXPLICIT
# entries notify, because the memoized defaults are this module's private
# bookkeeping. Callbacks run OUTSIDE the lock, so a listener may call back
# into the registry or into an engine without deadlocking; the ordering
# guarantee is per-class, from the mutation order under the lock.
_LISTENERS: list[Callable[[type, Any, Any], None]] = []


def subscribe_registrations(
    callback: Callable[[type, Any, Any], None],
) -> list[tuple[type, _Registration]]:
    """Subscribe to explicit registration changes; answers the current
    explicit entries so the subscriber can reflect the past before it hears
    the future.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    with _REGISTRY_LOCK:
        snapshot = [
            (cls, reg) for cls, reg in _REGISTRY.items() if reg.explicit
        ]
        _LISTENERS.append(callback)
    return snapshot


def _notify(cls: type, old: _Registration | None, new: _Registration | None) -> None:
    # Take a snapshot so a callback that subscribes another listener cannot
    # extend the notification currently in flight.
    for callback in tuple(_LISTENERS):
        callback(cls, old, new)


def _record_registration(cls: type, registration: _Registration) -> None:
    with _REGISTRY_LOCK:
        old = _REGISTRY.get(cls)
        _record_registration_locked(cls, registration)
    if registration.explicit:
        _notify(cls, old if old is not None and old.explicit else None, registration)


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
    """The image common types get without being registered.

    An atom IS the translation; its __match_args__ states destructuring for
    Python's match statement, not a constructor image, so it is refused here
    rather than offered to the rows.

    Everything else is the `image` point: rows are consulted in registration
    order and the first that recognises the class answers, so a model
    framework whose classes are also dataclasses is asked before the
    structural rows and a framework this seat has never heard of registers
    rather than being added to a chain here.
    """
    if issubclass(cls, Atom):
        return None
    claim = seam.image.claim(cls)
    return None if claim is None else claim.answer


def _dataclass_registration(cls: type) -> _Registration:
    data_fields = dataclasses.fields(typing.cast(Any, cls))
    non_init = tuple(field.name for field in data_fields if not field.init)
    if non_init:
        listed = ", ".join(non_init)
        msg = (
            f"{cls.__name__} has init=False state that the default expression "
            f"image cannot rebuild ({listed}). Register the type explicitly "
            f"with to_atom and from_atom."
        )
        raise TypeError(
            msg
        )
    names = tuple(field.name for field in data_fields)
    required_non_fields = _required_parameters_outside(cls, names)
    if required_non_fields:
        listed = ", ".join(required_non_fields)
        msg = (
            f"{cls.__name__} has required constructor state that dataclass "
            f"fields() cannot project ({listed}); give each InitVar a default "
            "or register an explicit conversion"
        )
        raise TypeError(msg)
    return _Registration(
        "expression",
        lambda obj: tuple(getattr(obj, name) for name in names),
        lambda *parts: cls(**dict(zip(names, parts, strict=True))),
        cls.__name__,
        names,
        _field_types(cls, names),
        explicit=False,
    )


def _required_parameters_outside(cls: type, names: tuple[str, ...]) -> tuple[str, ...]:
    """Constructor parameters with no default that the projected fields do not name.

    Each is state the positional or keyword rebuild cannot supply, so a
    registration that would lose it is refused before any data is lost. A
    class whose signature cannot be read has nothing to report here.
    """
    try:
        parameters = inspect.signature(cls).parameters.values()
    except (TypeError, ValueError):
        return ()
    return tuple(
        parameter.name
        for parameter in parameters
        if parameter.name not in names
        and parameter.default is inspect.Parameter.empty
        and parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    )


def _match_args_registration(cls: type, names: tuple[str, ...]) -> _Registration:
    """The image a class states for itself through PEP 634's ``__match_args__``.

    The tuple is the class's own statement of its positional fields, and the
    reverse the same tuple promises is the positional constructor call. attrs
    sets it for every ``define``d class and a plain class may set it by hand;
    dataclasses and NamedTuples never reach here because their own rules run
    first. Hidden state is refused the way the dataclass rule refuses
    ``init=False``: an attrs attribute the tuple does not name, ``init=False``
    or ``kw_only``, would be dropped or reset on the way back, and so would a
    required constructor parameter outside the tuple.
    """
    hidden = tuple(
        attribute.name
        for attribute in getattr(cls, "__attrs_attrs__", ())
        if attribute.name not in names
    )
    if hidden:
        listed = ", ".join(hidden)
        msg = (
            f"{cls.__name__} keeps attrs state its __match_args__ does not "
            f"name ({listed}), which the positional rebuild would lose; "
            "register the type explicitly with to_atom and from_atom"
        )
        raise TypeError(msg)
    required = _required_parameters_outside(cls, names)
    if required:
        listed = ", ".join(required)
        msg = (
            f"{cls.__name__} requires constructor state its __match_args__ "
            f"does not name ({listed}); give it a default or register an "
            "explicit conversion"
        )
        raise TypeError(msg)
    return _Registration(
        "expression",
        lambda obj: tuple(getattr(obj, name) for name in names),
        cls,
        cls.__name__,
        names,
        _field_types(cls, names),
        explicit=False,
    )


def _named_tuple_registration(cls: type) -> _Registration:
    raw_names = typing.cast(Any, cls)._fields
    if not (
        isinstance(raw_names, tuple)
        and all(isinstance(name, str) for name in raw_names)
    ):
        msg = f"{cls.__name__} declares invalid NamedTuple fields: {raw_names!r}"
        raise TypeError(
            msg
        )
    names = typing.cast(tuple[str, ...], raw_names)
    return _Registration(
        "expression",
        tuple,
        cls,
        cls.__name__,
        names,
        _field_types(cls, names),
        explicit=False,
    )


def resolved_hints(cls: type) -> dict:
    """A class's annotations, resolved, or a TypeError naming the class.

    Shared because both callers need the same refusal: a field annotation
    that does not resolve is a mistake in the declaration, and saying which
    class it was in is the whole value of catching it here rather than
    letting NameError surface from typing's internals.
    """
    try:
        return typing.get_type_hints(cls)
    except Exception as exc:
        msg = (
            f"the field annotations of {cls.__name__} do not resolve "
            f"({exc}); a declared field type must name something importable"
        )
        raise TypeError(
            msg
        ) from exc


def _field_types(cls: type, names: tuple[str, ...]) -> tuple:
    """Declared field annotations, kept WHOLE, for rebuilding parts that
    need their class: an Enum member above all, but also an Enum inside
    list[Colour] or Optional[Colour], which a bare-class filter would
    erase and leave as an unreconstructed symbol. Annotations that do not
    resolve are a hard error naming the class.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    hints = resolved_hints(cls)
    return tuple(hints.get(n) for n in names)
