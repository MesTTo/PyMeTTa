"""Purpose: the two-way translator between Python objects and MeTTa. There is
no single conversion: an Enum wants to become symbols the matcher sees
through, a model wants to stay one opaque handle, a dataclass wants to be a
constructor expression whose parts match. So this is four images, a rule for
choosing, defaults so common types need no registration, and a registry in
the shape JAX proved with pytrees: a type, a flatten, an unflatten. project()
turns an object into atoms plus the declarations that type them; build() is
the missing reverse, rebuilding the object an answer describes.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import itertools
import sys
import typing
from enum import Enum
from typing import Any, Callable, NamedTuple

from .atoms import Atom, Expr, Gnd, S, Sym, decode, encode, val

__all__ = [
    "register_type",
    "ensure_registered",
    "project",
    "build",
    "declarations",
    "Projected",
    "IMAGES",
]

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


class Projected(NamedTuple):
    """What a projection produced: the atom, and the declarations typing it.

    The declarations are (: ...) atoms; adding them to a space once makes
    every later projection of the same type participate in get-type.
    """

    atom: Atom
    declarations: tuple[Expr, ...]


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
    if image in ("expression", "symbol"):
        holder = _CONSTRUCTORS.get(type_name)
        if holder is not None and holder[0] is not cls:
            raise ValueError(
                f"the constructor name {type_name!r} already belongs to "
                f"{holder[0].__name__}; two types under one name would "
                f"rebuild each other's atoms. Register with name=... to "
                f"pick a distinct spelling."
            )
        _CONSTRUCTORS[type_name] = (cls, registration)
    _REGISTRY[cls] = registration
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
        _REGISTRY[cls] = registration
        if registration.image == "expression":
            _CONSTRUCTORS[registration.type_name] = (cls, registration)
    return registration


def _lookup(cls: type) -> _Registration | None:
    for base in cls.__mro__:
        hit = _REGISTRY.get(base)
        if hit is not None:
            return hit
    return None


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
        names = tuple(cls.model_fields.keys())
        return _Registration(
            "expression",
            lambda obj: tuple(getattr(obj, n) for n in names),
            # model_validate with by_name, not cls(**...): a field declared
            # with an alias validates under the alias in the constructor,
            # while projection read the ATTRIBUTE names, and by_name lets
            # the attribute names validate directly.
            lambda *parts: cls.model_validate(
                dict(zip(names, parts)), by_name=True
            ),
            cls.__name__,
            names,
            _field_types(cls, names),
        )
    if dataclasses.is_dataclass(cls) and not isinstance(cls, type(None)):
        names = tuple(f.name for f in dataclasses.fields(cls))
        return _Registration(
            "expression",
            lambda obj: tuple(getattr(obj, n) for n in names),
            lambda *parts: cls(*parts),
            cls.__name__,
            names,
            _field_types(cls, names),
        )
    if issubclass(cls, tuple) and hasattr(cls, "_fields"):  # NamedTuple
        names = tuple(cls._fields)
        return _Registration(
            "expression",
            lambda obj: tuple(obj),
            lambda *parts: cls(*parts),
            cls.__name__,
            names,
            _field_types(cls, names),
        )
    return None


def _field_types(cls: type, names: tuple[str, ...]) -> tuple:
    """Declared field annotations, kept WHOLE, for rebuilding parts that
    need their class: an Enum member above all, but also an Enum inside
    list[Colour] or Optional[Colour], which a bare-class filter would
    erase and leave as an unreconstructed symbol. Annotations that do not
    resolve are a hard error naming the class."""
    import typing

    try:
        hints = typing.get_type_hints(cls)
    except Exception as exc:
        raise TypeError(
            f"the field annotations of {cls.__name__} do not resolve "
            f"({exc}); a declared field type must name something importable"
        ) from exc
    return tuple(hints.get(n) for n in names)


def project(value: Any) -> Projected:
    """One Python value into MeTTa, by the image its type chose.

    The rule, from what the object is rather than from taste: match on its
    parts wants a symbol or an expression, since those are what the matcher
    sees through; identity mattering wants a handle, since a copy would lie.
    Defaults: an Enum member becomes its symbol, a dataclass or NamedTuple a
    constructor expression with parts projected recursively, and everything
    unregistered a grounded handle carried whole, unified by identity.

    project is the explicit spelling; encode() stays value-preserving
    (a dataclass through encode is a handle). The two intents are different:
    encode carries, project translates.
    """
    if isinstance(value, Atom):
        return Projected(value, ())
    if isinstance(value, (bool, int, float, str)):
        return Projected(encode(value), ())
    if isinstance(value, (list, tuple)) and not hasattr(type(value), "_fields"):
        parts = [project(v) for v in value]
        decls: list[Expr] = []
        for p in parts:
            decls.extend(p.declarations)
        return Projected(Expr([p.atom for p in parts]), _dedup(decls))

    cls = type(value)
    registration = _lookup(cls)
    if registration is None:
        registration = _default_registration(cls)
        if registration is not None:
            # Memoized, so the reverse direction knows the constructor a
            # default projection used without an explicit registration.
            _REGISTRY[cls] = registration
            if registration.image == "expression":
                _CONSTRUCTORS[registration.type_name] = (cls, registration)

    if registration is None:
        hook = getattr(value, "__metta__", None)
        if hook is not None:
            atom = hook()
            if not isinstance(atom, Atom):
                raise TypeError(
                    f"__metta__ on {cls.__name__} returned {type(atom).__name__}, not an Atom"
                )
            return Projected(atom, ())
        return Projected(val(value), ())

    if registration.image == "symbol":
        if registration.to_atom is not None:
            # A registered spelling: the symbol the registrant chose.
            text = registration.to_atom(value)
            return Projected(
                Sym(str(text)),
                (Expr([S[":"], Sym(str(text)), Sym(registration.type_name)]),),
            )
        return _project_symbol(value, cls, registration)
    if registration.image == "handle":
        return Projected(val(value), ())
    if registration.image == "operations":
        raise TypeError(
            f"{cls.__name__} is registered with the operations image: its "
            f"behaviour crosses as registered operations, not as data. Use "
            f"petta.integrate.wrap_object to register its methods, and carry "
            f"the instance with petta.val."
        )
    return _project_expression(value, cls, registration)


def _project_symbol(value: Any, cls: type, registration: _Registration) -> Projected:
    if isinstance(value, Enum):
        member = Sym(value.name)
        decls = [Expr([S[":"], Sym(cls.__name__), S.Type])]
        decls.extend(Expr([S[":"], Sym(m.name), Sym(cls.__name__)]) for m in cls)
        return Projected(member, tuple(decls))
    text = str(value)
    return Projected(
        Sym(text),
        (Expr([S[":"], Sym(text), Sym(registration.type_name)]),),
    )


def _project_expression(value: Any, cls: type, registration: _Registration) -> Projected:
    to_atom = registration.to_atom
    if to_atom is None:
        raise TypeError(
            f"{cls.__name__} is registered as an expression but has no "
            f"to_atom; register one, or give the class __metta__"
        )
    children = to_atom(value)
    if not isinstance(children, (list, tuple)):
        children = (children,)
    projected = [project(c) for c in children]
    decls: list[Expr] = []
    for p in projected:
        decls.extend(p.declarations)
    decls.append(_constructor_declaration(registration, projected))
    atom = Expr([Sym(registration.type_name), *(p.atom for p in projected)])
    return Projected(atom, _dedup(decls))


def _constructor_declaration(registration: _Registration, projected: list[Projected]) -> Expr:
    """(: Person (-> String Number Person)), argument types read off the parts."""
    arg_types = [S[_type_name_of(p.atom)] for p in projected]
    return Expr(
        [
            S[":"],
            Sym(registration.type_name),
            Expr([S["->"], *arg_types, Sym(registration.type_name)]),
        ]
    )


def _type_name_of(atom: Atom) -> str:
    if isinstance(atom, Gnd):
        v = atom.value
        if isinstance(v, bool):
            return "Bool"
        if isinstance(v, (int, float)):
            return "Number"
        if isinstance(v, str):
            return "String"
        return "%Undefined%"
    if isinstance(atom, Expr) and atom.children and isinstance(atom.head, Sym):
        name = atom.head.name
        if name in _CONSTRUCTORS:
            return _CONSTRUCTORS[name][1].type_name
    if isinstance(atom, Sym):
        for _cls, reg in _CONSTRUCTORS.values():
            if reg.image == "symbol":
                return reg.type_name
    return "%Undefined%"


def declarations(cls: type) -> tuple[Expr, ...]:
    """The (: ...) atoms a type contributes, without projecting an instance.
    Constructor arrows carry the field annotations' own types, mapped the
    way registration maps signatures, so a dataclass field typed float
    declares Number rather than %Undefined%; a Union field superposes one
    arrow per member, the checker's own reading of alternatives."""
    if issubclass(cls, Enum):
        decls = [Expr([S[":"], Sym(cls.__name__), S.Type])]
        decls.extend(Expr([S[":"], Sym(m.name), Sym(cls.__name__)]) for m in cls)
        return tuple(decls)
    registration = _lookup(cls) or _default_registration(cls)
    if registration is None or registration.image != "expression":
        return ()
    from .ops import type_atoms_for

    fields = registration.fields or ()
    try:
        hints = typing.get_type_hints(cls)
    except Exception as exc:
        raise TypeError(
            f"the field annotations of {cls.__name__} do not resolve "
            f"({exc}); a declared field type must name something importable"
        ) from exc
    alternative_lists = [
        type_atoms_for(hints[f]) if f in hints else [S["%Undefined%"]]
        for f in fields
    ]
    out: list[Expr] = []
    for combo in itertools.product(*alternative_lists):
        declaration = Expr(
            [
                S[":"],
                Sym(registration.type_name),
                Expr([S["->"], *combo, Sym(registration.type_name)]),
            ]
        )
        if declaration not in out:
            out.append(declaration)
    return tuple(out)


def build(atom: Atom, cls: Any = None) -> Any:
    """The reverse: rebuild the Python value an atom describes.

    A constructor expression rebuilds through its registered from_atom,
    children rebuilt recursively; an Enum symbol rebuilds to the member when
    cls names the Enum; a grounded atom unwraps to its value. cls may be a
    full annotation, not only a class: Optional[Colour] tries its members,
    list[Colour] rebuilds each element, Annotated unwraps. Anything else
    is returned as the atom it is, which is the honest answer for structure
    with no registered reverse.
    """
    if cls is not None and not isinstance(cls, type):
        return _build_annotated(atom, cls)
    if isinstance(atom, Gnd):
        return decode(atom)
    if isinstance(atom, Sym) and cls is not None:
        if issubclass(cls, Enum):
            return cls[atom.name]
        registration = _lookup(cls)
        if (
            registration is not None
            and registration.image == "symbol"
            and registration.from_atom is not None
        ):
            return registration.from_atom(atom.name)
    if isinstance(atom, Expr) and atom.children and isinstance(atom.head, Sym):
        hit = _CONSTRUCTORS.get(atom.head.name)
        if hit is None and cls is not None:
            registration = _lookup(cls) or _default_registration(cls)
            if registration is not None and registration.type_name == atom.head.name:
                hit = (cls, registration)
        if hit is not None:
            target_cls, registration = hit
            if registration.fields and len(atom.args) != len(registration.fields):
                raise TypeError(
                    f"({atom.head.name} ...) carries {len(atom.args)} "
                    f"part(s); {target_cls.__name__} has "
                    f"{len(registration.fields)} field(s). Rebuilding would "
                    f"drop or invent values."
                )
            kinds = registration.field_types or tuple(None for _ in atom.args)
            parts = [build(c, k) for c, k in zip(atom.args, kinds)]
            if registration.from_atom is None:
                hook = getattr(target_cls, "__from_metta__", None)
                if hook is None:
                    raise TypeError(
                        f"{target_cls.__name__} has no from_atom and no "
                        f"__from_metta__; register the reverse to rebuild it"
                    )
                return hook(*parts)
            return registration.from_atom(*parts)
    hook_cls = cls or None
    if hook_cls is not None:
        hook = getattr(hook_cls, "__from_metta__", None)
        if hook is not None and isinstance(atom, Expr):
            return hook(*(build(c) for c in atom.args))
    return atom


def _build_annotated(atom: Atom, annotation: Any) -> Any:
    """Rebuild guided by a typing annotation rather than a bare class:
    Annotated unwraps, a Union tries the member the atom's shape names,
    and a sequence annotation rebuilds elementwise into its container."""
    import types as _types

    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _build_annotated(atom, typing.get_args(annotation)[0])
    if origin in (typing.Union, _types.UnionType):
        members = [
            member
            for member in typing.get_args(annotation)
            if member is not type(None)
        ]
        for member in members:
            try:
                candidate = build(atom, member)
            except (KeyError, TypeError):
                continue  # not this member's shape; the next may claim it
            if candidate is not atom:
                return candidate
        return build(atom, None)
    if isinstance(atom, Expr) and isinstance(origin, type):
        import collections.abc as abc

        args = typing.get_args(annotation)
        if origin is tuple:
            if args and args[-1] is Ellipsis:
                return tuple(build(c, args[0]) for c in atom.children)
            if args and len(args) == len(atom.children):
                return tuple(build(c, a) for c, a in zip(atom.children, args))
            return tuple(build(c) for c in atom.children)
        if origin is list or issubclass(origin, abc.Sequence):
            element = args[0] if args else None
            return [build(c, element) for c in atom.children]
    if isinstance(annotation, type):
        return build(atom, annotation)
    return build(atom, None)


def _dedup(decls: list[Expr]) -> tuple[Expr, ...]:
    seen: list[Expr] = []
    for d in decls:
        if d not in seen:
            seen.append(d)
    return tuple(seen)
