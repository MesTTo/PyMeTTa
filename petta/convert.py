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
from enum import Enum
from typing import Any, Callable, NamedTuple

from .atoms import Atom, Expr, Gnd, S, Sym, decode, encode, val

__all__ = [
    "register_type",
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
    from them. A class you own may carry __metta__ and __from_metta__ instead
    and skip registration. image chooses among symbol, expression, handle and
    operations; the docstring of project() states the rule for choosing.
    Returns cls, so it composes as a decorator.
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
    _REGISTRY[cls] = registration
    if image == "expression":
        _CONSTRUCTORS[type_name] = (cls, registration)
    return cls


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
    if dataclasses.is_dataclass(cls) and not isinstance(cls, type(None)):
        names = tuple(f.name for f in dataclasses.fields(cls))
        return _Registration(
            "expression",
            lambda obj: tuple(getattr(obj, n) for n in names),
            lambda *parts: cls(*parts),
            cls.__name__,
            names,
        )
    if issubclass(cls, tuple) and hasattr(cls, "_fields"):  # NamedTuple
        names = tuple(cls._fields)
        return _Registration(
            "expression",
            lambda obj: tuple(obj),
            lambda *parts: cls(*parts),
            cls.__name__,
            names,
        )
    return None


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
    """The (: ...) atoms a type contributes, without projecting an instance."""
    if issubclass(cls, Enum):
        decls = [Expr([S[":"], Sym(cls.__name__), S.Type])]
        decls.extend(Expr([S[":"], Sym(m.name), Sym(cls.__name__)]) for m in cls)
        return tuple(decls)
    registration = _lookup(cls) or _default_registration(cls)
    if registration is None or registration.image != "expression":
        return ()
    fields = registration.fields or ()
    arg_types = [S["%Undefined%"] for _ in fields]
    return (
        Expr(
            [
                S[":"],
                Sym(registration.type_name),
                Expr([S["->"], *arg_types, Sym(registration.type_name)]),
            ]
        ),
    )


def build(atom: Atom, cls: type | None = None) -> Any:
    """The reverse: rebuild the Python value an atom describes.

    A constructor expression rebuilds through its registered from_atom,
    children rebuilt recursively; an Enum symbol rebuilds to the member when
    cls names the Enum; a grounded atom unwraps to its value. Anything else
    is returned as the atom it is, which is the honest answer for structure
    with no registered reverse.
    """
    if isinstance(atom, Gnd):
        return decode(atom)
    if isinstance(atom, Sym) and cls is not None and issubclass(cls, Enum):
        return cls[atom.name]
    if isinstance(atom, Expr) and atom.children and isinstance(atom.head, Sym):
        hit = _CONSTRUCTORS.get(atom.head.name)
        if hit is None and cls is not None:
            registration = _lookup(cls) or _default_registration(cls)
            if registration is not None and registration.type_name == atom.head.name:
                hit = (cls, registration)
        if hit is not None:
            target_cls, registration = hit
            if registration.from_atom is None:
                hook = getattr(target_cls, "__from_metta__", None)
                if hook is None:
                    raise TypeError(
                        f"{target_cls.__name__} has no from_atom and no "
                        f"__from_metta__; register the reverse to rebuild it"
                    )
                return hook(*(build(c) for c in atom.args))
            return registration.from_atom(*(build(c) for c in atom.args))
    hook_cls = cls or None
    if hook_cls is not None:
        hook = getattr(hook_cls, "__from_metta__", None)
        if hook is not None and isinstance(atom, Expr):
            return hook(*(build(c) for c in atom.args))
    return atom


def _dedup(decls: list[Expr]) -> tuple[Expr, ...]:
    seen: list[Expr] = []
    for d in decls:
        if d not in seen:
            seen.append(d)
    return tuple(seen)
