"""Purpose: the interface any Python library implements to work deeply with
PeTTa, and the toolkit that makes implementing it a page of code rather than
a project. An integration is a module with install_petta(m), an object with
name and install(m), or an entry point in the petta.integrations group; the
toolkit covers the capabilities an integration is made of: bulk operations
from a module, an instance's methods as operations, protocol-based typing
and printing, two-way value translation, structure reflected into facts,
spaces backed by the library's own storage, and reflective py-field
reasoning over any object.
Assumes:
  - inspect.signature reports unsupported callables with TypeError and
    unavailable signatures with ValueError [source 2026-08-14:
    https://docs.python.org/3/library/inspect.html#inspect.signature]
Guarantees:
  - protocol type, formatter, conversion, and reflector registrations have
    exact removal counterparts [tested
    test_protocol_and_reflector_registrations_can_be_removed,
    test_type_registration_can_be_removed_and_its_name_reclaimed]
  - installation idempotence ends with the lifetime of its space [tested
    test_dropped_space_name_reinstalls_integrations]
Owns:
  - _INSTALLED retains one target per live space and integration name;
    MeTTa.drop releases every record for that space [tested
    test_dropped_space_name_reinstalls_integrations]
Guarded by:
  - _INSTALLED_LOCK serializes integration installation and invalidation
    [tested test_dropped_space_name_reinstalls_integrations]
  - _REFLECTOR_LOCK protects reflector registrations [tested
    test_protocol_and_reflector_registrations_can_be_removed]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import threading
from collections.abc import Callable, Iterable
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from . import convert
from ._ops import register_protocol_type, unregister_protocol_type
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
    unregister_object_repr_protocol,
    val,
)
from .errors import PettaError
from .foreign import SpaceProvider

__all__ = [
    "ENTRY_POINT_GROUP",
    "LIBRARIES_GROUP",
    "SPACES_GROUP",
    "Integration",
    "SpaceProvider",
    "discover",
    "entry_points",
    "facts",
    "install_reflection_ops",
    "installed",
    "integrate",
    "load_entry_point",
    "module_ops",
    "reflect",
    "register_object_type",
    "register_reflector",
    "register_type",
    "unregister_object_type",
    "unregister_reflector",
    "unregister_repr",
    "unregister_type",
    "wrap_callable",
    "wrap_object",
]

ENTRY_POINT_GROUP = "petta.integrations"

#: The provider ecosystem's groups, pytest11's and SQLAlchemy dialects'
#: precedent: a third-party package advertises a provider factory under
#: petta.spaces, or the directory of MeTTa/Prolog sources it ships under
#: petta.libraries, and the app loads by NAME. Nothing auto-registers on
#: import; discovery answers names, and registration stays the app's
#: explicit call, which is the control the engine's backends/*.pl door
#: keeps on its side of the seam.
SPACES_GROUP = "petta.spaces"
LIBRARIES_GROUP = "petta.libraries"


@runtime_checkable
class Integration(Protocol):
    """What integrate() accepts beyond a module: a name and an installer."""

    name: str

    def install(self, m) -> None: ...


_INSTALLED: dict[tuple[str, str], Any] = {}
_INSTALLED_LOCK = threading.RLock()


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
    elif hasattr(target, "PETTA_PROLOG"):
        name = getattr(target, "__name__", type(target).__name__)
        installer = _prolog_installer(target)
    else:
        raise PettaError(
            f"{target!r} is not an integration: define install_petta(m), or "
            f"PETTA_PROLOG naming the .pl files your package ships, or "
            f"provide an object with .name and .install(m)"
        )
    key = (m.space_name, name)
    with _INSTALLED_LOCK:
        if key not in _INSTALLED:
            installer(m)
            _INSTALLED[key] = target
    return name


def _prolog_installer(target: Any) -> Callable:
    """The installer for a package that ships Prolog and no Python setup.

    A native library still had to hand-write an install() that hardcoded a
    __file__-relative path to its .pl, which is what lib/minimal_metta_lib.py
    does, so the standard plugin mechanism carried no Prolog at all. Name the
    files instead:

        PETTA_PROLOG = ["fast.pl"]        # beside the module

    Each file declares its own exports with :- metta_export, so there is no
    name list here either: the package says which files, the files say which
    names, and `pip install` is the whole of the wiring.
    """
    package = Path(inspect.getfile(target)).resolve().parent
    files = [package / name for name in target.PETTA_PROLOG]

    def install(m) -> None:
        alias = getattr(target, "__name__", "petta_integration").rsplit(".", 1)[-1]
        m.register_library_path(package, alias)
        for path in files:
            m.register_prolog(path=path)

    return install


def installed() -> dict[tuple[str, str], Any]:
    """(space, integration name) -> the installed target."""
    with _INSTALLED_LOCK:
        return _INSTALLED.copy()


def _forget_space(space: str) -> None:
    """Forget installations whose per-space state was dropped."""
    with _INSTALLED_LOCK:
        for key in [key for key in _INSTALLED if key[0] == space]:
            del _INSTALLED[key]


def _resolve(name: str) -> Any:
    for entry in metadata.entry_points(group=ENTRY_POINT_GROUP):
        if entry.name == name:
            return entry.load()
    return importlib.import_module(name)


def entry_points(group: str = SPACES_GROUP) -> dict[str, metadata.EntryPoint]:
    """The names installed packages advertise for one group, UNLOADED:
    asking imports nothing and registers nothing, so discovery is free to
    call and the app keeps deciding what loads.
    """
    return {entry.name: entry for entry in metadata.entry_points(group=group)}


def load_entry_point(name: str, /, *args: Any, group: str = SPACES_GROUP, **kwargs: Any) -> Any:
    """Load one advertised entry point by name, calling a callable target
    with the given arguments, the factory contract:

        m.register_space(integrate.load_entry_point("duck"), "&duck")
        m.register_library_path(
            integrate.load_entry_point("nars", group=integrate.LIBRARIES_GROUP),
            "nars",
        )

    A petta.spaces target is a provider class or factory; a
    petta.libraries target answers the directory of sources the package
    ships. A non-callable target answers as-is, the module-level-instance
    form, and refuses arguments it cannot take. An unknown name refuses,
    listing what IS installed, so a typo reads as one.
    """
    advertised = entry_points(group)
    if name not in advertised:
        known = ", ".join(sorted(advertised)) or "none"
        raise PettaError(
            f"no {group} entry point named {name!r}; installed: {known}"
        )
    target = advertised[name].load()
    if callable(target):
        return target(*args, **kwargs)
    if args or kwargs:
        raise PettaError(
            f"the {group} entry point {name!r} is not callable, "
            f"but arguments were given"
        )
    return target


def discover(m) -> list[str]:
    """Install every integration installed packages advertise."""
    return [
        integrate(m, entry.load())
        for entry in metadata.entry_points(group=ENTRY_POINT_GROUP)
    ]


# ----------------------------------------------------------------- operations


def _module_callable_names(module: Any) -> list[str]:
    return [
        name
        for name, value in vars(module).items()
        if not name.startswith("_") and callable(value) and not inspect.isclass(value)
    ]


def _require_callable(module: Any, pyname: str) -> Callable:
    target = getattr(module, pyname)
    if not callable(target):
        raise PettaError(f"{module.__name__}.{pyname} is not callable")
    return target


def _operation_name(pyname: str, prefix: str | None, rename: dict[str, str]) -> str:
    name = rename.get(pyname, pyname)
    return f"{prefix}{name}" if prefix else name


def _spreads_positional_calls(target: Callable) -> bool:
    """Whether module_ops must expose the conventional zero-to-four arities."""
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        # A C callable or unsupported callable type has no trustworthy
        # signature. The bulk helper serves its conventional common arities.
        return True
    return any(
        parameter.kind is inspect.Parameter.VAR_POSITIONAL
        for parameter in signature.parameters.values()
    )


def _register_module_callable(
    m: Any,
    target: Callable,
    name: str,
    *,
    raw: bool,
    typed: bool,
) -> None:
    if _spreads_positional_calls(target):
        m.register_op(
            _spread(target),
            name=name,
            raw=raw,
            typed=False,
            arities=[0, 1, 2, 3, 4],
        )
        return
    m.register_op(target, name=name, raw=raw, typed=typed)


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
        names = _module_callable_names(module)
    registered = []
    rename = rename or {}
    for pyname in names:
        target = _require_callable(module, pyname)
        metta_name = _operation_name(pyname, prefix, rename)
        _register_module_callable(m, target, metta_name, raw=raw, typed=typed)
        registered.append(metta_name)
    return registered


def _spread(fn: Callable) -> Callable:
    def call(*args):
        return fn(*args)

    call.__name__ = getattr(fn, "__name__", "call")
    return call


def _callable_arities(name: str, target: Callable) -> list[int]:
    """Derive every reachable positional arity from one callable signature."""
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError) as exc:
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
    required = sum(1 for parameter in positional if parameter.default is inspect.Parameter.empty)
    if variadic:
        return list(range(required, max(required + 1, 5)))
    return list(range(required, len(positional) + 1))


def wrap_callable(m, name: str, target: Callable, *, arities: list[int] | None = None):
    """One callable, any callable, as a MeTTa function under a chosen name.

    The instance behind a bound method or a callable object crosses nothing:
    the closure holds it, so identity and state stay Python's. The served
    arities are the signature's own reachable positional counts; a callable
    whose signature cannot be inspected, or that is variadic, names its
    call forms with arities=[...] rather than being served invented ones.
    """
    if arities is None:
        arities = _callable_arities(name, target)

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
unregister_type = convert.unregister_type


def register_object_type(predicate: Callable[[Any], bool], name: str) -> None:
    """A protocol as a type: objects satisfying predicate get name as an
    additional get-type candidate, beyond their own classes.

        register_object_type(lambda x: hasattr(x, "__dlpack__"), "DLTensor")
    """
    register_protocol_type(predicate, name)


def unregister_object_type(predicate: Callable[[Any], bool], name: str) -> None:
    """Remove the latest exact protocol type registration."""
    unregister_protocol_type(predicate, name)


def register_repr(predicate: Callable[[Any], bool], formatter: Callable[[Any], str]) -> None:
    """How objects satisfying a protocol print when stored as atoms."""
    register_object_repr_protocol(predicate, formatter)


def unregister_repr(
    predicate: Callable[[Any], bool], formatter: Callable[[Any], str]
) -> None:
    """Remove the latest exact protocol formatter registration."""
    unregister_object_repr_protocol(predicate, formatter)


# ----------------------------------------------------------------- reflection

# (predicate, reflector) pairs: a reflector lowers one object's structure
# into facts. Libraries register theirs; reflect() dispatches.
_REFLECTORS: list[tuple[Callable[[Any], bool], Callable[[Any, str, Any], int]]] = []
_REFLECTOR_LOCK = threading.RLock()


def register_reflector(
    predicate: Callable[[Any], bool], fn: Callable[[Any, str, Any], int]
) -> None:
    """fn(m, name, obj) writes facts about obj into m and returns the count."""
    with _REFLECTOR_LOCK:
        _REFLECTORS.append((predicate, fn))


def unregister_reflector(
    predicate: Callable[[Any], bool], fn: Callable[[Any, str, Any], int]
) -> None:
    """Remove the latest reflector matching both callables exactly."""
    with _REFLECTOR_LOCK:
        for index in range(len(_REFLECTORS) - 1, -1, -1):
            registered_predicate, registered_fn = _REFLECTORS[index]
            if registered_predicate is predicate and registered_fn is fn:
                _REFLECTORS.pop(index)
                return
    raise KeyError("no reflector is registered for those exact callables")


def reflect(m, name: str, obj: Any) -> int:
    """Lower an object's structure into facts, by whichever reflector claims it."""
    with _REFLECTOR_LOCK:
        registrations = tuple(_REFLECTORS)
    for predicate, fn in registrations:
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
