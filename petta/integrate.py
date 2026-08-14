"""Purpose: the interface any Python library implements to work deeply with
PeTTa, and the toolkit that makes implementing it a page of code rather than
a project. An integration is a module with install_petta(m), an object with
name and install(m), or an entry point in the petta.integrations group; the
toolkit covers the capabilities an integration is made of: bulk operations
from a module, an instance's methods as operations, protocol-based typing
and printing, two-way value translation, structure reflected into facts,
spaces backed by the library's own storage, and reflective py-field
reasoning over any object.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from collections.abc import Callable, Iterable
from importlib import metadata
from typing import Any, Protocol, runtime_checkable

from . import convert
from ._ops import PROTOCOL_TYPES
from .atoms import (
    Atom,
    Expr,
    Gnd,
    S,
    Sym,
    Var,
    decode,
    encode,
    expr,
    register_object_repr_protocol,
    val,
)
from .errors import PettaError
from .foreign import SpaceProvider

__all__ = [
    "Integration",
    "SpaceProvider",
    "discover",
    "facts",
    "install_reflection_ops",
    "installed",
    "integrate",
    "module_ops",
    "reflect",
    "register_object_type",
    "register_reflector",
    "register_type",
    "wrap_callable",
    "wrap_object",
]

ENTRY_POINT_GROUP = "petta.integrations"


@runtime_checkable
class Integration(Protocol):
    """What integrate() accepts beyond a module: a name and an installer."""

    name: str

    def install(self, m) -> None: ...


_INSTALLED: dict[tuple[str, str], Any] = {}


def integrate(m, target: Any) -> str:
    """Install an integration on a space, idempotently per (space, name).

    target may be: a module (or dotted module name) defining install_petta(m),
    an Integration object, or the name of an installed package's entry point
    in the petta.integrations group. Returns the integration's name.

    Idempotence is per SPACE, because equations and facts an installer
    writes land in the space it was handed: installing into a second space
    installs again there. Operations are process-wide either way, and
    re-registering them is the registry's ordinary replacement.
    """
    if isinstance(target, str):
        target = _resolve(target)
    if isinstance(target, Integration):
        name, installer = target.name, target.install
    elif hasattr(target, "install_petta"):
        name = getattr(target, "__name__", type(target).__name__)
        installer = target.install_petta
    else:
        raise PettaError(
            f"{target!r} is not an integration: define install_petta(m) on "
            f"the module, or provide an object with .name and .install(m)"
        )
    key = (m.space_name, name)
    if key not in _INSTALLED:
        installer(m)
        _INSTALLED[key] = target
    return name


def installed() -> dict[tuple[str, str], Any]:
    """(space, integration name) -> the installed target."""
    return _INSTALLED.copy()


def _resolve(name: str) -> Any:
    for entry in metadata.entry_points(group=ENTRY_POINT_GROUP):
        if entry.name == name:
            return entry.load()
    return importlib.import_module(name)


def discover(m) -> list[str]:
    """Install every integration installed packages advertise."""
    return [
        integrate(m, entry.load())
        for entry in metadata.entry_points(group=ENTRY_POINT_GROUP)
    ]


# ----------------------------------------------------------------- operations


def module_ops(
    m,
    module: Any,
    names: Iterable[str] | None = None,
    *,
    prefix: str | None = None,
    rename: dict[str, str] | None = None,
    raw: bool = True,
    typed: bool = False,
) -> list[str]:
    """Selected callables of any module as MeTTa functions, in one call.

        petta.integrate.module_ops(m, math, ["sqrt", "floor", "gcd"])
        m.run("!(sqrt 16.0)")

    Underscores read as hyphens, a prefix namespaces the lot, and rename
    overrides per function. Callables only; anything else named raises.
    """
    if names is None:
        names = [
            n
            for n, v in vars(module).items()
            if not n.startswith("_") and callable(v) and not inspect.isclass(v)
        ]
    registered = []
    rename = rename or {}
    for pyname in names:
        fn = getattr(module, pyname)
        if not callable(fn):
            raise PettaError(f"{module.__name__}.{pyname} is not callable")
        metta_name = rename.get(pyname, pyname.replace("_", "-"))
        if prefix:
            metta_name = f"{prefix}{metta_name}"
        spread = False
        try:
            signature = inspect.signature(fn)
        except ValueError:
            # No introspectable signature (a C builtin): every call form is
            # plausible, so the common arities serve.
            spread = True
        else:
            # A variadic callable accepts every count, so the common
            # arities are all reachable; keyword-only refusals propagate,
            # since inventing forms for them would fail at call time.
            spread = any(
                p.kind is inspect.Parameter.VAR_POSITIONAL for p in signature.parameters.values()
            )
        if spread:
            m.register_op(
                _spread(fn),
                name=metta_name,
                raw=raw,
                typed=False,
                arities=[0, 1, 2, 3, 4],
            )
        else:
            m.register_op(fn, name=metta_name, raw=raw, typed=typed)
        registered.append(metta_name)
    return registered


def _spread(fn: Callable) -> Callable:
    def call(*args):
        return fn(*args)

    call.__name__ = getattr(fn, "__name__", "call")
    return call


def wrap_callable(m, name: str, target: Callable, *, arities: list[int] | None = None):
    """One callable, any callable, as a MeTTa function under a chosen name.

    The instance behind a bound method or a callable object crosses nothing:
    the closure holds it, so identity and state stay Python's. The served
    arities are the signature's own reachable positional counts; a callable
    whose signature cannot be inspected, or that is variadic, names its
    call forms with arities=[...] rather than being served invented ones.
    """
    if arities is None:
        try:
            signature = inspect.signature(target)
        except ValueError as exc:
            raise PettaError(
                f"{name}: the callable's signature is not inspectable, so "
                f"its call forms cannot be derived; pass arities=[...]"
            ) from exc
        positional = []
        variadic = False
        for parameter in signature.parameters.values():
            if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                variadic = True
            elif parameter.kind is inspect.Parameter.KEYWORD_ONLY and (
                parameter.default is inspect.Parameter.empty
            ):
                raise PettaError(
                    f"{name}: required keyword-only parameter "
                    f"{parameter.name!r} is unreachable from a positional "
                    f"MeTTa call site"
                )
            elif parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ):
                positional.append(parameter)
        required = sum(1 for p in positional if p.default is inspect.Parameter.empty)
        if variadic:
            # Every count is reachable through *args; serve the common ones.
            arities = list(range(required, max(required + 1, 5)))
        else:
            arities = list(range(required, len(positional) + 1))

    def call(*xs):
        return target(*xs)

    m.register_op(call, name=name, raw=True, typed=False, arities=arities)
    return target


def wrap_object(m, name: str, obj: Any, methods: dict[str, str] | Iterable[str]) -> Any:
    """An instance's methods as operations: (name-method args...).

        petta.integrate.wrap_object(m, "db", connection,
                                    {"execute": "db-query!", "close": "db-close!"})

    methods maps Python method names to MeTTa spellings, or lists names to
    mangle by the usual rule. A method returning None answers True, the
    engine's own convention for an effectful builtin, since a Python method
    returning None almost always is one. The object itself also lands in the
    space as (wrapped name <obj>), so rules can enumerate what is wrapped.
    """
    if not isinstance(methods, dict):
        methods = {name_: f"{name}-{name_.replace('_', '-')}" for name_ in methods}
    for method_name, metta_name in methods.items():
        bound = getattr(obj, method_name)
        wrap_callable(m, metta_name, _effect(bound))
    m.add(Expr([S.wrapped, Sym(name), val(obj)]))
    return obj


def _effect(fn: Callable) -> Callable:
    def call(*xs):
        result = fn(*xs)
        return True if result is None else result

    call.__name__ = getattr(fn, "__name__", "effect")
    return call


# --------------------------------------------------------------- value bridge

# The four-image translator is part of the integration surface; re-exported
# so an integration is written against one namespace.
register_type = convert.register_type


def register_object_type(predicate: Callable[[Any], bool], name: str) -> None:
    """A protocol as a type: objects satisfying predicate get name as an
    additional get-type candidate, beyond their own classes.

        register_object_type(lambda x: hasattr(x, "__dlpack__"), "DLTensor")
    """
    PROTOCOL_TYPES.append((predicate, name))


def register_repr(predicate: Callable[[Any], bool], formatter: Callable[[Any], str]) -> None:
    """How objects satisfying a protocol print when stored as atoms."""
    register_object_repr_protocol(predicate, formatter)


# ----------------------------------------------------------------- reflection

# (predicate, reflector) pairs: a reflector lowers one object's structure
# into facts. Libraries register theirs; reflect() dispatches.
_REFLECTORS: list[tuple[Callable[[Any], bool], Callable[[Any, str, Any], int]]] = []


def register_reflector(
    predicate: Callable[[Any], bool], fn: Callable[[Any, str, Any], int]
) -> None:
    """fn(m, name, obj) writes facts about obj into m and returns the count."""
    _REFLECTORS.append((predicate, fn))


def reflect(m, name: str, obj: Any) -> int:
    """Lower an object's structure into facts, by whichever reflector claims it."""
    for predicate, fn in _REFLECTORS:
        if predicate(obj):
            return fn(m, name, obj)
    raise PettaError(
        f"no reflector claims {type(obj).__name__}; register one with "
        f"petta.integrate.register_reflector"
    )


def facts(m, atoms: Iterable[Any]) -> int:
    """Bulk facts into a space; returns how many."""
    count = 0
    for a in atoms:
        m.add(encode(a) if not isinstance(a, Atom) else a)
        count += 1
    return count


# -------------------------------------------------- reasoning over any object


def install_reflection_ops(m) -> list[str]:
    """(py-attr $obj $name) and the two-mode (py-field $obj $name $?): the
    smallest thing that turns calling Python into reasoning about a Python
    object. With the field name bound, py-field is getattr; unbound, it
    enumerates the object's fields and yields (name value) pairs, one answer
    per field, which is the mode a function cannot offer and a relation can.
    """

    def py_attr(obj, name):
        target = decode(obj) if isinstance(obj, Gnd) else obj
        attr = name.name if isinstance(name, Sym) else str(decode(name))
        try:
            value = getattr(target, attr)
        except AttributeError:
            return None
        return val(value)

    def py_field(obj, name=None):
        target = decode(obj) if isinstance(obj, Gnd) else obj
        if name is not None and not isinstance(name, Var):
            attr = name.name if isinstance(name, Sym) else str(decode(name))
            try:
                value = getattr(target, attr)
            except AttributeError:
                return
            yield expr(Sym(attr), val(value))
            return
        for attr in _field_names(target):
            yield expr(Sym(attr), val(getattr(target, attr)))

    m.register_op(py_attr, name="py-attr", raw=False, typed=False, pass_atoms=True)
    m.register_op(py_field, name="py-field", raw=False, typed=False, pass_atoms=True)
    return ["py-attr", "py-field"]


def _field_names(obj: Any) -> list[str]:
    if dataclasses.is_dataclass(obj):
        return [f.name for f in dataclasses.fields(obj)]
    if hasattr(obj, "_fields"):
        return list(obj._fields)
    if hasattr(obj, "__dict__"):
        return [n for n in vars(obj) if not n.startswith("_")]
    if hasattr(obj, "__slots__"):
        return [n for n in obj.__slots__ if not n.startswith("_")]
    return []
