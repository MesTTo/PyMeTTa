"""Purpose: the interface any Python library implements to work deeply with
MeTTa, and the toolkit that makes implementing it a page of code rather than
a project. An integration is a module with install_metta(m), an object with
name and install(m), or an entry point in the metta.integrations group; the
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
  - protocol registrations accept literal or computed type atoms, with
    expression terms preserved across the engine bridge and callable removal
    selected by identity [tested: test_computed_protocol_types_are_live_and_removable,
    test_computed_protocol_removal_uses_provider_identity; commit=4eaefdd8d40e53b2613722287302a14b41704662]
  - protocol type, formatter, conversion, and reflector registrations have
    exact removal counterparts [tested
    test_protocol_and_reflector_registrations_can_be_removed,
    test_type_registration_can_be_removed_and_its_name_reclaimed]
  - a failed installer restores operations and their declaration ownership,
    protocol types, protocol reprs, reflectors, converted types, atoms written
    to native spaces or transactional providers, library-path facts, dynamic
    Prolog extension registrations, and nested installation receipts [tested
    test_a_failed_integration_unwinds_every_framework_registration,
    test_a_failed_outer_installation_unwinds_its_completed_dependency]
  - a best-effort home space is refused before its installer runs, because its
    declared writes can survive rollback [tested
    test_an_integration_refuses_a_best_effort_home_before_installing]
  - a started installer's original failure names the effects no transaction
    can safely reverse, and declarative Prolog integrations also name every
    source file that may remain consulted [tested
    test_a_failed_prolog_integration_names_its_possible_source_residue]
  - installation idempotence ends with the lifetime of its space [tested
    test_dropped_space_name_reinstalls_integrations]
  - an installer is handed a SPACE whichever of the two the caller holds, so
    integrate(context, target) installs into that context's home space
    [tested: test_an_integration_installed_on_a_context_reaches_its_home_space]
  - discovery refuses duplicate names, missing dependencies, and named
    dependency cycles, and installs acyclic entries in topological order
    [tested: test_each_remaining_annotation_shape_refuses_or_carries;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - module and reflection helpers express transport and Atom delivery without
    boolean registration pairs [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - callable wrappers require a host-effect classification, and object
    wrappers require one class per method [tested:
    test_wrap_object_methods_with_effect_convention; commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - Prolog-only integrations register their directories under the module's
    fully qualified name, so distinct dotted modules cannot silently share
    one ordered SWI search alias [tested:
    test_prolog_integration_aliases_keep_fully_qualified_module_names,
    test_an_explicitly_shared_library_alias_keeps_all_directories;
    commit=a6681e54ded570684ba0e2969f2893ae016a841a]
Owns:
  - _INSTALLED retains one target per live space and integration name;
    MeTTa.drop releases every record for that space and a containing
    transaction rollback releases completed nested installations [tested
    test_dropped_space_name_reinstalls_integrations,
    test_a_failed_outer_installation_unwinds_its_completed_dependency]
Guarded by:
  - _INSTALLED_LOCK serializes integration installation and invalidation
    [tested test_dropped_space_name_reinstalls_integrations]
  - _REFLECTOR_LOCK protects reflector registrations [tested
    test_protocol_and_reflector_registrations_can_be_removed]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import graphlib
import importlib
import inspect
import threading
from collections.abc import Callable, Iterable, Mapping
from importlib import metadata
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from . import _atoms_core as _atom_registry
from . import _convert_registry as _type_registry
from . import _ops as _operation_registry
from . import convert, seam
from ._api_types import space_of as _space_of
from ._object_fields import field_names as _field_names
from .atoms import (
    Atom,
    Expression,
    Grounded,
    S,
    Symbol,
    Variable,
    _decode,
    _encode,
    _expr,
    ground,
)
from .errors import MettaError
from .foreign import SpaceProvider
from .ops import _record_registry_undo
from .vocabularies import EffectClass

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
    "register_repr",
    "register_type",
    "space_of",
    "unregister_object_type",
    "unregister_reflector",
    "unregister_repr",
    "unregister_type",
    "wrap_callable",
    "wrap_object",
]

ENTRY_POINT_GROUP = "metta.integrations"

#: The provider ecosystem's groups, pytest11's and SQLAlchemy dialects'
#: precedent: a third-party package advertises a provider factory under
#: metta.spaces, or the directory of MeTTa/Prolog sources it ships under
#: metta.libraries, and the app loads by NAME. Nothing auto-registers on
#: import; discovery answers names, and registration stays the app's
#: explicit call, which is the control the engine's extensions/*.pl loader
#: keeps on its side of the extension-loading boundary.
SPACES_GROUP = "metta.spaces"
LIBRARIES_GROUP = "metta.libraries"


@runtime_checkable
class Integration(Protocol):
    """What integrate() accepts beyond a module: a name and an installer."""

    name: str

    def install(self, m) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


_INSTALLED: dict[tuple[str, str], Any] = {}
_INSTALLED_LOCK = threading.RLock()


def space_of(m: Any) -> Any:
    """The space a door works in, given a context or a space.

    An installer is handed a SPACE, because "equations and facts an installer
    writes land in the space it was handed" is what makes integrate()
    idempotent per space. What a caller holds is usually a context, and MeTTa
    refuses a Space door rather than forwarding it, deliberately, so an
    installer written the natural way failed on the first storage door it
    reached: `metta.arrays.install(m)` raised `MeTTa has no 'is_function'`
    with every array operation left unregistered.

    Resolving once, at the door, is what lets `install(m)` work without
    erasing the distinction the two classes draw, because the installer still
    receives a space. A context is exactly the object that has a home space to
    give; a space has none, and answers for itself. This is the public
    spelling; every door in the library resolves the same way.
    """
    return _space_of(m)


def integrate(m, target: Any) -> str:
    """Install an integration on a space, idempotently per (space, name).

    target may be: a module (or dotted module name) defining install_metta(m),
    an Integration object, or the name of an installed package's entry point
    in the metta.integrations group. Returns the integration's name.

    m may be a context or a space; the installer is handed the space either
    way, which is the object whose storage doors it needs.

    Idempotence is per SPACE, because equations and facts an installer writes
    land in the space it was handed: installing into a second space installs
    again there. Operations are process-wide either way, and re-registering
    them is the registry's ordinary replacement.

    Installation is one unit of work. A failure restores engine state and each
    framework-owned Python registry to the state before this call. A home space
    declaring best-effort writes is refused before the installer runs because
    those writes explicitly survive rollback.

    Source consultation, native-library loading, custom listener effects, and
    arbitrary process-global side effects have no general safe inverse. The
    original installer exception carries that boundary as a note; a
    METTA_PROLOG integration also names every source path that may remain
    consulted.
    """
    if isinstance(target, str):
        target = _resolve(target)
    if isinstance(target, Integration):
        name, installer = target.name, target.install
    elif hasattr(target, "install_metta"):
        name = getattr(target, "__name__", type(target).__name__)
        installer = target.install_metta
    elif hasattr(target, "METTA_PROLOG"):
        name = getattr(target, "__name__", type(target).__name__)
        installer = _prolog_installer(target)
    else:
        msg = (
            f"{target!r} is not an integration: define install_metta(m), or "
            f"METTA_PROLOG naming the .pl files your package ships, or "
            f"provide an object with .name and .install(m)"
        )
        raise MettaError(
            msg
        )
    space = space_of(m)
    key = (space.name, name)
    with _INSTALLED_LOCK:
        if key in _INSTALLED:
            return name
        started = False

        def install() -> None:
            nonlocal started
            _require_transactional_home(space, name)
            started = True
            installer(space)
            _record_registry_undo(
                lambda: _restore_installation_receipt(key, target),
                description=f"installation receipt {key!r}",
            )
            _INSTALLED[key] = target

        try:
            space.transaction(install)
        except BaseException as error:
            if started:
                _annotate_irreversible_residue(error, name, installer)
            raise
    return name


def _require_transactional_home(space: Any, name: str) -> None:
    """Refuse a home whose own contract permits writes to survive rollback."""
    row = space.runtime.once(
        "metta_writes(Space, Atomicity)",
        Space=space.name,
    )
    if row is None or row.get("Atomicity") != "best-effort":
        return
    msg = (
        f"cannot install integration {name!r} into {space.name}: the space "
        "declares best-effort writes, so a failed installer could leave atoms "
        "behind; use a native or transactional home space"
    )
    raise MettaError(msg)


def _restore_installation_receipt(key: tuple[str, str], target: Any) -> None:
    """Remove one receipt created by a completed nested installation."""
    with _INSTALLED_LOCK:
        current = _INSTALLED.get(key)
        if current is target:
            del _INSTALLED[key]
        elif current is not None:
            msg = f"installation receipt {key!r} was replaced before rollback"
            raise RuntimeError(msg)


def _annotate_irreversible_residue(
    error: BaseException,
    name: str,
    installer: Callable,
) -> None:
    """State the process effects the framework cannot promise to reverse."""
    BaseException.add_note(
        error,
        f"integration {name!r} failed after its installer started; "
        "framework-managed registrations and transactional writes were "
        "enrolled for rollback, but consulted Prolog source, loaded native "
        "libraries, custom registration-listener effects, and other "
        "process-global side effects cannot be unwound automatically and may remain"
    )
    files = (
        installer.__dict__.get("_metta_prolog_files", ())
        if inspect.isfunction(installer)
        else ()
    )
    if files:
        paths = ", ".join(str(path) for path in files)
        BaseException.add_note(
            error,
            f"Prolog source declared by integration {name!r} may remain "
            f"consulted: {paths}"
        )


def _prolog_installer(target: Any) -> Callable:
    """The installer for a package that ships Prolog and no Python setup.

    A native library still had to hand-write an install() that hardcoded a
    __file__-relative path to its .pl, which is what lib/minimal_metta_lib/minimal_metta_lib.py
    does, so the standard plugin mechanism carried no Prolog at all. Name the
    files instead:

        METTA_PROLOG = ["fast.pl"]        # beside the module

    Each file declares its own exports with :- metta_export, so there is no
    name list here either: the package says which files, the files say which
    names, and `pip install` is the whole of the wiring.
    """
    package = Path(inspect.getfile(target)).resolve().parent
    files = [package / name for name in target.METTA_PROLOG]

    def install(m) -> None:
        alias = getattr(target, "__name__", "metta_integration")
        m.register_library_path(package, alias)
        for path in files:
            m.register_prolog(path=path)

    install.__dict__["_metta_prolog_files"] = tuple(files)
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
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return {entry.name: entry for entry in metadata.entry_points(group=group)}


def load_entry_point(name: str, /, *args: Any, group: str = SPACES_GROUP, **kwargs: Any) -> Any:
    """Load one advertised entry point by name, calling a callable target
    with the given arguments, the factory contract:

        m._register_space(integrate.load_entry_point("duck"), "&duck")
        m.register_library_path(
            integrate.load_entry_point("nars", group=integrate.LIBRARIES_GROUP),
            "nars",
        )

    A metta.spaces target is a provider class or factory; a
    metta.libraries target answers the directory of sources the package
    ships. A non-callable target answers as-is, the module-level-instance
    form, and refuses arguments it cannot take. An unknown name refuses,
    listing what IS installed, so a typo reads as one.
    """  # noqa: D205, D415  -- the API contract is one continuous invariant, not summary-and-body prose; the first line deliberately introduces the indented example that follows
    advertised = entry_points(group)
    if name not in advertised:
        known = ", ".join(sorted(advertised)) or "none"
        msg = f"no {group} entry point named {name!r}; installed: {known}"
        raise MettaError(
            msg
        )
    target = advertised[name].load()
    if callable(target):
        return target(*args, **kwargs)
    if args or kwargs:
        msg = (
            f"the {group} entry point {name!r} is not callable, "
            f"but arguments were given"
        )
        raise MettaError(
            msg
        )
    return target


def discover(m) -> list[str]:
    """Install advertised integrations after satisfying METTA_REQUIRES."""
    advertised = tuple(metadata.entry_points(group=ENTRY_POINT_GROUP))
    entries: dict[str, Any] = {}
    for entry in advertised:
        if entry.name in entries:
            msg = (
                f"duplicate {ENTRY_POINT_GROUP} entry point {entry.name!r}; "
                "integration names must be unique"
            )
            raise MettaError(msg)
        entries[entry.name] = entry
    targets = {name: entry.load() for name, entry in entries.items()}

    graph: dict[str, tuple[str, ...]] = {}
    for name, target in targets.items():
        raw = getattr(target, "METTA_REQUIRES", ())
        if isinstance(raw, str) or not isinstance(raw, Iterable):
            msg = (
                f"integration {name!r} METTA_REQUIRES must be an iterable "
                "of entry-point names"
            )
            raise MettaError(msg)
        dependencies = tuple(raw)
        invalid = [item for item in dependencies if not isinstance(item, str)]
        if invalid:
            msg = f"integration {name!r} METTA_REQUIRES contains a non-string name"
            raise MettaError(msg)
        missing = sorted(set(dependencies) - targets.keys())
        if missing:
            msg = (
                f"integration {name!r} requires missing integration(s): "
                f"{', '.join(missing)}"
            )
            raise MettaError(msg)
        graph[name] = dependencies

    try:
        order = tuple(graphlib.TopologicalSorter(graph).static_order())
    except graphlib.CycleError as exc:
        cycle = " -> ".join(exc.args[1])
        msg = f"integration dependency cycle: {cycle}"
        raise MettaError(msg) from exc
    return [integrate(m, targets[name]) for name in order]


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
        msg = f"{module.__name__}.{pyname} is not callable"
        raise MettaError(msg)
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
    effect: EffectClass | str,
    # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
    transport: Literal["encoded", "raw"],
) -> None:
    if _spreads_positional_calls(target):
        m.op(
            _spread(target),
            name=name,
            effect=effect,
            transport=transport,
            arities=[0, 1, 2, 3, 4],
        )
        return
    m.op(target, name=name, effect=effect, transport=transport)


def module_ops(
    m,
    module: Any,
    names: Iterable[str] | None = None,
    *,
    effect: EffectClass | str,
    prefix: str | None = None,
    rename: dict[str, str] | None = None,
    # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
    transport: Literal["encoded", "raw"] = "raw",
) -> list[str]:
    """Selected callables of any module as MeTTa functions, in one call.

        metta.integrate.module_ops(
            m, math, ["sqrt", "floor", "gcd"], effect="pureStructural"
        )
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
        _register_module_callable(
            m, target, metta_name, effect=effect, transport=transport
        )
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
        msg = (
            f"{name}: the callable's signature is not inspectable, so "
            f"its call forms cannot be derived; pass arities=[...]"
        )
        raise MettaError(
            msg
        ) from exc
    positional = []
    variadic = False
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            variadic = True
        elif parameter.kind is inspect.Parameter.KEYWORD_ONLY and (
            parameter.default is inspect.Parameter.empty
        ):
            msg = (
                f"{name}: required keyword-only parameter "
                f"{parameter.name!r} is unreachable from a positional "
                f"MeTTa call site"
            )
            raise MettaError(
                msg
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


def wrap_callable(
    m,
    name: str,
    target: Callable,
    *,
    effect: EffectClass | str,
    arities: list[int] | None = None,
):
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

    m.op(call, name=name, effect=effect, transport="raw", arities=arities)
    return target


def wrap_object(
    m,
    name: str,
    obj: Any,
    methods: dict[str, str] | Iterable[str],
    *,
    effects: Mapping[str, EffectClass | str],
) -> Any:
    """An instance's methods as operations: (name-method args...).

        metta.integrate.wrap_object(m, "db", connection,
                                    {"execute": "db-query!", "close": "db-close!"},
                                    effects={"execute": "oracleIO", "close": "oracleIO"})

    methods maps Python method names to MeTTa spellings, or lists names to
    mangle by the usual rule. A method returning None answers True, the
    engine's own convention for an effectful builtin, since a Python method
    returning None almost always is one. The object itself also lands in the
    space as (wrapped name <obj>), so rules can enumerate what is wrapped.
    """
    if not isinstance(methods, dict):
        methods = {name_: f"{name}-{name_.replace('_', '-')}" for name_ in methods}
    method_names = set(methods)
    missing = sorted(method_names - effects.keys())
    extra = sorted(effects.keys() - method_names)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unknown {extra}")
        raise MettaError(
            "wrap_object effects must classify exactly the wrapped methods: "
            + "; ".join(details)
        )
    for method_name, metta_name in methods.items():
        bound = getattr(obj, method_name)
        wrap_callable(m, metta_name, _effect(bound), effect=effects[method_name])
    m.add(Expression([S.wrapped, Symbol(name), ground(obj)]))
    return obj


def _effect(fn: Callable) -> Callable:
    def call(*xs):
        result = fn(*xs)
        return True if result is None else result

    call.__name__ = getattr(fn, "__name__", "effect")
    return call


# --------------------------------------------------------------- value bridge


def _append_registry_entry(
    registry: list[tuple[Any, Any]],
    lock: Any,
    entry: tuple[Any, Any],
    description: str,
) -> None:
    """Append one ordered registration and enlist its identity-exact inverse."""

    def undo() -> None:
        with lock:
            for index in range(len(registry) - 1, -1, -1):
                if registry[index] is entry:
                    registry.pop(index)
                    return

    _record_registry_undo(undo, description=description)
    with lock:
        registry.append(entry)


def _remove_registry_entry(
    registry: list[tuple[Any, Any]],
    lock: Any,
    matches: Callable[[tuple[Any, Any]], bool],
    *,
    missing: str,
    description: str,
) -> None:
    """Remove the latest match and enlist restoration at its exact precedence."""
    with lock:
        for index in range(len(registry) - 1, -1, -1):
            if matches(registry[index]):
                entry = registry[index]
                break
        else:
            raise KeyError(missing)

        def undo() -> None:
            with lock:
                if any(candidate is entry for candidate in registry):
                    return
                if index > len(registry):
                    msg = (
                        f"cannot restore {description} at index {index}; "
                        f"registry now has {len(registry)} entries"
                    )
                    raise RuntimeError(msg)
                registry.insert(index, entry)

        _record_registry_undo(undo, description=description)
        registry.pop(index)


def _type_registration(cls: type) -> Any:
    """Read one exact converted-type registration, without MRO fallback."""
    with _type_registry._REGISTRY_LOCK:
        return _type_registry._REGISTRY.get(cls)


def _restore_type_registration(cls: type, previous: Any, expected: Any) -> None:
    """Restore converter maps silently; the engine transaction restores listeners."""
    with _type_registry._REGISTRY_LOCK:
        current = _type_registry._REGISTRY.get(cls)
        if current is previous:
            return
        if current is not expected:
            msg = (
                f"converted type {cls.__qualname__} changed again before rollback"
            )
            raise RuntimeError(msg)
        _type_registry._discard_old_constructor(cls, current)
        if (
            current is not None
            and _type_registry._TYPE_OWNERS.get(current.type_name) is cls
        ):
            del _type_registry._TYPE_OWNERS[current.type_name]
        _type_registry._REGISTRY.pop(cls, None)
        if previous is not None:
            _type_registry._record_registration_locked(cls, previous)


def _enlist_type_preimage(cls: type) -> list[Any]:
    """Enlist before mutation so a failing registration listener also unwinds."""
    previous = _type_registration(cls)
    expected = [previous]
    _record_registry_undo(
        lambda: _restore_type_registration(cls, previous, expected[0]),
        description=f"converted type registration {cls.__qualname__!r}",
    )
    return expected


def register_type(
    cls: type,
    *,
    image: str | None = None,
    to_atom: Callable[[Any], Any] | None = None,
    from_atom: Callable[..., Any] | None = None,
    name: str | None = None,
    fields: tuple[str, ...] = (),
) -> type:
    """Register a converted type, enlisted in an enclosing transaction.

    `image` defaults to None rather than to a literal, so that a bare call
    reaches convert.register_type's derivation from the class shape. Passing
    "expression" here on its behalf was enough to defeat it, and an Enum, a
    dataclass or a NamedTuple registered through this door then lost the
    projection it already had.
    """
    expected = _enlist_type_preimage(cls)
    try:
        return convert.register_type(
            cls,
            image=image,
            to_atom=to_atom,
            from_atom=from_atom,
            name=name,
            fields=fields,
        )
    finally:
        expected[0] = _type_registration(cls)


def unregister_type(cls: type) -> None:
    """Remove one converted type, restoring its exact preimage on rollback."""
    expected = _enlist_type_preimage(cls)
    try:
        convert.unregister_type(cls)
    finally:
        expected[0] = _type_registration(cls)


def register_object_type(
    predicate: Callable[[Any], bool], name: str | Atom | Callable[[Any], Atom]
) -> None:
    """A protocol as a type: objects satisfying predicate get name as an
    additional get-type candidate, beyond their own classes. A type Atom
    carries structure; a callable computes a type Atom from the live value
    every time the engine reads its type.

        register_object_type(lambda x: hasattr(x, "__dlpack__"), "DLTensor")
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    _append_registry_entry(
        _operation_registry.PROTOCOL_TYPES,
        _operation_registry._PROTOCOL_TYPES_LOCK,
        (predicate, name),
        f"object type protocol {name!r}",
    )


def unregister_object_type(
    predicate: Callable[[Any], bool], name: str | Atom | Callable[[Any], Atom]
) -> None:
    """Remove the latest exact protocol type registration."""
    _remove_registry_entry(
        _operation_registry.PROTOCOL_TYPES,
        _operation_registry._PROTOCOL_TYPES_LOCK,
        lambda entry: entry[0] is predicate and (
            entry[1] is name
            or (isinstance(name, (str, Atom)) and entry[1] == name)
        ),
        missing=f"no object type protocol {name!r} uses that predicate",
        description=f"object type protocol {name!r}",
    )


def register_repr(predicate: Callable[[Any], bool], formatter: Callable[[Any], str]) -> None:
    """How objects satisfying a protocol print when stored as atoms."""
    _append_registry_entry(
        _atom_registry._PROTOCOL_REPRS,
        _atom_registry._STATE_LOCK,
        (predicate, formatter),
        "protocol repr registration",
    )


def unregister_repr(
    predicate: Callable[[Any], bool], formatter: Callable[[Any], str]
) -> None:
    """Remove the latest exact protocol formatter registration."""
    _remove_registry_entry(
        _atom_registry._PROTOCOL_REPRS,
        _atom_registry._STATE_LOCK,
        lambda entry: entry[0] is predicate and entry[1] is formatter,
        missing="no protocol repr is registered for those exact callables",
        description="protocol repr registration",
    )


# ----------------------------------------------------------------- reflection

# (predicate, reflector) pairs: a reflector lowers one object's structure
# into facts. Libraries register theirs; reflect() dispatches.
_REFLECTORS: list[tuple[Callable[[Any], bool], Callable[[Any, str, Any], int]]] = []
_REFLECTOR_LOCK = threading.RLock()


def register_reflector(
    predicate: Callable[[Any], bool], fn: Callable[[Any, str, Any], int]
) -> None:
    """fn(m, name, obj) writes facts about obj into m and returns the count."""
    _append_registry_entry(
        _REFLECTORS,
        _REFLECTOR_LOCK,
        (predicate, fn),
        "reflector registration",
    )


def unregister_reflector(
    predicate: Callable[[Any], bool], fn: Callable[[Any, str, Any], int]
) -> None:
    """Remove the latest reflector matching both callables exactly."""
    _remove_registry_entry(
        _REFLECTORS,
        _REFLECTOR_LOCK,
        lambda entry: entry[0] is predicate and entry[1] is fn,
        missing="no reflector is registered for those exact callables",
        description="reflector registration",
    )


def reflect(m, name: str, obj: Any) -> int:
    """Lower an object's structure into facts, by whichever reflector claims it."""
    with _REFLECTOR_LOCK:
        registrations = tuple(_REFLECTORS)
    for predicate, fn in registrations:
        if predicate(obj):
            return fn(m, name, obj)
    msg = (
        f"no reflector claims {type(obj).__name__}; register one with "
        f"metta.integrate.register_reflector"
    )
    raise MettaError(
        msg
    )


def facts(m, atoms: Iterable[Any]) -> int:
    """Bulk facts into a space; returns how many."""
    count = 0
    for a in atoms:
        m.add(_encode(a) if not isinstance(a, Atom) else a)
        count += 1
    return count


# -------------------------------------------------- reasoning over any object


def install_reflection_ops(m) -> list[str]:
    """(py-attr $obj $name) and the two-mode (py-field $obj $name $?): the
    smallest thing that turns calling Python into reasoning about a Python
    object. With the field name bound, py-field is getattr; unbound, it
    enumerates the object's fields and yields (name value) pairs, one answer
    per field, which is the mode a function cannot offer and a relation can.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def py_attr(obj, name):
        target = _decode(obj) if isinstance(obj, Grounded) else obj
        attr = name.name if isinstance(name, Symbol) else str(_decode(name))
        try:
            value = getattr(target, attr)
        except AttributeError:
            return None
        return ground(value)

    def py_field(obj, name=None):
        target = _decode(obj) if isinstance(obj, Grounded) else obj
        if name is not None and not isinstance(name, Variable):
            attr = name.name if isinstance(name, Symbol) else str(_decode(name))
            try:
                value = getattr(target, attr)
            except AttributeError:
                return
            yield _expr(Symbol(attr), ground(value))
            return
        for attr in _field_names(target):
            yield _expr(Symbol(attr), ground(getattr(target, attr)))

    m.op(
        py_attr,
        name="py-attr",
        effect="oracleIO",
        declarations=[_expr(S.arguments, S["py-attr"], S.atoms)],
    )
    m.op(
        py_field,
        name="py-field",
        effect="oracleIO",
        declarations=[_expr(S.arguments, S["py-field"], S.atoms)],
    )
    return ["py-attr", "py-field"]


# ------------------------------------------------ this module's seam points
#
# The six points below are the doors this module already had. Their rows live
# where they always lived, so nothing about a hot lookup or a transactional
# rollback changes; what the seam adds is that they are DECLARED, so "what can
# I extend here" is one query and one door registers against any of them. This
# is exactly what ext_points.pl does for a Prolog seam whose clauses Prolog's
# own database holds.
#
# They are declared HERE rather than in metta.seam because their readers and
# adders are this module's own: metta.seam is below metta.errors in the
# layering and a seam that imported this one would drag the base layer up the
# stack with it. metta.seam names this module in its _DECLARING list and
# imports it lazily when a caller asks for a point it does not already hold,
# so the cheap path stays cheap and `seam.points()` still answers all of them.


def _type_rows() -> list[seam.Row]:
    return [
        seam.Row(
            "type",
            registration.type_name,
            {"type": cls, "image": registration.image, "parts": registration.fields},
            "package",
        )
        for cls, registration in _type_registry._REGISTRY.items()
        if registration.explicit
    ]


def _add_type(row: seam.Row) -> Callable[[], None]:
    given = dict(row.fields)
    cls = given.pop("type")
    parts = given.pop("parts", ())
    register_type(cls, name=row.name, fields=parts, **given)
    return lambda: unregister_type(cls)


def _repr_rows() -> list[seam.Row]:
    return [
        seam.Row("repr", _named(text), {"claims": predicate, "text": text}, "package")
        for predicate, text in _atom_registry._PROTOCOL_REPRS
    ]


def _add_repr(row: seam.Row) -> Callable[[], None]:
    register_repr(row.claims, row.text)
    return lambda: unregister_repr(row.claims, row.text)


def _reflector_rows() -> list[seam.Row]:
    return [
        seam.Row("reflector", _named(lower), {"claims": claims, "lower": lower}, "package")
        for claims, lower in _REFLECTORS
    ]


def _add_reflector(row: seam.Row) -> Callable[[], None]:
    from .integrate import (  # noqa: PLC0415  -- the seat's own door
        register_reflector,
        unregister_reflector,
    )

    register_reflector(row.claims, row.lower)
    return lambda: unregister_reflector(row.claims, row.lower)


def _named(fn: Any) -> str:
    """A callable's own name, for a registry that stored no name with it."""
    return str(getattr(fn, "__qualname__", None) or getattr(fn, "__name__", fn))


def _advertised_rows(point_name: str, group: str) -> Callable[[], list[seam.Row]]:
    """Rows for one entry-point group, read without loading any of it."""

    def read() -> list[seam.Row]:
        return [
            seam.Row(point_name, name, {"entry": entry, "group": group}, name)
            for name, entry in seam.advertised(group).items()
        ]

    return read


type_ = seam.point(
    "type",
    "declaration",
    fields=("type",),
    optional=("to_atom", "from_atom", "image", "parts"),
    reader=_type_rows,
    adder=_add_type,
    doc=(
        "How a host class crosses, both ways, declared rather than derived. "
        "The ROW's name is the MeTTa type name, so nothing is said twice; "
        "`type` is the class, `to_atom`, `from_atom` and `image` are what "
        "metta.integrate.register_type takes, and `parts` is its `fields`, "
        "renamed because a row already carries its own fields. The rows are "
        "metta.convert's own registrations, read where they live."
    ),
)

repr_ = seam.point(
    "repr",
    "ownership",
    fields=("claims", "text"),
    reader=_repr_rows,
    adder=_add_repr,
    doc=(
        "How a host value PRINTS in MeTTa. `claims(value)` recognises the "
        "values this row formats and `text(value)` renders one. "
        "`metta.integrate.register_repr` is the same door."
    ),
)

reflector = seam.point(
    "reflector",
    "ownership",
    fields=("claims", "lower"),
    reader=_reflector_rows,
    adder=_add_reflector,
    doc=(
        "How a host object's structure becomes facts. `claims(value)` "
        "recognises what this row can lower and `lower(value, head, space)` "
        "writes the facts. `metta.integrate.register_reflector` is the same "
        "door."
    ),
)

provider = seam.point(
    "provider",
    "declaration",
    fields=("entry", "group"),
    reader=_advertised_rows("provider", SPACES_GROUP),
    doc=(
        f"A space backed by a library's own storage, advertised under the "
        f"{SPACES_GROUP} entry-point group. The rows are what installed "
        f"packages advertise, UNLOADED; `metta.integrate.load_entry_point` "
        f"loads one by name."
    ),
)

library = seam.point(
    "library",
    "declaration",
    fields=("entry", "group"),
    reader=_advertised_rows("library", LIBRARIES_GROUP),
    doc=(
        f"A directory of MeTTa or Prolog sources a package ships, advertised "
        f"under the {LIBRARIES_GROUP} entry-point group and importable as "
        f"`(library <name>)` once its path is registered."
    ),
)

integration = seam.point(
    "integration",
    "declaration",
    fields=("entry", "group"),
    reader=_advertised_rows("integration", ENTRY_POINT_GROUP),
    doc=(
        f"A whole library wired into a space, advertised under the "
        f"{ENTRY_POINT_GROUP} entry-point group. `metta.integrate.discover` "
        f"installs them in dependency order."
    ),
)
