"""Purpose: declare Python doors and resolve package accessors from their rows.

Assumes: body references name Python implementations with the declared signature.
Guarantees: the table imports without starting an engine, and every public
  projection is checked against it [tested: test_door_rows_need_no_engine,
  test_every_door_projection_is_current; commit=WORKTREE].
  Nested values are checked against the record fields before registration
  [tested: test_door_registration_refuses_mutable_or_untyped_nested_fields;
  commit=WORKTREE]. Public aliases preserve runtime overload lookup [tested:
  test_target_type_overloads_preserve_the_requested_class; commit=WORKTREE].
Owns resources: namespace objects borrow their receiver. They acquire no engine
  cursor and retain no registration after it is withdrawn [tested:
  test_a_retained_namespace_observes_replacement_and_withdrawal; commit=WORKTREE].
 Guarded by: the seam lock serializes registry validation and replacement. The
  lookup cache holds immutable snapshots under _CACHE_LOCK [tested:
  test_concurrent_door_claims_have_one_winner; commit=WORKTREE].
  Lookup, retained calls and generated annotations respect the receiving tier
  [tested: test_namespace_tiers_control_lookup_retained_calls_and_annotations;
  commit=WORKTREE].
Decides: a package publishes namespace members or explicit receiver sugars.
  It cannot replace a core door or duplicate an existing sugar point [tested:
  test_door_registration_refuses_collisions_and_duplicate_points; commit=WORKTREE].
"""

from __future__ import annotations

import ast
import importlib
import inspect
import keyword
import math
import threading
import weakref
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from functools import cache, cached_property
from pathlib import Path
from types import MappingProxyType, UnionType
from typing import Any, get_args, get_origin, get_overloads, get_type_hints, overload

from .vocabularies import ArgumentDelivery, Determinism, EffectClass, RefusalKind


class Kind(StrEnum):
    """The purpose of a door, published as the door-kind vocabulary."""

    query = "query"
    evaluation = "evaluation"
    write = "write"
    lifecycle = "lifecycle"
    introspection = "introspection"
    provider = "provider"
    scope = "scope"


class AnswersAs(StrEnum):
    """The outer host shape a door returns."""

    answers = "Answers"
    rows = "Rows"
    atom = "Atom"
    integer = "int"
    boolean = "bool"
    none = "None"
    context = "context"
    stream = "stream"
    sequence = "list"
    tuple = "tuple"
    mapping = "mapping"
    text = "str"
    value = "value"
    callable = "callable"
    space = "space"


class EvaluationAnswer(StrEnum):
    """Consumption choices of the evaluation door."""

    all = "all"
    answers = "answers"
    rows = "rows"
    atom = "atom"
    one = "one"
    first = "first"
    count = "count"  # type: ignore[assignment]  # the vocabulary word deliberately shadows str.count
    exists = "exists"
    none = "none"
    stream = "stream"


class Tier(StrEnum):
    """Host projections which carry a door."""

    sync = "sync"
    async_ = "async"
    module = "module"
    context = "context"
    remote = "remote"


class Owner(StrEnum):
    """Receiver families; namespace names themselves remain open."""

    space = "space"
    context = "context"
    rows = "rows"
    answers = "answers"
    remote_space = "remote-space"
    remote_cursor = "remote-cursor"
    namespace = "namespace"


class Receiver(StrEnum):
    """How an implementation receives the namespace's owner."""

    method = "method"
    space = "space"
    value = "value"
    none = "none"


class State(StrEnum):
    """The receiver state required by a contract."""

    live = "live"
    any = "any"


class Wire(StrEnum):
    """Boundary encodings already used by the seat."""

    atoms = "tagged-atoms"
    values = "host-values"
    goal = "prolog-goal"
    json = "json"
    arrow = "arrow"


@dataclass(frozen=True)
class Signature:
    """A complete Python call shape, parsed without evaluating annotations.

    The source is the parameter list. A return annotation and type parameters
    are separate fields so no host spelling of the door name is repeated.
    """

    parameters: str
    returns: str | None = None
    type_parameters: str = ""
    declarations: tuple[str, ...] = ()
    type_ignores: tuple[str, ...] = ()

    @cached_property
    def node(self) -> ast.FunctionDef:
        """The signature as Python's own grammar understands it."""
        generics = f"[{self.type_parameters}]" if self.type_parameters else ""
        answer = f" -> {self.returns}" if self.returns else ""
        tree = ast.parse(f"def door{generics}({self.parameters}){answer}: ...")
        node = tree.body[0]
        if (len(tree.body) != 1 or not isinstance(node, ast.FunctionDef)
                or len(node.body) != 1 or not isinstance(node.body[0], ast.Expr)
                or not isinstance(node.body[0].value, ast.Constant)
                or node.body[0].value.value is not Ellipsis):
            msg = "a door signature must declare one function"
            raise TypeError(msg)
        return node

    def arguments(self, module: str) -> tuple[Argument, ...]:
        """Named parameters, including positional and keyword boundaries."""
        args = self.node.args
        positional = [*args.posonlyargs, *args.args]
        defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
        out = []
        for index, (arg, default) in enumerate(zip(positional, defaults, strict=True)):
            kind = (
                inspect.Parameter.POSITIONAL_ONLY
                if index < len(args.posonlyargs)
                else inspect.Parameter.POSITIONAL_OR_KEYWORD
            )
            out.append(Argument.from_node(arg, kind, default, module))
        if args.vararg:
            out.append(Argument.from_node(args.vararg, inspect.Parameter.VAR_POSITIONAL, None, module))
        out.extend(
            Argument.from_node(arg, inspect.Parameter.KEYWORD_ONLY, default, module)
            for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
        )
        if args.kwarg:
            out.append(Argument.from_node(args.kwarg, inspect.Parameter.VAR_KEYWORD, None, module))
        return tuple(out)

    def host_signature(self, module: str, *, receiver: bool = False) -> inspect.Signature:
        """A binding signature; default expressions are not executed."""
        args = self.arguments(module)
        if receiver:
            args = args[1:]
        return inspect.Signature([
            inspect.Parameter(
                arg.name,
                arg.kind,
                default=inspect.Parameter.empty if arg.default is None else Ellipsis,
            )
            for arg in args
        ])


@dataclass(frozen=True, slots=True)
class Type:
    """A host annotation and its scope, projected by _projection.host_type."""

    python: str
    module: str

    def to_atom(self) -> Any:
        """The type expression through the shared projection table."""
        from ._projection import host_type  # noqa: PLC0415  -- the type projection

        return host_type(self.python, self.module)


@dataclass(frozen=True, slots=True)
class Argument:
    """One parameter's type, default expression, delivery, and binding kind."""

    name: str
    type: Type
    default: str | None
    delivery: ArgumentDelivery
    kind: inspect._ParameterKind

    @classmethod
    def from_node(
        cls, arg: ast.arg, kind: inspect._ParameterKind, default: ast.expr | None, module: str
    ) -> Argument:
        """Use the shared type projection's outer argument delivery."""
        from ._projection import host_delivery  # noqa: PLC0415 -- shared argument contract

        annotation = ast.unparse(arg.annotation) if arg.annotation else "Any"
        type_ = Type(annotation, module)
        return cls(
            arg.arg,
            type_,
            ast.unparse(default) if default is not None else None,
            host_delivery(type_.to_atom()),
            kind,
        )


@dataclass(frozen=True, slots=True)
class Body:
    """A qualified implementation name, resolved only when invoked."""

    module: str
    symbol: str
    receiver: Receiver = Receiver.method

    @property
    def reference(self) -> str:
        """The stable source reference used by contracts and documentation."""
        return f"{self.module}:{self.symbol}"

    def resolve(self) -> Any:
        """Load the implementation and preserve import failures verbatim."""
        value = importlib.import_module(self.module)
        for part in self.symbol.split("."):
            value = getattr(value, part)
        return value


@dataclass(frozen=True, slots=True)
class Binding:
    """The engine door and the wire used to cross it."""

    door: str
    wire: Wire


@dataclass(frozen=True, slots=True)
class Provider:
    """The seam registrant and accessor namespace contributing a door."""

    registrant: str
    namespace: str
    point: str = "door"
    callable: bool = False


@dataclass(frozen=True, slots=True)
class Sugar:
    """A named point in another door's parameter space."""

    base: str
    fixed: tuple[tuple[str, str | int | float | bool | None], ...]


@dataclass(frozen=True, slots=True)
class Remote:
    """The operation's request and reply schemas for the remote protocol."""

    operation: str
    request: str
    response: str
    summary: str


@dataclass(frozen=True, slots=True)
class Refusal:
    """A locally declared refusal and the test that exercises it."""

    kind: RefusalKind
    witness: str


@dataclass(frozen=True, slots=True)
class Assumes:
    """Input and receiver preconditions as data."""

    state: State
    args: tuple[Argument, ...]


@dataclass(frozen=True, slots=True)
class Guarantees:
    """Result and effect promises as data.

    Effects bound the door's work, including callbacks and consumption of an
    owned lazy result. A returned handle or callable has its own later work;
    a scope includes setup and teardown, while its caller owns the block.
    Determinism describes logical alternatives, including those collected in
    a result container. Refusals remain a separate part of the contract.
    """

    answers: AnswersAs
    type: Type
    effect: EffectClass
    determinism: Determinism


@dataclass(frozen=True, slots=True)
class FailsWhen:
    """Declared local refusals; implementation failures propagate unchanged."""

    refuses: tuple[Refusal, ...]
    propagates: bool = True


@dataclass(frozen=True, slots=True)
class Door:
    """One authoritative operation contract shared by every projection."""

    owner: Owner
    name: str
    kind: Kind
    signatures: tuple[Signature, ...]
    answers: AnswersAs
    effect: EffectClass
    determinism: Determinism
    tiers: tuple[Tier, ...]
    body: Body | None
    docs: str
    evidence: tuple[str, ...]
    state: State = State.live
    sugar_of: Sugar | None = None
    binding: Binding | None = None
    provider: Provider | None = None
    refuses: tuple[Refusal, ...] = ()
    remote: Remote | None = None
    alias: str | None = None
    async_signature: Signature | None = None
    async_reason: str | None = None
    async_excluded: str | None = None
    context_inplace: bool = False
    inherited: bool = False
    is_property: bool = False

    @property
    def python(self) -> str:
        """Python's casing map for the MeTTa-facing spelling."""
        return self.name.replace("-", "_")

    @property
    def key(self) -> str:
        """The receiver or namespace and the operation name."""
        owner = self.provider.namespace if self.owner is Owner.namespace and self.provider else self.owner
        return f"{owner}:{self.name}"

    @property
    def signature(self) -> Signature:
        """The implementation signature after any overload declarations."""
        return self.signatures[-1]

    @property
    def args(self) -> tuple[Argument, ...]:
        """The complete argument contract, derived from this row's signature."""
        args = self.signature.arguments(self.body.module if self.body else "metta")
        return args if self.body and self.body.receiver is Receiver.none else args[1:]

    @property
    def assumes(self) -> Assumes:
        """Preconditions checked by the obligation lane."""
        return Assumes(self.state, self.args)

    @property
    def guarantees(self) -> Guarantees:
        """Output promises checked by the obligation lane."""
        return Guarantees(
            self.answers,
            Type(self.signature.returns or "Any", self.body.module if self.body else "metta"),
            self.effect,
            self.determinism,
        )

    @property
    def fails_when(self) -> FailsWhen:
        """The refusal contract checked by the witness lane."""
        return FailsWhen(self.refuses)


@cache
def _record_fields(record_type: type) -> tuple[tuple[str, Any], ...]:
    """Read the declared grammar once, including postponed nested types."""
    hints = get_type_hints(record_type)
    return tuple((field.name, hints[field.name]) for field in fields(record_type))


def _field_finding(value: Any, annotation: Any, path: str) -> str | None:
    """Check nested data against the records' own grammar, without coercion."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is UnionType:
        if any(_field_finding(value, arm, path) is None for arm in args):
            return None
    elif origin is tuple:
        if isinstance(value, tuple):
            if len(args) == 2 and args[-1] is Ellipsis:
                elements = zip(value, (args[0] for _ in value), strict=True)
            elif len(value) == len(args):
                elements = zip(value, args, strict=True)
            else:
                return f"{path} requires {annotation}"
            for index, (item, kind) in enumerate(elements):
                finding = _field_finding(item, kind, f"{path}[{index}]")
                if finding:
                    return finding
            return None
    elif isinstance(value, annotation):
        if annotation is int and isinstance(value, bool):
            return f"{path} requires int"
        if annotation is float and not math.isfinite(value):
            return f"{path} requires a finite float"
        if isinstance(annotation, type) and is_dataclass(annotation):
            for name, kind in _record_fields(annotation):
                finding = _field_finding(getattr(value, name), kind, f"{path}.{name}")
                if finding:
                    return finding
        return None
    return f"{path} requires {annotation}"


def validate(rows: Iterable[Door]) -> tuple[Door, ...]:
    """Refuse invalid records, collisions, cyclic sugars, and duplicate points."""
    result = tuple(rows)
    by_key: dict[str, Door] = {}
    spellings: set[tuple[str, str]] = set()
    points: dict[tuple[Owner, str, tuple[tuple[str, Any], ...]], str] = {}
    namespaces: dict[str, str] = {}
    for row in result:
        if not isinstance(row, Door):
            msg = "the door point accepts immutable Door rows"
            raise TypeError(msg)
        finding = _field_finding(row, Door, f"door {row.name!r}")
        if finding:
            raise TypeError(finding)
        if len({item.kind for item in row.refuses}) != len(row.refuses):
            msg = f"door {row.key!r} repeats a refusal kind"
            raise ValueError(msg)
        if row.body and any(not part.isidentifier() or keyword.iskeyword(part)
                            for name in (row.body.module, row.body.symbol)
                            for part in name.split(".")):
            msg = f"door {row.key!r} requires a qualified implementation name"
            raise ValueError(msg)
        if row.provider and (row.provider.point != "door" or not row.provider.registrant):
            msg = f"door {row.key!r} requires a named registrant on the door point"
            raise ValueError(msg)
        if any(not item.strip() for item in row.evidence) or any(not item.witness.strip() for item in row.refuses):
            msg = f"door {row.key!r} has an empty evidence or refusal witness"
            raise ValueError(msg)
        if row.key in by_key:
            msg = f"door {row.key!r} already exists"
            raise ValueError(msg)
        if not row.python.isidentifier() or keyword.iskeyword(row.python):
            msg = f"door {row.key!r} has no Python spelling"
            raise ValueError(msg)
        spelling = (row.key.rpartition(':')[0], row.python)
        if spelling in spellings:
            msg = f"door {row.key!r} has an existing Python spelling"
            raise ValueError(msg)
        spellings.add(spelling)
        if not row.signatures or not isinstance(row.docs, str) or not row.docs.strip() or not row.evidence:
            msg = f"door {row.key!r} needs signatures, documentation, and evidence"
            raise ValueError(msg)
        if not row.tiers or len(set(row.tiers)) != len(row.tiers):
            msg = f"door {row.key!r} needs distinct projection tiers"
            raise ValueError(msg)
        if row.body is None and row.sugar_of is None:
            msg = f"door {row.key!r} has neither an implementation nor a sugar base"
            raise ValueError(msg)
        for signature in row.signatures:
            _ = signature.node
        if row.owner is Owner.namespace:
            if row.provider is None:
                msg = f"namespace door {row.key!r} has no provider"
                raise ValueError(msg)
            name = row.provider.namespace
            if not name.isidentifier() or name.startswith("_") or keyword.iskeyword(name):
                msg = f"invalid accessor namespace {name!r}"
                raise ValueError(msg)
            if row.python.startswith("_"):
                msg = f"namespace door {row.key!r} must be a public member"
                raise ValueError(msg)
            if row.provider.callable:
                if name in namespaces:
                    msg = f"namespace {name!r} already has callable door {namespaces[name]}"
                    raise ValueError(msg)
                namespaces[name] = row.key
        by_key[row.key] = row
    core_names = {row.python for row in result if row.owner in {Owner.space, Owner.context}}
    for row in result:
        if row.owner is Owner.namespace and row.provider and row.provider.namespace in core_names:
            msg = f"namespace {row.provider.namespace!r} collides with a core door"
            raise ValueError(msg)
        if row.sugar_of is None:
            continue
        seen = {row.key}
        fixed: dict[str, Any] = {}
        current = row
        while current.sugar_of is not None:
            sugar = current.sugar_of
            if sugar.base in seen:
                msg = f"cyclic door sugar at {sugar.base!r}"
                raise ValueError(msg)
            seen.add(sugar.base)
            if sugar.base not in by_key:
                msg = f"door {row.key!r} names missing sugar base {sugar.base!r}"
                raise ValueError(msg)
            base = by_key[sugar.base]
            arguments = {arg.name for arg in base.args}
            for name, value in sugar.fixed:
                if name not in arguments:
                    msg = f"door {row.key!r} fixes unknown argument {name!r}"
                    raise ValueError(msg)
                if name in fixed and fixed[name] != value:
                    msg = f"door {row.key!r} contradicts fixed argument {name!r}"
                    raise ValueError(msg)
                fixed[name] = value
            if len(dict(sugar.fixed)) != len(sugar.fixed):
                msg = f"door {row.key!r} repeats a fixed argument"
                raise ValueError(msg)
            current = base
        point = (row.owner, current.key, tuple(sorted(fixed.items())))
        if point in points:
            msg = f"door {row.key!r} is the existing parameter point {points[point]!r}"
            raise ValueError(msg)
        points[point] = row.key
    return result


_CACHE_LOCK = threading.RLock()
_CACHE_ROWS: tuple[Any, ...] = ()


@dataclass(frozen=True)
class _Snapshot:
    rows: Mapping[str, Door]
    namespaces: Mapping[tuple[Tier, str], Mapping[str, str]]
    callable: Mapping[tuple[Tier, str], str]
    sugars: Mapping[Owner, Mapping[str, str]]


_CACHE: _Snapshot | None = None
_CHECKED_BODIES: weakref.WeakKeyDictionary[Any, set[Signature]] = weakref.WeakKeyDictionary()


def table(*, discover: bool = True) -> Mapping[str, Door]:
    """Current core and package rows, indexed by their qualified names."""
    return _snapshot(discover=discover).rows


def _snapshot(*, discover: bool = True) -> _Snapshot:
    from . import seam  # noqa: PLC0415  -- the registry imports the row grammar lazily

    held = seam.door.rows() if discover else seam._rows_of(seam.door, discover_first=False)
    global _CACHE_ROWS, _CACHE  # noqa: PLW0603 -- replace one process-wide registry snapshot under _CACHE_LOCK
    with _CACHE_LOCK:
        if held != _CACHE_ROWS or _CACHE is None:
            rows = validate((*DOORS, *(door for row in held for door in row.doors)))
            names: dict[tuple[Tier, str], dict[str, str]] = {}
            callable_doors: dict[tuple[Tier, str], str] = {}
            sugars: dict[Owner, dict[str, str]] = {}
            for row in rows:
                if row.owner is Owner.namespace and row.provider:
                    for tier in row.tiers:
                        index = tier, row.provider.namespace
                        names.setdefault(index, {})[row.python] = row.key
                        if row.provider.callable:
                            callable_doors[index] = row.key
                elif row.sugar_of:
                    sugars.setdefault(row.owner, {})[row.python] = row.key
            _CACHE = _Snapshot(
                MappingProxyType({row.key: row for row in rows}),
                MappingProxyType({name: MappingProxyType(members) for name, members in names.items()}),
                MappingProxyType(callable_doors),
                MappingProxyType({owner: MappingProxyType(members) for owner, members in sugars.items()}),
            )
            _CACHE_ROWS = held
        return _CACHE


def validate_registration(row: Any, standing: tuple[Any, ...]) -> None:
    """Validate the complete proposed registry while the seam lock is held."""
    if not isinstance(row.doors, tuple):
        msg = "a door registration supplies a tuple of immutable Door rows"
        raise TypeError(msg)
    for door in row.doors:
        if not isinstance(door, Door) or door.provider is None or door.provider.registrant != row.name:
            msg = "each package door must name the registrant that owns it"
            raise ValueError(msg)
        if door.owner is not Owner.namespace and (
            door.owner not in {Owner.rows, Owner.answers} or door.sugar_of is None
        ):
            msg = "package doors belong to namespaces or explicit Rows/Answers sugars"
            raise ValueError(msg)
        if door.owner is not Owner.namespace:
            from collections import (  # noqa: PLC0415 -- validate the inherited receiver protocol only on registration
                UserList,
            )
            from collections.abc import (  # noqa: PLC0415 -- validate the inherited receiver protocol only on registration
                Sequence,
            )

            inherited = UserList if door.owner is Owner.rows else Sequence
            if door.python.startswith("_") or hasattr(inherited, door.python):
                msg = f"package sugar {door.key!r} collides with the receiver protocol"
                raise ValueError(msg)
    validate((*DOORS, *(door for held in (*standing, row) for door in held.doors)))


def _bind_public(member: Any, owner: str, name: str) -> None:
    """Preserve runtime overload lookup when a body gains its public name."""
    function = member.fget if isinstance(member, property) else member
    assert function is not None
    # CPython indexes overloads by module and qualified name. Register their
    # public identities through typing's own decorator before renaming the body.
    # https://github.com/python/cpython/blob/v3.14.4/Lib/typing.py
    declarations = get_overloads(function)
    for declaration in declarations:
        declaration.__name__ = name
        declaration.__qualname__ = f"{owner}.{name}"
        overload(declaration)
    function.__name__ = name
    function.__qualname__ = f"{owner}.{name}"


class _Call:
    """A retained member resolves its current row again when called."""

    __slots__ = ("_key", "_receiver", "_tier")

    def __init__(self, receiver: Any, key: str, tier: Tier = Tier.sync) -> None:
        self._receiver = receiver
        self._key = key
        self._tier = tier

    @property
    def __signature__(self) -> inspect.Signature:
        row = table().get(self._key)
        if row is None or self._tier not in row.tiers:
            msg = f"door {self._key!r} was withdrawn"
            raise AttributeError(msg)
        return row.signature.host_signature(
            row.body.module if row.body else "metta", receiver=not row.body or row.body.receiver is not Receiver.none
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        row = table().get(self._key)
        if row is None or self._tier not in row.tiers:
            msg = f"door {self._key!r} was withdrawn"
            raise AttributeError(msg)
        return _invoke(row, self._receiver, args, kwargs)


def _invoke(row: Door, receiver: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    if row.body is None:
        if row.sugar_of is None:
            msg = f"door {row.key!r} has no implementation"
            raise TypeError(msg)
        base = table()[row.sugar_of.base]
        overlap = set(kwargs).intersection(name for name, _ in row.sugar_of.fixed)
        if overlap:
            msg = f"door {row.key!r} fixes {', '.join(sorted(overlap))}"
            raise TypeError(msg)
        row.signature.host_signature("metta", receiver=True).bind(*args, **kwargs)
        return _invoke(base, receiver, args, {**kwargs, **dict(row.sugar_of.fixed)})
    function = row.body.resolve()
    _check_body(function, row)
    if row.body.receiver is Receiver.none:
        return function(*args, **kwargs)
    if row.body.receiver is Receiver.space:
        from . import seam  # noqa: PLC0415  -- public receiver normalization

        receiver = seam.space_of(receiver)
    return function(receiver, *args, **kwargs)


def _check_body(function: Any, row: Door) -> None:
    """Check an installed provider's call shape before its first invocation."""
    assert row.body is not None
    try:
        with _CACHE_LOCK:
            if row.signature in _CHECKED_BODIES.get(function, ()):
                return
    except TypeError:
        # Some native descriptors cannot be weakly referenced. Checking them
        # on each use avoids retaining a provider or its receiver indefinitely.
        pass
    actual = inspect.signature(function, eval_str=False)
    expected = row.signature.host_signature(row.body.module)
    def shape(parameters):
        return tuple((parameter.name, parameter.kind, parameter.default is inspect.Parameter.empty)
                     for parameter in parameters.values())
    if shape(actual.parameters) != shape(expected.parameters):
        msg = f"door {row.key!r}: implementation signature differs from its row"
        raise TypeError(msg)
    try:
        with _CACHE_LOCK:
            _CHECKED_BODIES.setdefault(function, set()).add(row.signature)
    except TypeError:
        pass


class Namespace:
    """A package accessor borrowing one receiver and the live door registry."""

    __slots__ = ("_name", "_receiver", "_tier")

    def __init__(self, receiver: Any, name: str, tier: Tier = Tier.sync) -> None:
        """Borrow a receiver for one named accessor and projection tier."""
        self._receiver = receiver
        self._name = name
        self._tier = tier

    def __getattr__(self, name: str) -> Any:
        """Resolve a member from the current registration snapshot."""
        key = _snapshot().namespaces.get((self._tier, self._name), {}).get(name)
        if key is None:
            msg = f"namespace {self._name!r} has no door {name!r}"
            raise AttributeError(msg)
        return _Call(self._receiver, key, self._tier)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the current row declared as the callable accessor."""
        current = _snapshot()
        key = current.callable.get((self._tier, self._name))
        row = current.rows.get(key) if key is not None else None
        if row is None:
            msg = f"namespace {self._name!r} has no callable door"
            raise TypeError(msg)
        return _invoke(row, self._receiver, args, kwargs)

    def __dir__(self) -> list[str]:
        """List only the currently registered members of this tier."""
        return sorted(_snapshot().namespaces.get((self._tier, self._name), ()))


def namespace(receiver: Any, name: str, tier: Tier = Tier.sync) -> Namespace:
    """Build a namespace only when current registrations contribute members."""
    if (tier, name) in _snapshot().namespaces:
        return Namespace(receiver, name, tier)
    msg = f"no door namespace {name!r} is registered"
    raise AttributeError(msg)


def sugar(receiver: Any, owner: Owner, name: str) -> Any:
    """Resolve a package's short receiver spelling through its sugar row."""
    key = _snapshot().sugars.get(owner, {}).get(name)
    if key is None:
        msg = f"no {owner} sugar {name!r} is registered"
        raise AttributeError(msg)
    return _Call(receiver, key)


def publish(runtime: Any) -> int:
    """Publish one atomic catalog snapshot and return its changed row count."""
    from ._door_catalog import atoms  # noqa: PLC0415  -- generated catalog projection

    runtime.must("load_files(Path, [if(not_loaded)])", Path=str(Path(__file__).with_name("door_catalog.pl")))
    result = runtime.must(
        "metta_py_publish_doors(Wires, Count)",
        Wires=[atom.to_wire() for atom in atoms(tuple(table().values()))],
    )
    return int(result["Count"])


# closed-set: decides; policy=the complete Python core door contracts; reads=each named implementation and evidence target, checked by tools/doorgen.py
DOORS: tuple[Door, ...] = (
    Door(
        owner=Owner.space,
        name='name',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='_SpaceId', declarations=('property',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_name'),
        docs=(
            'The live engine name represented by this handle.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.live,
        is_property=True,
    ),
    Door(
        owner=Owner.space,
        name='self',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='Space', declarations=('property',)),
        ),
        answers=AnswersAs.space,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_self'),
        docs=(
            "The space this receiver's doors work in, which for a space is itself.\n"
            '\n'
            "MeTTa's own `&self` is the space a form is evaluated in, and a form\n"
            "stored in a space is evaluated in THAT space, so a space's `&self` is\n"
            'the space. `MeTTa.self` answers the same question for a context, whose\n'
            'answer is its home space, which is what makes `m.self` one attribute\n'
            'read at every door that takes either [source:\n'
            'extensions/python/metta/_api_types.py, SpaceLike].\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
        async_excluded="the space a receiver's doors work in, which for a space IS the receiver: mirroring it would give the async tier a property whose answer is the SYNCHRONOUS space, which is the one thing the async surface exists not to hand out. AsyncMeTTa answers its own home through the context tier, and an async space is already itself",
    ),
    Door(
        owner=Owner.space,
        name='space-names',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='list[str]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_space_names'),
        docs=(
            "Every space name this engine registers, sorted: '&self' and\n"
            "'&metta' from boot, every native space something created or wrote to,\n"
            'and every foreign space currently bound. (new-space) and (spawn ...)\n'
            'create, so their answers are here at once; naming a space never\n'
            "registers it, so Space('&kb') is not here until a write, and a bind!\n"
            "token's target appears once something is stored under it.\n"
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_space_names_lists_the_registered_spaces',),
        binding=Binding('metta_py_space_names', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='drop',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_drop'),
        docs=(
            'Clear this space and release an anonymous name for reuse.\n'
            '\n'
            'Dropping retires every space-owned catalog declaration, including\n'
            'algebra rows and their Python mirrors.\n'
            'Dropping unregisters a Python provider and closes only backing state\n'
            'owned by this handle. A foreign provider with a clear/drop lifecycle,\n'
            'such as MORK, releases its provider state.\n'
            "A named space's public name is not an anonymous allocation and never\n"
            'enters the anonymous pool. The engine-owned &self and &metta roots\n'
            "refuse before any Python-side state changes; drop the caller's own\n"
            'context or a named space instead.\n'
            'Subscriptions on the space cancel with it: a pooled name reused later\n'
            "must not deliver to the old life's watchers. The handle itself dies\n"
            'here, and dropping twice is a no-op, as closing twice is.\n'
            '\n'
            'Engine teardown must succeed before Python cleanup is discarded.\n'
            'If later cleanup fails, call drop() again to finish it. The handle\n'
            'refuses other operations in that state and retains its anonymous name\n'
            'until cleanup succeeds; retrying does not repeat engine teardown.\n'
        ),
        evidence=('extensions/python/ext/metta-arrays/tests/test_arrays.py::test_dropping_the_space_retires_its_installation_row', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_drop_retires_algebra_before_redeclaration', 'extensions/python/tests/ch04_spaces_and_matching/test_drop_recovery.py::test_backing_close_failure_keeps_the_name_and_cleanup_retryable'),
        state=State.any,
        binding=Binding('metta_py_drop_space', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='dropped',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self', returns='bool', declarations=('property',)),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_dropped'),
        docs=(
            "Whether :meth:`drop` has released this handle's space.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
    ),
    Door(
        owner=Owner.space,
        name='to-wire',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='list'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_to_wire'),
        docs=(
            'Encode the live engine reference as a portable space operand.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.live,
        async_excluded="Space's Atom/Handle operand protocol, not an engine call",
    ),
    Door(
        owner=Owner.space,
        name='metatype',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='str', declarations=('property',)),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_metatype'),
        docs=(
            'Read Space.metatype.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
        async_excluded="Space's Atom/Handle operand protocol, not an engine call",
    ),
    Door(
        owner=Owner.space,
        name='bind',
        kind=Kind.scope,
        signatures=(
            Signature('self, values: _abc.Mapping[str, Any] | None=None, /, **named: Any', returns='_BoundValues'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_bind'),
        docs=(
            'Scope named host values for :meth:`run` without a call flag.\n'
        ),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_atoms.py::test_bind_reaches_a_variable_hole_through_an_atom_key', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_bind_carries_identity_into_a_term', 'extensions/python/tests/ch04_spaces_and_matching/test_variadic_doors.py::test_eval_batches_with_one_bind_scope'),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:bind]'),
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_bind_refuses_the_reserved_template_namespace'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='run',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, source: str | TemplateLike, /, *, timeout: float | None=None, inferences: int | None=None, **values: Any', returns='list[list[Atom]]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_run'),
        docs=(
            'Run MeTTa source: one list of answers per ! directive.\n'
            '\n'
            "The pipeline is the engine's own reader, compiler and evaluator, so\n"
            'the answers are exactly what the CLI would print, kept grouped per\n'
            'directive instead of flattened. Equations and facts in the source\n'
            'land in this space.\n'
            '\n'
            'The source may carry HOLES, which are bindings by position:\n'
            '\n'
            '    m.run(t"!(fib {n})")            # a 3.14 t-string literal\n'
            '    m.run("!(fib {n})", n=10)       # the same on every version\n'
            '\n'
            'Each hole is spliced into the text as a generated symbol and bound to\n'
            'its value, so a str stays one String atom and never has to be escaped.\n'
            'Values enter through `encode`: an int is a Number, a str a String, an\n'
            'Atom itself, a Space its handle. The markers at a hole are the atom\n'
            'constructors, `{Symbol(name)}`, `{Grounded(obj)}` and `{parse(text)}`,\n'
            'with the specs `:sym`, `:py` and `:expr` as their short forms; `!r`\n'
            'and `!s` convert in Python first and enter the result as text. A hole\n'
            'inside a string literal, a comment or a symbol is refused with its\n'
            'line and column.\n'
            '\n'
            '`bind()` is the same substitution by NAME, for a value several calls\n'
            'share, the way DuckDB reads a local dataframe by its variable name:\n'
            '\n'
            '    with m.bind({"graph": my_graph}):\n'
            '        m.run("!(py-len graph)")\n'
            '\n'
            'Each named symbol substitutes to its value (objects by identity),\n'
            'after reading, before anything runs. It is a BLOCK rather than a\n'
            'keyword because a binding mapping is the kind of value that grows,\n'
            'and a block grows down the page where a keyword has to fit beside\n'
            'everything else on the call. Every call that accepts a target reads the\n'
            'same scope, so one block covers run(), eval(), and answers() together.\n'
            'A binding names a symbol and so replaces EVERY occurrence of it,\n'
            'including one the author meant as a symbol; a hole is positional and\n'
            'cannot reach anything but itself.\n'
            '\n'
            '`timeout` (seconds) and `inferences` (engine steps) bound the call\n'
            "with the engine's own guards; passing either raises TimeLimitError\n"
            'or InferenceLimitError when the bound is hit, and whatever the\n'
            'source completed before the stop, writes included, stands.\n'
            '\n'
            '`with m.capture() as output` collects printed text in `output.text`\n'
            "without changing this method's return shape. `with m.atomic()`\n"
            'and `with m.speculative()` scope execution policy without boolean\n'
            'combinations on each call. Atomic commits or rolls\n'
            'back each complete source; speculative answers and discards its\n'
            'writes. Both cover engine state; Python side effects and subscription\n'
            'callbacks already fired stay where they happened.\n'
            '\n'
            'A term the engine hands back unevaluated is an ordinary MeTTa value,\n'
            'not a failure: `!(hello world)` answers `(hello world)` and that is\n'
            'the whole of hello world in this language. eval_status() reports\n'
            'which answers reduced and which did not, as data, for a caller who\n'
            'wants to decide about it.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_run_groups_answers_per_directive',),
        alias='run',
        binding=Binding('metta_py_run', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='explain',
        kind=Kind.introspection,
        signatures=(
            Signature('self, query: Any, /, *, analyze: bool=False, allow_writes: bool=False, **values: Any', returns='Explanation'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_explain'),
        docs=(
            'What the engine will do with this query, reflected rather than run.\n'
            '\n'
            '    e = m.self.explain(\n'
            '        "(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))"\n'
            '    )\n'
            '    e.plan          # (plan generic-join (order ...) (relations ...))\n'
            '    e["writes"]     # (writes transactional)\n'
            '\n'
            "SQL's EXPLAIN, over this engine's own decisions. A match form answers\n"
            'which seam entry handles it and with what fidelity, whether a bound\n'
            'pushes into the provider, the source, the context world, the\n'
            'annotation semiring, emission, event delivery, writes, the error mode,\n'
            "the merge policy, whether the space's source relations are\n"
            'materialised, and the PLAN: `generic-join` with the variable order and\n'
            "each conjunct's columns, `nested-loop` with the conjunct the matcher\n"
            'leads with, or `empty-factor` with the conjunct that has no candidate.\n'
            'An operation call answers its effect, whether it has an inverse, its\n'
            'annotations, its error mode and the cache decision the memo made.\n'
            '\n'
            'The plan names the join the engine RUNS. Deciding that costs the\n'
            "query's shape and one scan of each conjunct's relation, because a\n"
            'conjunction whose stored rows are not all ground declines the Generic\n'
            'Join and must read `nested-loop`; nothing is sorted and no trie is\n'
            'built, so explaining a triangle over 2,048 stored edges cost 7,350\n'
            "engine inferences against the query's own 237,473, and the share falls\n"
            'as the data grows: 10.1%, 4.6% and 3.1% at 128, 512 and 2,048 rows\n'
            '[measured 2026-09-07; command=PYTHONPATH=extensions/python\n'
            'python extensions/python/benchmarks/probes/explain_plan_cost.py;\n'
            'fixture=a two-out-degree ring of\n'
            '1,024 nodes at loadavg 62].\n'
            '\n'
            '`analyze=True` is EXPLAIN ANALYZE: the same items plus `(inferences\n'
            'N)`, `(answers N)` and `(cputime S)` measured by running the query\n'
            'inside `stats()`. It REFUSES the query when the engine can NAME an\n'
            'operation in it that writes, because an analysis that mutates is not an\n'
            'analysis; `allow_writes=True` says to measure it anyway. A match\n'
            'TEMPLATE is evaluated once per answer, so `(match &s (edge $x $y)\n'
            '(add-atom &s (seen $x)))` is a writing query.\n'
            '\n'
            'The longhand is the MeTTa form: `m.run("!(explain <query>)")` answers\n'
            'the same atoms, and `analyze=True` is that run with a `stats()` block\n'
            'around `eval()` of the same query. A form that is neither a match nor\n'
            "an operation call keeps the engine's own `type_error(explainable, ...)`.\n"
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_a_rows_with_no_query_behind_it_refuses_to_explain', 'extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_an_explanation_is_a_mapping_over_its_item_heads', 'extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_an_explanation_is_data_a_space_stores_and_matches_back'),
    ),
    Door(
        owner=Owner.space,
        name='profile',
        kind=Kind.introspection,
        signatures=(
            Signature('self, source: str | TemplateLike, /, *, timeout: float | None=None, inferences: int | None=None, **values: Any', returns='tuple[list[list[Atom]], EngineProfile]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_profile'),
        docs=(
            "Run source under the engine's statistical profiler, answering\n"
            '(groups, profile): the groups exactly as run() answers them, and\n'
            'the profile carrying sample counters plus one row per predicate,\n'
            'self-ticks first.\n'
            '\n'
            '    groups, prof = m.profile("!(big-computation)")\n'
            '    prof.top(5)     # the five predicates the samples landed in\n'
            '\n'
            "A row carries the predicate's calls and redos, its ticks, the file\n"
            'and line its clauses were defined at, and its share of the sampled\n'
            'seconds. `prof.as_stats()` answers the same run as a `pstats.Stats`,\n'
            'so `sort_stats("cumulative").print_stats()` reads it and\n'
            '`dump_stats(path)` writes what snakeviz and tuna open.\n'
            '\n'
            'The sampler is statistical: a program that finishes in\n'
            'milliseconds carries few samples, so profile something that runs.\n'
            'Profiling changes execution; it is a debugging surface, not a\n'
            'mode to leave on.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_profile_exports_as_pstats', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_profile_is_the_same_table_every_other_door_answers', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_counts_samples_on_real_work'),
    ),
    Door(
        owner=Owner.space,
        name='profile-extension',
        kind=Kind.introspection,
        signatures=(
            Signature('self, source: str | TemplateLike, /, *, extension: str | None=None, names: _abc.Sequence[str] | None=None, timeout: float | None=None, inferences: int | None=None, **values: Any', returns='tuple[list[list[Atom]], list[FunctionCost]]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_profile_extension'),
        docs=(
            'Run source under the profiler, reporting only YOUR functions.\n'
            '\n'
            '`profile()` answers "which predicate did the samples land in", over\n'
            'every predicate in the process. The question a library author has is\n'
            'narrower: of the functions my library registered, which one is\n'
            'costing me, and is anything wrong with how it was installed.\n'
            '\n'
            '    groups, costs = m.profile_extension("!(my-workload)",\n'
            '                                        extension="mylib")\n'
            '    for cost in costs:\n'
            '        print(cost)\n'
            '    # <mylib-join/3 prolog: 40100 calls, 39900 redos, 812 ticks, index 1x>\n'
            '\n'
            'Name the `extension` and its registered members are looked up, or\n'
            'pass `names` for an explicit list. Each row carries the tier that\n'
            'installed the function and where from, its exact call and redo\n'
            "counts, the sampler's ticks, and its clause index.\n"
            '\n'
            'The two columns worth reading first are `redos` and `speedup`. Redos\n'
            'on a function meant to be deterministic are a leftover choice point,\n'
            'which costs the caller about twice and is invisible to the inference\n'
            'counter. A `speedup` of 1 means no argument discriminates, so every\n'
            'call walks the clause list; `indexed` False on a function nothing has\n'
            'called much only means SWI has not built one yet.\n'
            '\n'
            'The sampler is statistical, so profile something that runs, and\n'
            'profiling changes execution: this is a debugging surface.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_extension_needs_exactly_one_of_extension_or_names', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_extension_reports_every_declared_member', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_extension_separates_an_indexed_table_from_a_single_clause'),
        refuses=(
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:profile-extension]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='save',
        kind=Kind.introspection,
        signatures=(
            Signature('self, path: str | os.PathLike[str], *, format: SaveFormat=SaveFormat.metta, timeout: float | None=None, inferences: int | None=None', returns='int'),
        ),
        answers=AnswersAs.integer,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_save'),
        docs=(
            'Write every stored atom of this space, equations included, as\n'
            'MeTTa source by default. ``format="fast"`` writes a version-pinned\n'
            "image of the receiver's equation world: its own atoms, owned child\n"
            'spaces, aliases bound to those spaces, and translator rules. Loading\n'
            'the image mints fresh runtime space identities and preserves their\n'
            "graph relationships. The returned count remains the receiver's own\n"
            'atom count. Text variables are numbered by first occurrence within\n'
            'each atom, so saving unchanged content twice is byte-stable. A path\n'
            'ending .gz writes gzip compressed in either format, and load and\n'
            'import! read it back under the same name. The completed sibling file\n'
            'is synced and then atomically replaces the target, so a failed save\n'
            'leaves the old file intact. Atoms carrying live host objects cannot\n'
            'survive either file and are refused.\n'
            '\n'
            '`timeout` (seconds) and `inferences` (engine steps) bound the save with\n'
            "the engine's own guards, exactly as they bound load(). A text save\n"
            'examines the receiver; a fast save also traverses its reachable\n'
            'equation-world graph and registries. Those guards therefore bound all\n'
            'state the chosen format writes, and the atomic replace above makes a\n'
            'stopped save safe: the sibling is never moved into place.\n'
            '\n'
            'There is no `format` on load(), and that is not an omission. When you\n'
            'save, the file does not exist and something has to say which of the two\n'
            'to write; when you load, load() reads which it is, `.gz` included.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_specialized_program_saves_and_digests', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_save_keeps_every_number_it_accepts', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_save_keeps_every_symbol_it_accepts'),
    ),
    Door(
        owner=Owner.space,
        name='source',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_source'),
        docs=(
            "Return this space's directly stored atoms as loadable MeTTa text.\n"
            '\n'
            'This is exactly the text that ``save(path, format="metta")`` writes:\n'
            'one atom per line, including equations, with a final newline when the\n'
            'space is nonempty. Variables are numbered by first occurrence within\n'
            'each atom, making independent views of unchanged content byte-stable.\n'
            'Inherited prelude and library atoms, the global\n'
            '``&metta`` catalog, and child spaces are outside that save boundary.\n'
            'Live host objects and atoms whose printed form cannot round-trip are\n'
            'refused for the same reason a text save refuses them.\n'
        ),
        evidence=('extensions/python/tests/ch18_performance/test_fast_bindings.py::test_fast_images_preserve_each_equations_binding',),
    ),
    Door(
        owner=Owner.space,
        name='load',
        kind=Kind.introspection,
        signatures=(
            Signature('self, path: str | os.PathLike[str], *, timeout: float | None=None, inferences: int | None=None', returns='list[list[Atom]]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_load'),
        docs=(
            'Add a text program or trusted fast cache to this space.\n'
            '\n'
            'This is a consult, so it always loads and what it loads REPLACES\n'
            'what the same file put in this space before. Edit the file, load it\n'
            'again, and the space holds the new definitions and not both; the\n'
            'engine says on stderr which file it replaced and how many atoms\n'
            'went. Atoms from other sources, and ones you added yourself, stay.\n'
            'A load that raises leaves the previous definitions standing, so a\n'
            'broken edit costs nothing but the error.\n'
            '\n'
            '`!(import! &self path)` is the other form and loads a file that is\n'
            'new or edited, skipping one that is neither. The two agree on what\n'
            'a reload means and differ only in whether an unchanged file runs\n'
            "again, which is SWI's consult/1 against its if(changed).\n"
            '\n'
            'A .gz path is detected and read through the decompressed bytes.\n'
            '\n'
            '`timeout` (seconds) and `inferences` (engine steps) bound the load\n'
            "with the engine's own guards, raising TimeLimitError or\n"
            'InferenceLimitError. A load is all or nothing: a stop takes back\n'
            'everything the file had put in a space, the same way a load that\n'
            'fails on a bad form does, because a file the space holds half of is\n'
            'not a file it can replace later. run() is the entry point that\n'
            'keeps finished work when a bound stops it. This is the one most\n'
            'likely to be handed code the caller did not write, since a file can\n'
            'carry `!` directives and an import graph, so it takes the same pair\n'
            'its siblings take.\n'
            '\n'
            'Program text with holes is refused here. A hole is a binding, and a\n'
            'PATH has nowhere to bind one: run() takes holes, and an f-string or a\n'
            'Path builds a computed filename.\n'
        ),
        evidence=('extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_refuses_while_a_load_is_in_flight', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_second_load_of_a_specialized_program_still_round_trips', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_load_adds_to_existing_space'),
        alias='load',
    ),
    Door(
        owner=Owner.space,
        name='parse',
        kind=Kind.introspection,
        signatures=(
            Signature('self, source: str | TemplateLike, /, **values: Any', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_parse'),
        docs=(
            'Read one form into an atom without evaluating it.\n'
            '\n'
            'Holes work here as they do at run(), and land in the term this\n'
            'answers rather than crossing to the engine, since nothing runs:\n'
            '`m.parse(t"(person {name} 36)")` is the built term with the value\n'
            'already in it.\n'
        ),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_registered_token_class_parses_like_a_shipped_one', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_token_constructor_failure_is_a_reader_error_not_a_symbol_fallback'),
        binding=Binding('metta_py_parse', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='register-token',
        kind=Kind.provider,
        signatures=(
            Signature('self, pattern: str | _re.Pattern[str], constructor: Callable[[str], Any]', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_register_token'),
        docs=(
            'Register a full-token regex and its Atom constructor.\n'
            '\n'
            'The constructor receives the complete matched lexeme. It may return an\n'
            'Atom or any value accepted by :func:`metta.ground`. A later registration\n'
            'of the same pattern replaces the constructor. Only future parses read\n'
            'the new mapping; atoms already returned are immutable values.\n'
        ),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_registered_token_class_parses_like_a_shipped_one', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_compiled_reader_patterns_preserve_flags_and_unregister', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_token_constructor_failure_is_a_reader_error_not_a_symbol_fallback'),
        binding=Binding('metta_py_register_token', Wire.goal),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:register-token]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='unregister-token',
        kind=Kind.provider,
        signatures=(
            Signature('self, pattern: str | _re.Pattern[str]', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_unregister_token'),
        docs=(
            'Remove a reader-token class; an absent pattern is already removed.\n'
        ),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_compiled_reader_patterns_preserve_flags_and_unregister', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_registered_token_class_parses_like_a_shipped_one', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_token_constructor_failure_is_a_reader_error_not_a_symbol_fallback'),
        binding=Binding('metta_py_unregister_token', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='add',
        kind=Kind.write,
        signatures=(
            Signature('self, *atoms: Any', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_add'),
        docs=(
            'Add atoms to this space, one engine round-trip for the lot.\n'
            'An (= ...) atom compiles as an equation. Every Atom shape crosses\n'
            'unchanged, including a bare Symbol, Grounded value, and empty\n'
            "Expression; a free Variable receives the engine's own\n"
            'insufficient-instantiation refusal. The MeTTa longhand is\n'
            '`!(add-atoms <space> (<atom> ...))`. It is NOT `add-atom`, which is\n'
            "upstream PeTTa's spelling and takes upstream's domain: a headless atom\n"
            'cannot become a fact in a space there, so `!(add-atom &self b)` has no\n'
            'answer on either engine. This space is wider and `add-atoms` is the\n'
            'door onto the wider part.\n'
            '\n'
            "A variable's NAME is not stored. `(rule $x $y)` reads back as\n"
            '`(rule $_17902 $_17904)`, because a variable is an identity and not a\n'
            'spelling. That is the right property for a logic engine and it is the\n'
            'one thing about storage that surprises everybody once.\n'
            '\n'
            'A library IS knowledge, so the same operator imports it: ``m += lib.he``\n'
            'performs ``!(import! <m> (library lib_he))`` with this space as the\n'
            'target. An import is an effect, so it refuses to hide inside an atom\n'
            'batch or share a call with stored atoms.\n'
        ),
        evidence=('extensions/python/ext/metta-arrays/tests/test_arrays.py::test_embedding_store_validates_added_vectors', 'extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_add_atom_accepts_a_computed_space_handle', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_add_query_atoms'),
        alias='add',
        binding=Binding('metta_py_add_many', Wire.goal),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:add]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='remove',
        kind=Kind.write,
        signatures=(
            Signature('self, atom: Any, *more: Any', returns='bool | int'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_remove'),
        docs=(
            'Remove ONE unifying occurrence and say whether one was there,\n'
            "which is Python's own `list.remove` grain.\n"
            '\n'
            'Variadic like `add` and `transfer`: several atoms ride one engine\n'
            'crossing inside one transaction, and the answer counts the found,\n'
            'so the one-atom call still reads as the truth value it always\n'
            'was.\n'
            '\n'
            '`space -= atom` is this same grain without the report, the way\n'
            "`+=` is `add` without one: Python's in-place difference over a\n"
            'MULTISET, whose own Python spelling is `collections.Counter`,\n'
            'subtracts the multiplicity given rather than clearing the key.\n'
            'That is the only reading under which the operators are inverses,\n'
            'so `s += a; s -= a` leaves the space it found. `-=` classifies its\n'
            'operand exactly as `+=` does, so `-=` subtracts the same fact stream\n'
            '`+=` stores, one occurrence per element, in one\n'
            'transactional crossing.\n'
            '\n'
            '`del m[pattern]` is the draining form: it takes every\n'
            'unifying occurrence in one crossing and raises when nothing\n'
            "matched, as Python's `del` does, and MeTTa spells it `remove-atom`\n"
            '[source: engine/spaces/foreign.pl, remove_matching_atoms/2].\n'
            "MeTTa spells this method's grain `subtract-atom`. This is the one\n"
            'method that reports absence.\n'
            '\n'
            'A bare variable is the remove-everything reading a multiset space\n'
            'gives it, each atom leaving through its own proper path, equations\n'
            'and their compiled clauses included.\n'
        ),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_structures.py::test_matchindex_routes_and_removes', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_atoms_count_contains_remove_clear', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_delitem_removes_every_unifying_occurrence'),
        alias='remove',
        binding=Binding('metta_py_remove_many', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='transfer',
        kind=Kind.write,
        signatures=(
            Signature('self, *atoms: Any, to: Space', returns='int'),
        ),
        answers=AnswersAs.integer,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_transfer'),
        docs=(
            'Move ONE unifying occurrence of each atom into another space.\n'
            '\n'
            'Variadic and atomic: however many atoms ride the call, one engine\n'
            'transaction moves them in one crossing, so a mid-move failure\n'
            'rolls every side back and nothing is lost between the spaces. The\n'
            'answer counts the moved; an absent atom moves nothing and counts\n'
            "nothing, which is ``remove``'s own found-reporting grain, so the\n"
            'one-atom call still reads as a truth value. The longhand stays\n'
            'reachable: a :meth:`transaction` around ``remove`` and ``add``\n'
            'says the same thing one atom at a time. :meth:`take` is the\n'
            'WAITING kin for a pattern.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_variadic_doors.py::test_transfer_moves_a_batch_atomically',),
    ),
    Door(
        owner=Owner.space,
        name='atoms',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='list[Atom]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_atoms'),
        docs=(
            'Every stored atom in this space.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
        binding=Binding('metta_py_atoms', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='peek',
        kind=Kind.query,
        signatures=(
            Signature('self, pattern: Any, *, where: Any | None=None, deadline: float | None=None', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_peek'),
        docs=(
            'Wait for one matching atom and leave it in this space.\n'
            '\n'
            'A finite deadline raises ``Timeout`` when no match arrives.\n'
            '\n'
            "`where` is match()'s guard on a blocking wait: a term over the\n"
            "pattern's variables, evaluated once a candidate binds them and\n"
            'required true, so "wait for a job whose priority is above five" is one\n'
            'call. Without it the guard had to live in the caller, as a wait and a\n'
            're-wait around every candidate the guard rejected, and the deadline\n'
            'restarted each time round [measured 2026-08-31].\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_space_handle_peek_and_take_are_linda_verbs', 'extensions/python/tests/ch11_python_as_a_notation/test_library_fixes.py::test_peek_does_not_import_linda_into_the_waited_space', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_take_peek_and_watch_retire_the_thread_linda_fn_strings'),
    ),
    Door(
        owner=Owner.space,
        name='take',
        kind=Kind.write,
        signatures=(
            Signature('self, pattern: Any, *, where: Any | None=None, deadline: float | None=None', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_take'),
        docs=(
            'Wait for and remove exactly one matching atom from this space.\n'
            '\n'
            'Competing takers cannot receive the same occurrence. A finite\n'
            'deadline raises ``TimeoutError`` when no match arrives. `where` is\n'
            "peek()'s guard, and it is checked BEFORE the removal, so an atom the\n"
            'guard rejects stays where it is for whoever does want it.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_space_handle_peek_and_take_are_linda_verbs', 'extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_the_linda_verbs_take_matchs_guard', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_take_peek_and_watch_retire_the_thread_linda_fn_strings'),
    ),
    Door(
        owner=Owner.space,
        name='cast',
        kind=Kind.introspection,
        signatures=(
            Signature('self, type_: _builtins.type[_CastT], /', returns='_CastT', declarations=('overload',)),
            Signature('self, type_: Atom | str, /', returns='Any', declarations=('overload',)),
            Signature('self, value: Any, type_: _builtins.type[_CastT], /', returns='_CastT', declarations=('overload',)),
            Signature('self, value: Any, type_: Atom | str, /', returns='Any', declarations=('overload',)),
            Signature('self, value: Any, type_: Any=..., /', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_cast'),
        docs=(
            'Cast this space atom ambiently with one argument, or answer value\n'
            "narrowed by this space's type discipline with two arguments. The\n"
            "explicit form has the same acceptance a typed call compiles, ':'\n"
            'declarations here and &self in scope, protocol types included. A\n'
            "refusal raises metta.CastError naming the value's actual types.\n"
        ),
        evidence=('extensions/python/tests/ch01_getting_started/test_api_types.py::test_cast_target_is_positional_only', 'extensions/python/tests/ch09_types/test_casting.py::test_arrow_typed_expressions_cast_structurally', 'extensions/python/tests/ch09_types/test_casting.py::test_atom_cast_delegates_to_the_ambient_space'),
    ),
    Door(
        owner=Owner.space,
        name='trace',
        kind=Kind.scope,
        signatures=(
            Signature('self, source: Atom | str, max_events: int | None=None, *, filter: Symbol | str | Iterable[Symbol | str] | None=None, timeout: float | None=None, inferences: int | None=None', returns='Trace'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_trace'),
        docs=(
            "Run a TERM, or source, under the engine's reduction trace and\n"
            'answer TraceEvent records: what entered reduction at which depth,\n'
            'what it answered, and which reductions failed (a call with no\n'
            'exit). `m.trace(S.fib(10))` is the ordinary spelling, the same\n'
            'argument `answers` and `eval` take; a string is still a string.\n'
            'What is traced executes for real, writes included, like run();\n'
            'the wrap exists only while tracing, so untraced calls pay\n'
            'nothing and the wrapping itself is not charged to the bounds\n'
            'below. max_events bounds the RECORDING and timeout,\n'
            'inferences and stack bound the RUN, defaulting to whatever\n'
            '`m.limits()` scopes; they are independent because a program can\n'
            'retire millions of inferences inside a handful of recorded\n'
            'events. Whichever one stops it, the events already recorded are\n'
            'ANSWERED and `stopped` names the bound, so a caller told a trace\n'
            'was cut knows which bound to raise.\n'
            'filter selects exact function Symbols or names, singly or in an iterable.\n'
            'None records all functions; [] records none. Selection happens before\n'
            'the recording bounds, while excluded calls still execute and add depth.\n'
        ),
        evidence=('extensions/python/ext/metta-otel/tests/test_otel.py::test_a_reduction_a_bound_cut_ends_with_the_trace', 'extensions/python/ext/metta-otel/tests/test_otel.py::test_a_trace_becomes_one_span_per_reduction', 'extensions/python/ext/metta-otel/tests/test_otel.py::test_a_trace_inside_an_observed_block_refuses'),
        alias='trace',
    ),
    Door(
        owner=Owner.space,
        name='debug',
        kind=Kind.scope,
        signatures=(
            Signature('self, source: Atom | str, *, on: Any=None, inferences: int | None=None, at: int | None=None', returns='Debugger'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_debug'),
        docs=(
            'Run a TERM, or source, under breakpoints, stepped from Python.\n'
            '\n'
            'Iterating the Debugger runs the program to each breakpoint, the loop\n'
            'body is where the program is SUSPENDED, and leaving the body resumes\n'
            'that same execution:\n'
            '\n'
            '    with m.debug(S.quad(3), on=[S.double]) as d:\n'
            '        for stop in d:\n'
            '            print(stop)      # halted here\n'
            '            if stop.depth > 2:\n'
            '                d.step()     # stop at the next reduction instead\n'
            '        print(d.answers)\n'
            '\n'
            'on= names the functions that stop it, the way every door here names a\n'
            'head; naming none runs the program to the end in one advance.\n'
            '`step()` stops at the very next reduction, breakpoint or not, and\n'
            'lasts one advance. `breakpoints` is a live set, so one added while\n'
            'the program is suspended stops it.\n'
            '\n'
            'at= is the third kind of breakpoint, a COUNT: it stops at the event\n'
            'with that sequence number, numbering reductions from 0 the way a\n'
            'Recording numbers them, so `at=200` is "put me where event 200 is".\n'
            '`Recording.debug(at=k)` is the convenience over this one.\n'
            '\n'
            'inferences bound the WHOLE session cumulatively, so a resume that\n'
            'would never reach another breakpoint stops. There is no timeout:\n'
            'the session is suspended by design and a clock would run while a\n'
            'person reads a stop. What is debugged executes for real, writes\n'
            "included, and inherits the caller's scope. Close it, or leave its\n"
            'with-block: the session holds a wrapper on every compiled function\n'
            'until it does.\n'
        ),
        evidence=('extensions/python/ext/metta-otel/tests/test_otel.py::test_observing_inside_a_debug_session_refuses', 'extensions/python/tests/ch14_seeing_your_program/test_debug.py::test_a_breakpoint_inside_a_host_operation_refuses_with_its_remedy', 'extensions/python/tests/ch14_seeing_your_program/test_debug.py::test_a_breakpoint_suspends_the_program_and_resuming_carries_it_on'),
        alias='debug',
    ),
    Door(
        owner=Owner.space,
        name='record',
        kind=Kind.scope,
        signatures=(
            Signature('self, source: Atom | str, *, seed: int | None=None, max_events: int | None=None, timeout: float | None=None, inferences: int | None=None', returns='Recording'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_record'),
        docs=(
            'Run a TERM, or source, and keep the whole run as data.\n'
            '\n'
            'The data walks backwards, saves to a file, and re-runs.\n'
            '`m.trace` is the rung below: it answers the events alone. A Recording\n'
            'is those events plus the state that produced them, which is what makes\n'
            'them re-runnable rather than only readable:\n'
            '\n'
            '    rec = m.record(S.fib(12))\n'
            '    rec.save("fib.metta-rec.json")\n'
            '    rec.at(-1)               # the last event, with its call stack\n'
            '    rec.back()               # a step backwards costs a lookup\n'
            '    rec.replay(other)        # the same run, in another engine\n'
            '    with rec.debug(at=17) as d:   # live, stopped where event 17 is\n'
            '        print(d.stop)\n'
            '\n'
            'A recorded run always has a seed, minted when you do not name one,\n'
            'because a replay that cannot reproduce the draws is not a replay; the\n'
            'generator is restored afterwards. `(with-seed S expr)` is the MeTTa\n'
            'spelling of the same scope.\n'
            '\n'
            'max_events bounds the RECORDING and timeout and inferences bound the\n'
            'RUN, exactly as on trace(); a cut recording says so through\n'
            '`rec.events.stopped` and replays to the same length. A program whose\n'
            'effect plan reaches oracleIO is recorded with `replayable` false and\n'
            'the reason naming what it reached, and replay() then refuses rather\n'
            'than re-reading the host.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_recording.py::test_a_cut_recording_says_so_and_replays_to_the_same_length', 'extensions/python/tests/ch14_seeing_your_program/test_recording.py::test_a_file_that_is_not_a_recording_refuses_by_name', 'extensions/python/tests/ch14_seeing_your_program/test_recording.py::test_a_frame_outside_the_recording_refuses'),
        alias='record',
    ),
    Door(
        owner=Owner.space,
        name='lint',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='list[Finding]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_lint'),
        docs=(
            'Diagnose this space for the silently-wrong class: declared\n'
            'types nothing defines, arity mismatches, unbound body variables,\n'
            'duplicate equations, and references no function or fact carries.\n'
            'Answers metta.lint.Finding records, empty when nothing looks\n'
            'wrong.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_a_canonicalised_read_of_a_tabled_function_is_not_a_finding', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_a_declaration_for_a_name_with_no_equations_is_data', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_a_declaration_that_cannot_type_its_function'),
    ),
    Door(
        owner=Owner.space,
        name='effect-plan',
        kind=Kind.introspection,
        signatures=(
            Signature('self, target: Any', returns='_ops_module.EffectPlan'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_effect_plan'),
        docs=(
            'Return operations the target may execute and their joined effect.\n'
            '\n'
            'The engine translates the same atom or source form ``eval`` accepts,\n'
            'follows nested compiled calls, and reads current operation metadata.\n'
            'It does not execute the target. A later registration change is visible\n'
            'on the next call. This is the analysis reified-world admission uses.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_effect_plan.py::test_async_effect_plan_retains_the_sync_contract', 'extensions/python/tests/ch11_python_as_a_notation/test_effect_plan.py::test_effect_plan_reads_replaced_operation_classification', 'extensions/python/tests/ch11_python_as_a_notation/test_effect_plan.py::test_effect_plan_reports_nested_calls_without_executing_them'),
        binding=Binding('metta_py_world_effect_plan', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='copy',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self', returns='Space'),
        ),
        answers=AnswersAs.space,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_copy'),
        docs=(
            "This space's contents in a new anonymous space, cloned through\n"
            'one bulk write, so equations copy as equations and keep running:\n'
            '"a scratch space set up like production" is one line. The handle\n'
            "is ``space()``'s kind, so drop it, or use it as a context\n"
            'manager, to return the name. copy.copy(m) answers the same\n'
            'through the copy protocol. There is deliberately no __deepcopy__:\n'
            'stored Python objects keep their identity across the clone, the\n'
            'shallow reading, and a deep clone of a live engine handle has no\n'
            'meaning to promise.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_copy_reproduces_the_space_it_copied',),
    ),
    Door(
        owner=Owner.space,
        name='reify',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_reify'),
        docs=(
            'Capture this space as an immutable, independently evaluable world.\n'
        ),
        evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_reify_refuses_an_effectful_captured_compilation_before_replay', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_reify_refuses_and_names_a_live_composite_member', 'extensions/python/tests/ch11_python_as_a_notation/test_arrow_products.py::test_world_coverage_uses_the_annotated_effect'),
    ),
    Door(
        owner=Owner.space,
        name='commit',
        kind=Kind.write,
        signatures=(
            Signature('self, world: Any', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_commit'),
        docs=(
            "Apply one reified world's diff through this originating space.\n"
        ),
        evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_a_journaled_world_commit_replays_its_ordinary_diff', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_commit_applies_the_world_diff_as_post_commit_events', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_world_commit_preserves_multiplicity_and_refuses_stale_or_wrong_origins'),
    ),
    Door(
        owner=Owner.space,
        name='digest',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_digest'),
        docs=(
            "A sha256 hex digest of this space's content: every stored atom,\n"
            'equations included, canonicalized (variables numbered, multiset\n'
            'sorted) so the same atoms answer the same digest in any insertion\n'
            'order and in any process. Two spaces agree on digest() exactly\n'
            'when save() would write the same content. Live host objects have\n'
            'no cross-process identity and are refused, like save().\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_second_load_of_a_specialized_program_still_round_trips', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_specialized_program_saves_and_digests', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_digest_counts_duplicates'),
        binding=Binding('metta_py_digest', Wire.goal),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_digest_refuses_an_invalid_engine_reply'),
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_digest_refuses_live_host_identity'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='__len__',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='int'),
        ),
        answers=AnswersAs.integer,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___len__'),
        docs=(
            'Read Space.__len__.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    ),
    Door(
        owner=Owner.space,
        name='__bool__',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='bool'),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___bool__'),
        docs=(
            'Always true: a space is a handle to a store, not a value that\n'
            'dwindles. Without this, bool() falls through to __len__ and an\n'
            'empty space is falsy, so `if space:` skips a perfectly good empty\n'
            'space, the bug class that made datetime stop treating midnight as\n'
            'false in 3.5. Existence is an ask: use\n'
            '``bool(space.match(V.x))`` rather than ``bool(space)``.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
    ),
    Door(
        owner=Owner.space,
        name='__contains__',
        kind=Kind.introspection,
        signatures=(
            Signature('self, atom: Any', returns='bool'),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___contains__'),
        docs=(
            'Read Space.__contains__.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    ),
    Door(
        owner=Owner.space,
        name='clear',
        kind=Kind.write,
        signatures=(
            Signature('self', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_clear'),
        docs=(
            'Remove everything stored here, compiled equations included.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_atoms_count_contains_remove_clear', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_clear_removes_equations_too', 'extensions/python/tests/ch05_equations_and_evaluation/test_reload.py::test_a_cleared_space_forgets_what_a_file_put_in_it'),
        binding=Binding('metta_py_clear', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='__iadd__',
        kind=Kind.write,
        signatures=(
            Signature(parameters='self, atom: Any', returns='Self', type_parameters='', declarations=(), type_ignores=('override',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___iadd__'),
        docs=(
            "add()'s operator spelling for one atom or one fact stream.\n"
            '\n'
            '``m += (S.Edge, a, b)`` adds one fact. ``m += [(S.Edge, a, b),\n'
            '(S.Edge, b, c)]`` and a generator yielding those rows add two. A built\n'
            'Expression is always one atom even though it implements Sequence.\n'
            'Dataframes use ``iter_rows`` or ``itertuples(index=False)``. The\n'
            'explicit ``add(list_value)`` method remains available when a list itself\n'
            'is intended as one transparent expression.\n'
            '\n'
            'Relative ``S.admits(Type)``, ``S.capacity(n)``, and\n'
            '``S.covers(effect)`` values are declared data: they install the same\n'
            'contract as the receiver methods and are not stored in this space.\n'
            'Explicit ``add(...)`` remains the raw storage method for those shapes.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
        context_inplace=True,
    ),
    Door(
        owner=Owner.space,
        name='__isub__',
        kind=Kind.write,
        signatures=(
            Signature(parameters='self, atom: Any', returns='Self', type_parameters='', declarations=(), type_ignores=('override',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___isub__'),
        docs=(
            'Read Space.__isub__.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
        context_inplace=True,
    ),
    Door(
        owner=Owner.space,
        name='__ior__',
        kind=Kind.write,
        signatures=(
            Signature(parameters='self, other: Any', returns='Self', type_parameters='', declarations=(), type_ignores=('override',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___ior__'),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:__ior__]'),
        ),
        docs=(
            'Merge into this space in one bulk crossing: every atom of\n'
            'another space, of a registered space name, or of an iterable.\n'
            '\n'
            '    m |= other_space     # every atom, equations included\n'
            '    m |= "&kb"           # the space registered under this name\n'
            '    m |= [a, b, c]       # each element becomes one atom\n'
            '\n'
            'Equations in the merge compile on arrival, the same rule add()\n'
            'enforces. A space is a multiset, so merging a space into itself\n'
            'doubles every atom. A Mapping is refused because add(d) reads the\n'
            'same dict as ONE grounded atom and its values would silently\n'
            'vanish here; spell the reading you mean. Strings name spaces, so\n'
            'an unregistered name is a KeyError rather than a parse.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
        context_inplace=True,
    ),
    Door(
        owner=Owner.space,
        name='__iter__',
        kind=Kind.introspection,
        signatures=(
            Signature('self'),
        ),
        answers=AnswersAs.stream,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___iter__'),
        docs=(
            'Iterate one assembly-order snapshot of the stored atoms.\n'
            '\n'
            'A native or inherited-native space materializes its readable chain\n'
            'when ``iter(space)`` is called, so later additions and removals do not\n'
            'alter that iterator. A Python-backed space likewise materializes its\n'
            "provider's ``atoms()`` result before returning the iterator; the\n"
            'provider owns and must document how concurrent mutation behaves while\n'
            'that one enumeration itself is being produced.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space_container_protocol.py::test_native_iteration_snapshots_before_mutation',),
    ),
    Door(
        owner=Owner.space,
        name='__getitem__',
        kind=Kind.introspection,
        signatures=(
            Signature('self, i: Any', returns='Rows'),
        ),
        answers=AnswersAs.rows,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___getitem__'),
        docs=(
            'Subscription is query. A tuple headed by an atom is one built\n'
            'expression pattern; a tuple of complete expression patterns is a join:\n'
            '\n'
            '    m[(S.Parent, V.x, S.Bob)]\n'
            '    m[S.edge(V.a, V.b), S.edge(V.b, V.c)]\n'
            '\n'
            'Python hands both spellings to ``__getitem__`` as a tuple, so shape is\n'
            'the visible classifier. A mixed tuple beginning with a complete\n'
            'pattern and followed by a bare atom can only be the tuple mistake; it\n'
            'raises and names the one-pattern and join spellings instead of\n'
            'silently asking an impossible bare-atom conjunct.\n'
            '\n'
            "A str key parses first, matching match()'s tolerance. A slice is\n"
            'refused: a slice of a space has no one meaning, and the bounded\n'
            'readings have their own methods, match(limit=) for a bounded answer\n'
            'set and stream() for rows pulled until you have seen enough.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:__getitem__]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='__delitem__',
        kind=Kind.write,
        signatures=(
            Signature('self, pattern: Any', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.context,),
        body=Body('metta._space', 'Space._door___delitem__'),
        docs=(
            'Del m[pattern] removes every unifying occurrence, the bulk\n'
            "spelling of remove()'s multiset subtraction: m[pattern] is a\n"
            'query answering many rows, so deleting it deletes them all, the\n'
            'way DELETE WHERE does. Nothing unifying raises KeyError, as\n'
            'del d[k] does on a missing key; remove() is the method that\n'
            'reports absence as False instead.\n'
            '\n'
            "It asks the engine's own drain, so the whole pattern costs ONE\n"
            'crossing rather than one per removed atom.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    ),
    Door(
        owner=Owner.space,
        name='match',
        kind=Kind.query,
        signatures=(
            Signature('self, *patterns: Any, where: Any | None=None, limit: int | None=None, timeout: float | None=None, inferences: int | None=None, under: Any=_UNSET, into: _builtins.type | None=None, **values: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_match'),
        docs=(
            'Lazily match patterns against this space as one conjunction.\n'
            '\n'
            "Variables shared between patterns join, the engine's own match/4\n"
            'doing the joining. Columns are the variable names in first\n'
            'appearance order. `where` is a guard term over the same variables,\n'
            'evaluated per join and required true, so restrictions a pattern\n'
            'cannot spell (an inequality) compose onto the match:\n'
            '\n'
            '    m.match(S.person(V.name, V.age), where=V.age.ge(18))\n'
            '\n'
            '`limit` bounds the answers, the engine stopping at the count\n'
            'rather than trimming afterwards. `timeout` (seconds) and\n'
            '`inferences` (engine steps) bound the whole call, raising\n'
            'TimeLimitError or InferenceLimitError when hit, for joins whose\n'
            'size is not known in advance.\n'
            '\n'
            'The returned Answers view pulls only what Python observes. ``bool``\n'
            'pulls one row, exact-one operations pull at most two, and slicing\n'
            'retains an Answers view. ``len`` uses an engine-side aggregate when\n'
            'no row has yet been pulled.\n'
            '\n'
            '``under=`` interprets the same ask through an annotation algebra.\n'
            '``under=counting`` answers one ``TaggedAnswer`` whose annotation is\n'
            'the engine-computed count, including duplicate derivations without\n'
            'crossing their rows into Python. Ordered carriers sort in their\n'
            'declared direction before slicing, so\n'
            '``m.match(q, under=ranked)[:3]`` is top-k and\n'
            '``under=tropical`` puts the cheapest annotation first. Other carriers\n'
            'answer ``TaggedAnswer`` values with ``annotation``, ``why()`` and\n'
            '``under(other)``; the latter two reuse the retained derivation rather\n'
            'than querying the space again. ``with metta.under(carrier)`` supplies\n'
            'the carrier when this call has no explicit ``under=``.\n'
            '\n'
            '`into=Rows` explicitly chooses the eager Rows face. Other `into=`\n'
            'values shape each row into a dataclass, NamedTuple, or\n'
            "TypedDict matched by field name, sqlite3's row_factory reading:\n"
            '`m.match(S.edge(V.a, V.b), into=Edge)` answers `list[Edge]`,\n'
            'and Rows stays the default so nothing is lost. A one-variable query\n'
            'whose column holds complete constructor expressions rebuilds those\n'
            'expressions instead: `m.match(V.edge, into=Edge)`.\n'
            '\n'
            '    m.match(S.Edge(V.x, V.y), S.Edge(V.y, V.z))\n'
            '\n'
            "A text pattern may carry HOLES, as run()'s source may:\n"
            '`m.match(t"(person {name} $age)")` matches the value itself, so a name\n'
            'holding a space stays one String atom rather than reading as two\n'
            'symbols. Keyword values apply across every pattern of the call.\n'
        ),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_identity_wire.py::test_store_and_match_preserve_python_object_identity', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_drop_retires_algebra_before_redeclaration', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_recorded_session_replays_verbatim'),
        alias='match',
    ),
    Door(
        owner=Owner.space,
        name='stream',
        kind=Kind.query,
        signatures=(
            Signature('self, *patterns: Any, where: Any | None=None, limit: int | None=None, timeout: float | None=None, inferences: int | None=None, under: Any=_UNSET', returns='Cursor'),
        ),
        answers=AnswersAs.stream,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_stream'),
        docs=(
            'match(), pulled: the same conjunction and guard, answered one\n'
            'row at a time through a cursor the engine holds open.\n'
            '\n'
            '    with m.stream(S.edge(V.a, V.b), S.edge(V.b, V.c)) as rows:\n'
            '        for row in rows:\n'
            '            if wanted(row):\n'
            '                break            # nothing further is even joined\n'
            '\n'
            "The join's state lives inside an SWI engine between pulls, each\n"
            'pull is one ordinary call, and unrelated calls interleave freely,\n'
            'so a huge join costs one row of work per row actually taken where\n'
            'match() computes and decodes every answer up front. `timeout`\n'
            "bounds each pull's wall time; `inferences` is one budget for the\n"
            "cursor's whole engine work, spent across pulls, and the cursor\n"
            'stops on the answer that passes it. Because the budget counts the\n'
            "cursor's own engine, it is not the number ``stats()`` reports for\n"
            "the same work: ``stats()`` reads the calling thread's counters,\n"
            'which see the pull loop rather than the engine. The cursor\n'
            "enumerates under the engine's logical update view: writes made\n"
            'after the first pull are not seen by this cursor.\n'
            '\n'
            '`limit` and `under` mean what they mean on match(), because this is\n'
            'match() and the cursor underneath already carried both: a tagging\n'
            'algebra (ranked, tropical, prov) answers one TaggedAnswer per pull,\n'
            "the same value match() answers. `under='counting'` is refused by\n"
            'name, because a counting fold is ONE aggregate over the whole answer\n'
            'set and a cursor exists not to have one.\n'
            '\n'
            "What this method does NOT take is match()'s `into=`, the same kind of\n"
            'difference: `into` builds a container out of every row.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_wide_query_projection_is_identical_through_every_answer_door', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_nonpositive_limits_are_refused_by_match_stream_and_prepared'),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:stream]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='assuming',
        kind=Kind.scope,
        signatures=(
            Signature('self, *facts: Any', returns='_Assuming'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_assuming'),
        docs=(
            'Facts held only inside a with-block: the assumptions reading of\n'
            'a what-if query, added on entry, removed on exit, exceptions\n'
            'included.\n'
            '\n'
            '    with m.assuming(S.closed(S.bridge)):\n'
            '        detour = m.match(S.route(V.r), where=...)\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_assuming_groups_multiple_cleanup_failures_after_removing_all', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_assuming_removes_every_fact_after_one_cleanup_fails', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_assuming_scopes_facts'),
    ),
    Door(
        owner=Owner.space,
        name='transaction',
        kind=Kind.scope,
        signatures=(
            Signature('self, target: Callable[[], _R], /', returns='_R', declarations=('overload',)),
            Signature('self, target: Atom | str, /', returns='list[Atom | Undefined]', declarations=('overload',)),
            Signature('self, target: Callable[[], _R] | Any, /', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_transaction'),
        docs=(
            'Run one callable or term inside a closed engine transaction.\n'
            '\n'
            'The two inputs preserve their native failure laws. A zero-argument\n'
            'Python callable commits its return value and rolls back on a Python\n'
            'exception. A term returns its engine answers and rolls back when that\n'
            'answer set is empty, exactly like ``(transaction ...)``.\n'
            '\n'
            '    m.transaction(lambda: migrate(m))\n'
            '    m.transaction(S.progn(write, verify))\n'
            '\n'
            'Every engine write the callable makes, stored atoms, equations\n'
            'and their compiled clauses included, commits or rolls back\n'
            "together. An exception is the callable's rollback trigger, because a\n"
            'Python callable cannot fail the Prolog way, and it re-raises AS\n'
            'ITSELF: your ValueError arrives as ValueError with the engine\n'
            "boundary in its chain. Only the engine's dynamic state rolls\n"
            'back; what the callable did on the Python side (a list appended,\n'
            'a file written) is yours to undo, SWI transactions being\n'
            'database-scoped.\n'
            '\n'
            "Transactions nest, SWI's own semantics: an inner commit is\n"
            'relative to its outer transaction, so an outer rollback discards\n'
            'inner work too.\n'
            '\n'
            "There is deliberately no `with m.transaction():` form. SWI's\n"
            'transaction/1 takes a closed goal; there is no open begin/commit\n'
            'to hold across a block, and pretending otherwise would lie about\n'
            'the isolation actually provided. transactional() is the\n'
            'decorator twin.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_composes_with_transaction', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_transaction_term_uses_empty_answer_rollback_law', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_saga_refuses_transaction_speculation_and_batch_boundaries'),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_transaction_refuses_an_unreported_engine_failure'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='saga',
        kind=Kind.scope,
        signatures=(
            Signature('self, receipts: Space'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_saga'),
        docs=(
            'Open a committed-receipt saga over this execution space.\n'
            '\n'
            '``receipts`` is an ordinary space that stores ``(did op args result)``\n'
            "atoms. Run each forward term with the returned context manager's\n"
            '``run`` method. A normal exit keeps its work and receipts; an\n'
            'exceptional exit invokes declared compensations in reverse commit\n'
            'order and removes each successfully recovered receipt.\n'
            '\n'
            '    with orders.saga(receipts) as saga:\n'
            '        saga.run(S.charge(S.order_7))\n'
            '\n'
            'Operations ranked writesState or oracleIO leave receipts. Declare a\n'
            'handler with ``compensates`` before recovery. Handlers receive the\n'
            'complete receipt, written at the call site as ``(quote <receipt>)`` so\n'
            'it is not evaluated on the way in, and must be idempotent, because a\n'
            'failed compensation remains queryable and is retried by\n'
            '``rollback()``.\n'
        ),
        evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_a_discarded_step_runs_no_compensation', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_a_failed_compensation_can_be_retried_without_losing_its_receipt', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_a_lost_participant_leaves_the_saga_in_doubt_rather_than_compensating'),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:saga]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='solve',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, pattern: Any, subject: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_solve'),
        docs=(
            'Run relational ``let`` and return bindings keyed by its variables.\n'
            '\n'
            "``solve(4, V.x - 1).x`` places the known value on let's pattern side,\n"
            'lets the arithmetic relation solve backwards, and projects ``x``.\n'
            "The answer template is derived from the pattern's variables followed\n"
            'by any new subject variables, so either relational direction can\n'
            'introduce the bindings and the third hand-written ``let`` argument\n'
            'disappears.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_library_fixes.py::test_solve_projects_variables_from_the_winning_pattern', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_set_is_the_unique_image_of_solve_answers', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_solve_refuses_an_anonymous_only_subject'),
        alias='solve',
        refuses=(
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:solve]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='watch',
        kind=Kind.scope,
        signatures=(
            Signature('self, pattern: Any, *, on: SubscriptionEdge=SubscriptionEdge.add, where: Any | None=None, deadline: float | None=None, queue_max: int | None=None'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_watch'),
        docs=(
            'Yield matching changes, raising Timeout after each quiet deadline.\n'
            '\n'
            '`queue_max` bounds the subscription underneath, the same bound\n'
            'subscribe() takes; a watch could not name it before, though the\n'
            'subscription it builds always had one.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_take_peek_and_watch_retire_the_thread_linda_fn_strings', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_watch_close_before_first_event_cancels_its_eager_subscription', 'extensions/python/tests/ch16_events_and_standing_queries/test_events.py::test_an_abandoned_watch_cancels_itself'),
    ),
    Door(
        owner=Owner.space,
        name='limits',
        kind=Kind.scope,
        signatures=(
            Signature('self, *, timeout: float | None=None, inferences: int | None=None, stack: int | None=None', returns='ScopedLimits'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_limits'),
        docs=(
            'Scoped default bounds for every call in the with-block:\n'
            '\n'
            '    with m.limits(inferences=1_000_000, timeout=2.0):\n'
            '        m.match(...)      # bounded without saying so again\n'
            '\n'
            "decimal.localcontext's shape, contextvars underneath, so the\n"
            'scope is async-correct and per-task. A per-call timeout= or\n'
            'inferences= still overrides, which is the whole ladder: one\n'
            'block replaces the parameter forest, and the forest remains\n'
            'for whoever wants per-call control.\n'
            '\n'
            "stack= is SWI's combined stack ceiling in BYTES, the bound a\n"
            'runaway recursion hits as a StackOverflow error atom. It is NOT\n'
            "MeTTa's reduction depth: that is the max-stack-depth pragma,\n"
            '`(with-pragma! ((max-stack-depth N)) expr)`, which counts\n'
            'reduction steps and is scoped in the program text.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_scoped_limits_apply_and_per_call_overrides', 'extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_scoped_limits_validate_at_the_block', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_aio.py::test_aio_scoped_limits_cross_to_the_worker'),
        alias='limits',
    ),
    Door(
        owner=Owner.space,
        name='capture',
        kind=Kind.scope,
        signatures=(
            Signature('self', returns='CapturedOutput'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_capture'),
        docs=(
            'Collect printed engine text without changing answer shapes.\n'
            '\n'
            'with m.capture() as output:\n'
            '    groups = m.run("!(println! hello) !(+ 1 2)")\n'
            'assert groups == [[3]]\n'
            'assert output.text == "hello\\n"\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_capture_composes_with_limits', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_eval_capture', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_capture_collects_held_engine_output'),
    ),
    Door(
        owner=Owner.space,
        name='atomic',
        kind=Kind.scope,
        signatures=(
            Signature('self', returns='ScopedExecution'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_atomic'),
        docs=(
            'Make each CALL in the block one committing engine transaction.\n'
            '\n'
            'Per call, the write doors included: ``m.add(a, b)`` inside the block\n'
            'is one transaction, so a provider that refuses the second atom takes\n'
            'the first back with it. Across SEVERAL calls the boundary is\n'
            ":meth:`transaction`, because SWI's transaction/1 takes a closed goal\n"
            'and an engine cannot yield out of one, so no with-block can hold one\n'
            'open; a raise later in the block does not undo a call that already\n'
            'committed.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_an_atomic_scope_makes_one_python_write_one_transaction', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_atomic_run_commits_or_rolls_back_whole', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_atomic_rolls_back_after_a_late_cursor_failure'),
    ),
    Door(
        owner=Owner.space,
        name='speculative',
        kind=Kind.scope,
        signatures=(
            Signature('self', returns='ScopedExecution'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_speculative'),
        docs=(
            'Run each CALL against a snapshot and discard its writes.\n'
            '\n'
            'Per call, the write doors included: ``m.add(atom)`` inside the block\n'
            'leaves nothing behind, exactly as ``m.run("!(add-atom &self ...)")``\n'
            'in the same block does, and a later call in the block does not see\n'
            'what an earlier one wrote, because each call is its own what-if.\n'
        ),
        evidence=('extensions/python/tests/ch08_data/test_state_cell.py::test_speculative_state_write_is_fenced', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_every_public_execution_door_honours_speculative_policy', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_speculative_lazy_execution_preserves_every_answer'),
        alias='speculate',
    ),
    Door(
        owner=Owner.space,
        name='batch',
        kind=Kind.scope,
        signatures=(
            Signature('self', returns='_Batch'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_batch'),
        docs=(
            "Collect this space's add() calls and cross once at exit:\n"
            '\n'
            '    with m.batch():\n'
            '        for edge in edges:\n'
            '            m.add(edge)          # collected, no crossing yet\n'
            '    # one add_many crossing happened here\n'
            '\n'
            'The write forms are add for one or several atoms, batch for a region,\n'
            "transaction for all-or-nothing work, and a provider's bulk method\n"
            'underneath them. A batch is a transport economy and must not invent\n'
            'semantics, so the sharp edges are stated and enforced: reads\n'
            'inside the block see the space WITHOUT the pending adds; a\n'
            'remove() or clear() on this space inside the block refuses,\n'
            'because it would otherwise silently order around writes the\n'
            'program already made; and an exception discards the pending\n'
            'batch rather than landing writes the code after the raise never\n'
            'saw. Compose with transaction() for atomicity: batch for\n'
            'economy, transaction for all-or-nothing, or both.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_composes_with_transaction', 'extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_crosses_once_and_reads_see_the_pre_batch_space', 'extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_edges_are_enforced'),
    ),
    Door(
        owner=Owner.space,
        name='transactional',
        kind=Kind.scope,
        signatures=(
            Signature('self, fn: Callable[_P, _R], /', returns='Callable[_P, _R]'),
        ),
        answers=AnswersAs.callable,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_transactional'),
        docs=(
            "transaction()'s decorator twin, the atomic shape Django made\n"
            'familiar: each CALL of the wrapped function runs inside its own\n'
            'engine transaction. Decorating runs nothing, exactly as a\n'
            'decorator should not; reach for transaction() to run one\n'
            'callable now.\n'
            '\n'
            '    @m.transactional\n'
            '    def migrate():\n'
            '        m.add(...)\n'
            '        m.remove(...)\n'
            '\n'
            '    migrate()     # one transaction; a raise rolls it all back\n'
        ),
        evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_transaction.py::test_transactional_is_the_decorator_twin',),
        async_excluded="a transaction body is a closed synchronous goal, SWI's transaction/1 takes one; transaction() is the async spelling, and there is no decorator because decoration cannot await",
        state=State.any,
    ),
    Door(
        owner=Owner.space,
        name='prepare',
        kind=Kind.query,
        signatures=(
            Signature('self, *patterns: Any, where: Any | None=None', returns='Prepared'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_prepare'),
        docs=(
            'A query whose shape is fixed and whose facts are not: the wire\n'
            'form and columns build once, and each solve() may bring per-call\n'
            'facts (given=) that leave nothing behind.\n'
            '\n'
            '    route = m.prepare(S.path(V.a, V.b), where=V.a != ...)\n'
            '    route.solve()\n'
            '    route.solve(given=[S.edge(S.x, S.y)])\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_nonpositive_limits_are_refused_by_match_stream_and_prepared', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_prepared_query_with_given', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_limits_on_query_eval_value_and_prepared'),
    ),
    Door(
        owner=Owner.space,
        name='eval',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, target: Any, /, *more: Any, timeout: float | None=None, inferences: int | None=None, under: Any=_UNSET, theory: Any | None=None, interpreter: Any | None=None, answer: EvaluationAnswer | str = "all", delivery: ArgumentDelivery | str, limit: int | None = None, image: ImageMode | str | None = None, on_error: OnError | str = "keep", determinism: Determinism | str = "nondet", **values: Any', returns='Any', declarations=('overload',)),
            Signature(parameters='self, target: Any, /, *more: Any, timeout: float | None=None, inferences: int | None=None, under: Any=_UNSET, theory: Any | None=None, interpreter: Any | None=None, answer: EvaluationAnswer | str, delivery: ArgumentDelivery | str = "atoms", limit: int | None = None, image: ImageMode | str | None = None, on_error: OnError | str = "keep", determinism: Determinism | str = "nondet", **values: Any', returns='Any', type_parameters='', declarations=('overload',), type_ignores=()),
            Signature(parameters='self, target: Any, /, *, timeout: float | None=..., inferences: int | None=..., under: Any=..., theory: Any | None=..., interpreter: Any | None=..., **values: Any', returns='list[Atom | Undefined]', type_parameters='', declarations=('overload',), type_ignores=()),
            Signature(parameters='self, target: Any, _second: Any, /, *more: Any, timeout: float | None=..., inferences: int | None=..., under: Any=..., theory: Any | None=..., interpreter: Any | None=..., **values: Any', returns='list[list[Atom | Undefined]]', type_parameters='', declarations=('overload',), type_ignores=()),
            Signature(parameters='self, target: Any, /, *more: Any, timeout: float | None=None, inferences: int | None=None, under: Any=_UNSET, theory: Any | None=None, interpreter: Any | None=None, answer: EvaluationAnswer | str = "all", delivery: ArgumentDelivery | str = "atoms", limit: int | None = None, image: ImageMode | str | None = None, on_error: OnError | str = "keep", determinism: Determinism | str = "nondet", **values: Any', returns='Any', type_parameters='', declarations=(), type_ignores=()),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_eval'),
        docs=(
            'Evaluate a term, returning every answer.\n\nThis is what !(...) runs, minus the printing: the engine\'s\ntranslate_expr over the term, then its goals. Nondeterminism means\nthe list can hold any number of answers, including none.\n\nVariadic, and that is how evaluation BATCHES: several terms ride\none engine crossing and the answer is one group per term in call\norder, run()\'s own grouping carried to the term form. One term\nkeeps its flat list, so the scalar reading never changes shape.\n\nEvery answer carries its truth: an answer that is undefined under\nWell Founded Semantics (a tabled loop through tnot, reachable via\ntranslatePredicate or injected Prolog) arrives as an Undefined\nholding the answer and the delay condition that makes it\nundefined, never as an ordinary-looking value. A term to which no\nrule applies is the ordinary answer itself; `eval_status()` names\nthat path `not-reducible`. run() does not carry the third truth\nvalue; evaluate through eval() when it matters.\n\nA text target may carry HOLES, exactly as run()\'s source may:\n`m.eval(t"(decide {tensor})")` and `m.eval("(decide {x})", x=tensor)`\nhand the object itself to the rule, by identity. One call\'s holes are\nnumbered together, so a batch and a nested template cannot collide.\n\n`bind()` binds named host values into the term before it evaluates,\nexactly as it does for run(): inside `with m.bind({"x": tensor})`,\n`m.eval("(decide x)")` hands the tensor itself to the rule, by\nidentity, rather than a printed form of it. The name is the SYMBOL x\nand not the variable $x, in this call and the source form alike. The\nevaluation calls take the same vocabulary as the source form, so using\na term instead of source text costs no change of spelling.\n\nA key may be a NAME or an ATOM. A name means the symbol of that name,\nwhich is what the engine\'s own substitution matches and what run()\ntakes. An atom means exactly that atom, so `bind({V.x: 5})` fills a\nVARIABLE hole -- the one substitution `unify` reports and the one no\nevaluation call could apply, because a variable crosses the wire as [\'v\', \'x\']\nwhere a symbol crosses as [\'s\', \'x\'] and the engine matches names.\n\n`timeout` (seconds) and `inferences` (engine steps) bound the call,\nraising TimeLimitError or InferenceLimitError when hit. A surrounding\n`capture()` scope collects printed text without changing the list.\n\n`under`, `theory` and `interpreter` are answers()\' three, and mean\nexactly what they mean there; `eval()` materialises that query as a list. A\nsurrounding `with metta.under(carrier)` reaches here too, which it did\nnot before: match() and answers() both honoured such a scope while\neval() ignored it in silence.\n\nThe answer, delivery, limit, image, on_error and determinism options\nselect one evaluation contract. answer=answers retains a replayable\ncursor; answer=stream returns a closable single-pass stream. count,\nexists and none consume only the requested shape. A determinism\npromise is checked before a limit truncates the answers. Image\nprojection publishes the type declarations its values require.\n'
        ),
        evidence=('extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_preserve_the_eager_kernel', 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_compose_without_losing_answers'),
        alias='eval',
        binding=Binding('metta_py_eval_all', Wire.goal),
        refuses=(
            Refusal(RefusalKind.assertion, 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_check_cardinality_before_truncation'),
            Refusal(RefusalKind.inference_limit, 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_preserve_bounds_and_capture'),
            Refusal(RefusalKind.value, 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_refuse_invalid_values'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='answers',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, target: Any, /, *, timeout: float | None=None, inferences: int | None=None, under: Any=_UNSET, theory: Any | None=None, interpreter: Any | None=None, **values: Any', returns='Answers[Any]'),
        ),
        answers=AnswersAs.answers,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_answers'),
        docs=(
            'Evaluate lazily as an immutable, cached and replayable view.\n'
            '\n'
            'Creating the view performs no engine work. Existence pulls at most\n'
            'one answer, ``one()`` at most two, and ordinary iteration resumes the\n'
            'same held evaluation [tested:\n'
            'test_function_calls_pull_engine_answers_only_as_demanded;\n'
            'commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4].\n'
            '\n'
            '``under=`` has the same carrier semantics as ``match``. In\n'
            'particular, ``space.answers(call, under=counting).one()`` returns one\n'
            "``TaggedAnswer`` whose annotation counts the call's answer\n"
            'derivations inside the engine, and ordered carriers\n'
            'order their annotated ``TaggedAnswer`` values before a slice pulls\n'
            'its prefix. A surrounding ``metta.under(carrier)`` is used only when\n'
            'this call does not pass an explicit carrier.\n'
            '\n'
            '``theory=`` treats an atom or iterable of atoms as the theory value for\n'
            "this ask. That value replaces the receiver's own equational program.\n"
            'Engine builtins and the shared ``&self`` session space remain in scope\n'
            'exactly as they are for every space, and names the theory defines\n'
            'shadow inherited ones. It installs the theory in an isolated scratch\n'
            'space on the first pull, evaluates there, and drops the space when the\n'
            'view is exhausted or abandoned. The receiver is unchanged. This\n'
            'mirrors reflective descent functions whose inputs are a reified module\n'
            'and term [source:\n'
            'https://maude.cs.illinois.edu/maude1/manual/maude-manual-html/maude-manual_24.html;\n'
            'commit=0d49980b03d507f9bae0354786ab826a146c20df].\n'
            '\n'
            '``interpreter=`` instead evaluates the explicit full-interpreter\n'
            'application ``(interpreter target %Undefined% space)`` for this ask,\n'
            "which is the shape MeTTa's own evaluation function has: it says\n"
            '"reduce with YOURS rather than the engine\'s".\n'
            '\n'
            'The two COMPOSE, and are the head and the third argument of one\n'
            'application rather than rival answers to one question: with both, the\n'
            "interpreter is handed the theory's space, so it interprets the theory\n"
            '[measured 2026-08-31: an interpreter tracing its delegate answered\n'
            '`(Traced base)` alone and `(Traced left), (Traced right)` over a\n'
            'two-equation theory]. They used to refuse together.\n'
            '\n'
            "The INTERPRETER must declare its first parameter `Atom`, MeTTa's own\n"
            'way to receive an argument unevaluated, or the engine reduces the\n'
            'target before the interpreter ever sees it; and its RETURN metatype\n'
            "`%Undefined%`, or the interpreter's own answer is not reduced either.\n"
            '`(: e (-> Atom Atom Atom %Undefined%))` is the declaration.\n'
            '\n'
            "A text target may carry HOLES, as run()'s source may:\n"
            '`m.answers(t"(near {point})")`. A theory, an interpreter or a carrier\n'
            'makes this view ask through another door, so the holes are read into\n'
            'the term itself there rather than sent as pairs a hand-off would drop.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_answers_scalar_doors_raise_error_atoms_but_iteration_retains_them', 'extensions/python/tests/ch04_spaces_and_matching/test_arrow_doors.py::test_term_answers_refuse_the_arrow_doors', 'extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_term_answers_never_render_as_a_binding_table'),
        binding=Binding('metta_py_eval_cursor', Wire.goal),
        sugar_of=Sugar("space:eval", (('answer', 'answers'),)),
        async_excluded="Answers is a synchronous replayable iterator; AsyncMeTTa's stream is the awaitable pull protocol rather than a cross-thread iterator",
    ),
    Door(
        owner=Owner.space,
        name='parallel',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, *targets: Any, timeout: float | None=None', returns='list[Atom | Undefined]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_parallel'),
        docs=(
            "Evaluate every target concurrently, answering every branch's answers.\n"
            '\n'
            "This is the engine's `hyperpose`, the parallel twin of `superpose`:\n"
            'one SWI thread per branch through concurrent_and/2, so independent\n'
            "branches cost about one branch's wall clock rather than their sum.\n"
            '\n'
            '    m.run("(= (sq $x) (* $x $x))")\n'
            '    m.parallel(S.sq(1), S.sq(2), S.sq(3))    # 1, 4 and 9, in any order\n'
            '\n'
            'This is the **in-engine** fan-out: one janus call, the branches split\n'
            'below it. The other route is `pool()`, the **Python-side** fan-out\n'
            'across several engines. Reach for this one when the fan-out is a MeTTa\n'
            'expression, and for `pool()` when it is a Python loop. They compose,\n'
            'so a pool worker may itself evaluate a `parallel()`.\n'
            '\n'
            '(Before 2026-08-15 this docstring said in-engine fan-out was the only\n'
            'route to a second core, because every janus call took one process-wide\n'
            'lock. That lock is now per-engine, and Python threads holding their own\n'
            'engine measured 1.94x, 3.90x and 7.26x at 2, 4 and 8 threads.)\n'
            '\n'
            '**Answers arrive in completion order, not argument order**, because\n'
            'the branches race. Compare sets rather than sequences, and evaluate a\n'
            '`superpose` instead when order carries meaning.\n'
            '\n'
            'Each target is a term or its source text, as everywhere else. No\n'
            'targets answers nothing without calling the engine.\n'
            '\n'
            '`timeout` bounds the call and is the bound to use here. There is\n'
            "deliberately no `inferences=`: the engine's inference limit counts\n"
            'the calling thread, and `concurrent_and/2` runs every branch in a\n'
            'worker, so a limit of 50,000 does not stop two branches spending six\n'
            'million [measured 2026-08-15]. An unenforceable bound is worse than\n'
            'an absent one, so eval() over a `superpose` is the way to bound this\n'
            'work by inferences, at the cost of running it on one core.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_hyperpose_is_parallel_under_the_languages_name', 'extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_pool_composes_with_in_engine_parallel', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_parallel.py::test_parallel_accepts_text_and_atoms'),
    ),
    Door(
        owner=Owner.space,
        name='pool',
        kind=Kind.provider,
        signatures=(
            Signature('self, workers: int | None=None', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_pool'),
        docs=(
            'A pool of worker threads that each hold their own Prolog engine.\n'
            '\n'
            'The Python-side twin of `parallel()`. Each worker attaches its own\n'
            'engine, so the process lock that serialises the home engine does not\n'
            'apply to it and the calls genuinely run at once [measured 2026-08-15:\n'
            '1.94x, 3.90x and 7.26x at 2, 4 and 8 workers].\n'
            '\n'
            '    m.run("(= (sq $x) (* $x $x))")\n'
            '    with m.pool(workers=4) as p:\n'
            '        list(p.map(lambda n: m.eval(S.sq(n))[0], range(64)))\n'
            '\n'
            'Use it as a context manager so every engine is released. `workers`\n'
            'defaults to os.cpu_count(). This handle stays usable from the workers:\n'
            'a MeTTa is a space name over the process runtime, not thread-owned.\n'
            '\n'
            'Reach for `parallel()` instead when the fan-out is a MeTTa expression\n'
            'rather than a Python loop; the two compose.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_metta_pool_is_the_same_pool', 'extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_several_failures_raise_together_one_raises_plain'),
        async_excluded="asyncio's fan-out is N workers and asyncio.gather; a pool of engine threads is the synchronous spelling of the same thing",
    ),
    Door(
        owner=Owner.space,
        name='reducible',
        kind=Kind.introspection,
        signatures=(
            Signature('self, target: Any', returns='bool'),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_reducible'),
        docs=(
            'Whether a head reduces here, asked without evaluating anything.\n'
            '\n'
            '    m.reducible(S.double(4))     # True\n'
            '    m.reducible(S.Point(1, 2))   # False, nothing applies to that head\n'
            '\n'
            'The same head test eval_status() uses, published on its own because a\n'
            'caller who wants to DECIDE about an unreduced term should not have to\n'
            "run the term to find out. That decision is the caller's: a term\n"
            'nothing applies to is its own answer, which is ordinary MeTTa and how\n'
            '`!(hello world)` works, so there is no scope here that refuses one.\n'
            '\n'
            'The Node extension has had m.reducible() since it existed; Python had\n'
            'only eval_status(), which evaluates to tell you [measured 2026-08-31].\n'
        ),
        evidence=('extensions/python/tests/ch05_equations_and_evaluation/test_nothing_outcomes.py::test_reducible_asks_the_question_without_running_the_term',),
        binding=Binding('metta_py_reducible', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='eval-status',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, target: Any, /, *, timeout: float | None=None, inferences: int | None=None, theory: Any | None=None, interpreter: Any | None=None, **values: Any', returns='list[tuple[str, Atom | Undefined | None]]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_eval_status'),
        docs=(
            'Evaluate a term, pairing each answer with how it was produced.\n'
            '\n'
            '    m.eval_status(S.double(4))       # [("value", Grounded(8))]\n'
            '    m.eval_status(S.Point(1, 2))     # [("not-reducible", Expression(...))]\n'
            '    m.eval_status(S.empty())         # [("empty", None)]\n'
            '\n'
            '`value` means an equation, builtin or special form applied.\n'
            '`not-reducible` means no rule applied, so the answer is the term\n'
            'itself, which is what MeTTa does with any head it cannot call.\n'
            '`empty` means the goal produced no answer at all, and its atom is\n'
            'None. Reading the last two as the same thing is the mistake this\n'
            'exists to prevent: an unevaluated term and a pruned branch look\n'
            'alike from the answers alone. An error is not a status here,\n'
            'because it arrives as an exception.\n'
            '\n'
            'A `bind()` scope binds host values into the term exactly as it\n'
            'does for eval(), and it has to: the substitution lands BEFORE the\n'
            'reducibility question, so the status of an evaluation that binds\n'
            'anything was unaskable without it. Name keys mean symbols and atom\n'
            'keys mean themselves, so `bind({V.x: 5})` fills a variable hole.\n'
            '\n'
            "`theory` and `interpreter` are eval()'s own, and mean the same here.\n"
            'This is the method that says which evaluation path produced an answer, so\n'
            'being unable to point it at an alternative evaluation relation was the\n'
            'sharpest form of the gap: `m.eval_status(target, interpreter=my_eval)`\n'
            'is how you see whether an explicit interpreter reduced a term or handed\n'
            'it back. `under=` is deliberately NOT here: a carrier annotates every\n'
            'answer with an algebra value, so it would make a status row a triple\n'
            'rather than the pair it is, which is a question about what a status IS.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_eval_status_reports_the_four_outcomes', 'extensions/python/tests/ch05_equations_and_evaluation/test_per_ask_evaluation.py::test_eval_status_selects_the_same_relations_answers_does', 'extensions/python/tests/ch05_equations_and_evaluation/test_nothing_outcomes.py::test_eager_eval_keeps_empty_and_not_reducible_distinct'),
    ),
    Door(
        owner=Owner.space,
        name='run-status',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, source: str, *, timeout: float | None=None, inferences: int | None=None', returns='list[list[tuple[str, Atom | Undefined | None]]]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_run_status'),
        docs=(
            "run(), with each directive's answers paired with how they arose.\n"
            '\n'
            "The grouping and the answers are run()'s own; see eval_status() for\n"
            'what the three paths mean.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_run_status_registers_signatures_before_any_form_runs', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_run_status_reports_each_directive', 'extensions/python/tests/ch11_python_as_a_notation/test_template_holes.py::test_run_status_refuses_program_text_with_holes'),
    ),
    Door(
        owner=Owner.space,
        name='one',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, target: Any, *, timeout: float | None=None, inferences: int | None=None', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.async_,),
        body=Body('metta._space', 'Space._one'),
        docs=(
            'Return the sole answer as a plain Python value for internal callers.\n'
            '\n'
            '    m.eval(S.fact(5))[0]         # Grounded(120)\n'
            '\n'
            'Exactly one answer is the contract: none or several raise naming\n'
            'the count, because a caller asking for the value has asserted\n'
            'there is one. Grounded answers unwrap to their Python values;\n'
            'symbols and structure stay atoms.\n'
            '\n'
            'This is one point on the answer-cardinality axis, spelled the\n'
            "same everywhere it appears: eval() takes every answer (MeTTa's\n"
            'collapse), while this private helper demands exactly one. The same\n'
            'timeout/inferences bounds apply throughout.\n'
            '\n'
            'An `(Error ...)` answer raises MettaResultError carrying the\n'
            'atom: an error among the answers is the evaluation reporting\n'
            'failure, and failure outranks the count. eval() is the method\n'
            'that keeps errors as data.\n'
        ),
        evidence=('extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_one_raises_a_structured_error_on_an_error_answer', 'extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_one_still_answers_plain_values', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_value_answers_the_one_answer'),
        sugar_of=Sugar("space:eval", (('answer', 'one'), ('delivery', 'values'), ('on_error', 'abort'))),
    ),
    Door(
        owner=Owner.space,
        name='first',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, target: Any, *, timeout: float | None=None, inferences: int | None=None', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.async_,),
        body=Body('metta._space', 'Space._first'),
        docs=(
            'The first answer as a plain Python value, or None for no answers.\n'
            '\n'
            "The tolerant member of one()'s family: one() asserts exactly\n"
            'one, eval() answers all, first() answers the first or nothing,\n'
            'decoded by the same rule as one(). An Undefined first answer\n'
            'still raises, since None here MEANS no answers. Tolerance is\n'
            'about cardinality, not content: a first answer that is an\n'
            '`(Error ...)` atom raises MettaResultError exactly as one()\n'
            'does, because None must keep meaning "no answers" and an error\n'
            'used as a value is the silent kind of wrong.\n'
        ),
        evidence=('extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_first_raises_on_an_error_first_answer_only', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_the_three_families_share_the_tolerant_member'),
        sugar_of=Sugar("space:eval", (('answer', 'first'), ('delivery', 'values'), ('on_error', 'abort'))),
    ),
    Door(
        owner=Owner.space,
        name='stats',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='_StatsBlock'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_stats'),
        docs=(
            "The engine's own counters over a with-block, as deltas.\n"
            '\n'
            '    with m.stats() as s:\n'
            '        m.match(S.edge(V.x, V.y), S.edge(V.y, V.z))\n'
            '    s.inferences        # engine steps the block spent\n'
            '    s.cputime           # engine CPU seconds\n'
            "    s.walltime          # wall seconds, Python's clock\n"
            '    s.gc_count, s.gc_freed, s.gc_time\n'
            "    s.table_bytes       # answer-table bytes grown, tabling's memory\n"
            '\n'
            "The counters are SWI's statistics/2 read on the CALLING thread, so\n"
            "a block that runs other threads' engine work counts that work too;\n"
            'the honest reading is "what this thread saw the engine do while the\n'
            'block ran". A lazy cursor is the exception, and a large one: its\n'
            'goal runs in an SWI engine, an engine counts its own inferences,\n'
            'and this thread cannot see them. Draining 20,000 rows through the\n'
            'match cursor reports 40,049 inferences against about 381,000 the\n'
            "cursor's engine really spent, 10.5% of the work; the real cost is\n"
            'readable off the `inferences` budget, which does count the engine\n'
            '[measured 2026-08-27]. The evaluation cursor behind `answers()`\n'
            "does report its engine's spend, so that one is whole. The z3py\n"
            'Solver.statistics() reading, on the engine this library actually\n'
            'has.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_analyze_numbers_equal_the_stats_of_the_same_query', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_profile_exports_as_pstats', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_stats_counter_is_unreadable_until_its_block_closes'),
        alias='stats',
    ),
    Door(
        owner=Owner.space,
        name='op',
        kind=Kind.provider,
        signatures=(
            Signature("self, fn: Callable[_P, _R], /, *, name: str | None=..., transport: Literal['encoded', 'raw']=..., effect: EffectClass | str, declarations: Iterable[Atom]=..., arities: list[int] | None=..., inverse: Callable | None=...", returns='Callable[_P, _R]', declarations=('overload',)),
            Signature("self, *, name: str | None=..., transport: Literal['encoded', 'raw']=..., effect: EffectClass | str, declarations: Iterable[Atom]=..., arities: list[int] | None=..., inverse: Callable | None=...", returns='Callable[[Callable[_P, _R]], Callable[_P, _R]]', declarations=('overload',)),
            Signature("self, fn: Callable | None=None, *, name: str | None=None, transport: Literal['encoded', 'raw']='encoded', effect: EffectClass | str | None=None, declarations: Iterable[Atom]=(), arities: list[int] | None=None, inverse: Callable | None=None", returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_op'),
        docs=(
            'Register a Python callable as a MeTTa function, decorator-style.\n'
            '\n'
            '    @m.op(effect=EffectClass.pureStructural)\n'
            '    def double(x: int) -> int:\n'
            '        return 2 * x                    # !(double 21) -> 42\n'
            '\n'
            '    @m.op(effect=EffectClass.nondeterministicReadOnly)\n'
            '    def neighbours(n: int):\n'
            '        yield n - 1                     # a generator is nondeterministic\n'
            '        yield n + 1\n'
            '\n'
            'An implicit Python name maps underscores to MeTTa hyphens. ``name=``\n'
            'is exact, for source vocabularies that deliberately use underscores.\n'
            '\n'
            'A name must read back as one MeTTa symbol. A space, parenthesis,\n'
            'quote, comment opener, variable spelling, number, boolean, or another\n'
            'registered reader token is refused before any registry changes, with\n'
            'the name and the conflicting character in the error.\n'
            '\n'
            'Annotations become ordinary `(: ...)` declarations. An unannotated\n'
            'callable makes no type claim. `transport="raw"` skips wire encoding\n'
            'both ways and is reflected as raw_det or raw_many in `(op ...)`;\n'
            'symbols then reach Python as strings, so encoded transport is the\n'
            'fidelity-preserving default. unregister_op(name) removes every\n'
            'registered arity and every declaration the registration owns.\n'
            '\n'
            'An `Atom` parameter changes evaluation order. The declaration tells\n'
            'the compiler to pass the argument as written, before it reduces:\n'
            '\n'
            '    @m.op(effect=EffectClass.pureStructural)\n'
            '    def anyatom(term: Atom) -> Atom:\n'
            '        return term\n'
            '\n'
            '    # with (= (side) 42), !(anyatom (side)) answers (side)\n'
            '\n'
            'An unconstrained parameter receives the evaluated value instead, so\n'
            'the otherwise identical `def anyval(term): return term` answers 42.\n'
            'Use `Atom` only when the operation deliberately implements syntax or\n'
            'a control form; it is not just a static hint.\n'
            '\n'
            'An encoded generator may instead yield exact tuples as positional\n'
            'relation rows, or exact dicts keyed by parameter name as sparse rows.\n'
            'The engine unifies each candidate against the written call, so one\n'
            'implementation serves free, partially bound, and ground arguments:\n'
            '\n'
            '    @m.op\n'
            '    def route(origin, destination):\n'
            '        yield (S.paris, S.lyon)\n'
            '        yield {"destination": S.nice}  # origin is unconstrained\n'
            '\n'
            '    # route(V.origin, S.lyon).rows[0].origin == S.paris\n'
            '\n'
            'Each matching occurrence answers unit and duplicate yields remain\n'
            'duplicate answers. Use `Answer(value=...)` when an exact tuple or dict\n'
            'is the result value rather than a parameter row. Relational rows\n'
            'require encoded transport; raw calls cannot carry unbound argument\n'
            'positions.\n'
            '\n'
            'When evaluation order stays ordinary but the callable needs the\n'
            'resulting Atom wrappers, declare that policy as data:\n'
            '\n'
            '    m.op(\n'
            '        inspect_atom,\n'
            '        name="inspect-atom",\n'
            '        effect=EffectClass.pureStructural,\n'
            '        declarations=[parse("(arguments inspect-atom atoms)")],\n'
            '    )\n'
            '\n'
            'The declaration is matchable in &metta and is retired with the\n'
            'operation. Raw transport refuses this declaration because it bypasses\n'
            'the atom codec entirely.\n'
            '\n'
            'The cost ladder, measured on the maintained box in inferences per\n'
            'call, explains the transport choice:\n'
            '\n'
            '    native MeTTa function            9.11   the floor\n'
            '    transport="raw"                10.11   opaque handles, near-native\n'
            '    encoded                        17.11   encoded values\n'
            '    encoded, typed literal         17.11   the check hoists to compile\n'
            '    py-call, dotted                 22.11   the ad-hoc escape hatch\n'
            '\n'
            'The ergonomic default (encoded, typed) costs about 1.7x raw on the\n'
            'counter and more on wall clock, since encoding walks the value both\n'
            'ways; a registered raw operation measured 0.85us against 2.26us\n'
            'encoded. Bulk data should stay opaque: one transparent 64-float\n'
            'crossing costs 330 inferences where the handle costs 10.\n'
            '\n'
            '`inverse=` remains the distinct-output form. Use it when the forward\n'
            'operation returns a result and a separate callable must recover the\n'
            'arguments from that result:\n'
            '\n'
            '    m.op(\n'
            '        cons,\n'
            '        name="cons",\n'
            '        inverse=uncons,\n'
            '        effect=EffectClass.pureStructural,\n'
            '    )\n'
            '    # !(let (cons $h $t) (1 2 3) ($h $t))  ->  (1 (2 3))\n'
            '\n'
            'It takes the result and returns the arguments, as a tuple, or the\n'
            'bare value at arity one; a generator enumerates every preimage, and\n'
            'None or NotReducible means there is none. It runs only when the arguments\n'
            'are not ground and the result is, so a forward call never reaches it,\n'
            'and an operation without one compiles exactly what it did before.\n'
            '\n'
            "A parameter annotated `metta.MeTTa` is the framework's to fill,\n"
            "FastAPI's Depends read with the house convention that the\n"
            'annotation is the request. The engine injects itself bound to the\n'
            "CALLING context's space, so an operation invoked from a program\n"
            'running in &kb queries &kb; the slot never counts toward MeTTa\n'
            'arities or the declared arrow, and only operations that ask pay\n'
            'the weaving:\n'
            '\n'
            '    @m.op(effect=EffectClass.nondeterministicReadOnly)\n'
            '    def related(term, engine: metta.MeTTa):\n'
            '        for row in engine.match(Expression(S.link, term, V.x)):\n'
            '            yield row[0]\n'
            '\n'
            'Every operation declares its strongest observable effect. The five\n'
            'ordered choices are ``pureStructural``, ``readOnlyLookup``,\n'
            '``nondeterministicReadOnly``, ``writesState``, and ``oracleIO``:\n'
            '\n'
            '    m.op(\n'
            '        len,\n'
            '        name="size",\n'
            '        effect=EffectClass.pureStructural,\n'
            '    )\n'
            '    # (= (count-of $x) (size $x))  is cacheable\n'
            '\n'
            'It is an allow-list on purpose. An operation that does not say so is\n'
            'refused by name in a cached body, loudly, rather than cached and\n'
            'quietly wrong.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_effect_lattice.py::test_every_effect_rank_registers_and_reflects',),
        alias='op',
        async_signature=Signature("self, fn: Callable, /, *, effect: Any, name: Any = None, transport: Any = 'encoded', declarations: Any = (), arities: Any = None, inverse: Any = None", returns='Any'),
        async_reason="the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the worker would register on the caller's thread rather than the engine's. Only the applied form crosses",
    ),
    Door(
        owner=Owner.space,
        name='pure',
        kind=Kind.provider,
        signatures=(
            Signature('self, fn: Callable | None=None, /, **options: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_pure'),
        docs=(
            'An operation whose answer depends only on its arguments.\n'
            '\n'
            '    @m.pure\n'
            '    def double(x: int) -> int:\n'
            '        return 2 * x\n'
            '\n'
            'The cache-safe class, and the only one memoization and tabling admit\n'
            'without an explicit policy.\n'
            '\n'
            'A GENERATOR written this way is lifted to `nondeterministicReadOnly`,\n'
            'because a generator is nondeterministic whatever it declares, and the\n'
            'registration reads that off the function rather than asking. The lift\n'
            'only ever raises the rank, so it widens the answer-count claim and\n'
            'never weakens the effect claim -- but it does mean a generator is not\n'
            'cache-safe, which is the whole reason it is lifted out of this class\n'
            '[tested: test_a_generator_is_lifted_to_the_nondeterministic_rank;\n'
            'commit=7e5091540a8dc0903bcee24f3e5b8b85a19f805f].\n'
            '\n'
            'Every ``op`` keyword applies: ``name``, ``arities``,\n'
            '``declarations``, ``inverse`` and ``transport``. They arrive as\n'
            '``**options`` and forward unchanged, so the signature above shows\n'
            'the mechanism and this line shows the surface.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_effect_sugars_are_their_declared_parameter_points',),
        alias='pure',
        async_signature=Signature('self, fn: Callable, /, **options: Any', returns='Any'),
        async_reason="the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the worker would register on the caller's thread rather than the engine's. Only the applied form crosses",
        sugar_of=Sugar("space:op", (('effect', 'pureStructural'),)),
    ),
    Door(
        owner=Owner.space,
        name='reads',
        kind=Kind.provider,
        signatures=(
            Signature('self, fn: Callable | None=None, /, **options: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_reads'),
        docs=(
            'An operation that reads stable state without changing it.\n'
            '\n'
            'Every ``op`` keyword applies: ``name``, ``arities``,\n'
            '``declarations``, ``inverse`` and ``transport``. They arrive as\n'
            '``**options`` and forward unchanged, so the signature above shows\n'
            'the mechanism and this line shows the surface.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_effect_sugars_are_their_declared_parameter_points',),
        alias='reads',
        async_signature=Signature('self, fn: Callable, /, **options: Any', returns='Any'),
        async_reason="the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the worker would register on the caller's thread rather than the engine's. Only the applied form crosses",
        sugar_of=Sugar("space:op", (('effect', 'readOnlyLookup'),)),
    ),
    Door(
        owner=Owner.space,
        name='writes',
        kind=Kind.provider,
        signatures=(
            Signature('self, fn: Callable | None=None, /, **options: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_writes'),
        docs=(
            'An operation that changes engine or host state.\n'
            '\n'
            'Every ``op`` keyword applies: ``name``, ``arities``,\n'
            '``declarations``, ``inverse`` and ``transport``. They arrive as\n'
            '``**options`` and forward unchanged, so the signature above shows\n'
            'the mechanism and this line shows the surface.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_effect_sugars_are_their_declared_parameter_points',),
        alias='writes',
        async_signature=Signature('self, fn: Callable, /, **options: Any', returns='Any'),
        async_reason="the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the worker would register on the caller's thread rather than the engine's. Only the applied form crosses",
        sugar_of=Sugar("space:op", (('effect', 'writesState'),)),
    ),
    Door(
        owner=Owner.space,
        name='io',
        kind=Kind.provider,
        signatures=(
            Signature('self, fn: Callable | None=None, /, **options: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_io'),
        docs=(
            'An operation that observes an external oracle.\n'
            '\n'
            'A clock, randomness, a network, a file, another runtime.\n'
            '\n'
            '    @m.io\n'
            '    def now() -> float:\n'
            '        return time.time()\n'
            '\n'
            'The fail-closed top of the lattice. Declare it when what the operation\n'
            'reaches is decided at run time or by a library the engine cannot bound.\n'
            '\n'
            'Every ``op`` keyword applies: ``name``, ``arities``,\n'
            '``declarations``, ``inverse`` and ``transport``. They arrive as\n'
            '``**options`` and forward unchanged, so the signature above shows\n'
            'the mechanism and this line shows the surface.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_effect_sugars_are_their_declared_parameter_points',),
        alias='io',
        async_signature=Signature('self, fn: Callable, /, **options: Any', returns='Any'),
        async_reason="the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the worker would register on the caller's thread rather than the engine's. Only the applied form crosses",
        sugar_of=Sugar("space:op", (('effect', 'oracleIO'),)),
    ),
    Door(
        owner=Owner.space,
        name='unregister-op',
        kind=Kind.provider,
        signatures=(
            Signature('self, name: str', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_unregister_op'),
        docs=(
            'Remove a registered operation, every arity of it.\n'
            '\n'
            'An absent name raises KeyError, as convert.unregister_type does:\n'
            'removing something that was never there is a mistake worth hearing\n'
            'about, not a no-op to absorb.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_shared_class_declarations_survive_one_unregister', 'extensions/python/tests/ch11_python_as_a_notation/test_ops.py::test_unregistering_a_name_a_system_predicate_shares_does_not_throw', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_unregister_removes_the_effect_atom_with_the_op_facts'),
    ),
    Door(
        owner=Owner.space,
        name='builtins',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='list[str]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_builtins'),
        docs=(
            'Every function callable from this space, plus every special form.\n'
            '\n'
            "Its own equations, the ones it inherits, ``&self``'s shared ones and\n"
            "the engine's builtins, with the translator's special-form heads,\n"
            'sorted without duplicates. A head another space defines is\n'
            "registered process-wide (the translator's call-or-data question,\n"
            'which ``is_function`` answers) but is not callable here and is not\n'
            'listed here.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_mention_doors.py::test_catalogue_membership_answers_the_builtins_union', 'extensions/python/tests/ch18_performance/test_builtins_generation_cache.py::test_eval_definitions_reach_the_next_namespace_access', 'extensions/python/tests/ch20_extending_the_engine/test_builtins.py::test_builtins_equals_the_union_of_functions_and_special_forms'),
    ),
    Door(
        owner=Owner.space,
        name='is-function',
        kind=Kind.introspection,
        signatures=(
            Signature('self, name: str', returns='bool'),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_is_function'),
        docs=(
            'Report whether the name is registered as a function anywhere.\n'
            '\n'
            "This is the translator's call-or-data question and holds wherever a\n"
            'term compiles; ``is_function_here`` asks whether the head answers\n'
            'from THIS space, and ``builtins()`` lists what this space can call.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_registration_failure_leaves_nothing_half_registered', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_union_expansion_is_bounded', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call'),
        binding=Binding('metta_py_is_function', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='is-function-here',
        kind=Kind.introspection,
        signatures=(
            Signature('self, name: str', returns='bool'),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_is_function_here'),
        docs=(
            'Whether a function would answer from THIS space: it has clauses\n'
            "this space's module sees, its own or the shared ones in user.\n"
            "Another space's equations are invisible here and do not count.\n"
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_a_space_is_the_grounded_handle_species_and_import_operand', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call', 'extensions/python/tests/ch11_python_as_a_notation/test_host_island.py::test_unknown_host_callee_islands_implicitly'),
        binding=Binding('metta_py_function_visible', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='arities',
        kind=Kind.introspection,
        signatures=(
            Signature('self, name: str', returns='list[int]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_arities'),
        docs=(
            'Compiled predicate arities for a name: MeTTa arity plus one each.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ide_surface.py::test_declarations_carry_arrows_arities_and_documentation', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_aio.py::test_aio_plain_methods_forward_on_the_worker'),
        binding=Binding('metta_py_arities', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='register-prolog',
        kind=Kind.provider,
        signatures=(
            Signature('self, source: str | None=None, *, path: str | os.PathLike[str] | None=None, names: _abc.Sequence[str] | _abc.Mapping[str, str]=()', returns='tuple[str, ...]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_register_prolog'),
        docs=(
            'Register Prolog predicates as MeTTa functions, at native speed.\n'
            '\n'
            'This is the extension point for a library that wants to run fast.\n'
            'op() is the one most people find first, and every call it\n'
            'serves crosses the janus boundary: 25.16 inferences and 2.34us per\n'
            'call, against 7.16 inferences and 0.13us for the same operation\n'
            'written in Prolog [measured 2026-08-15, 3000 calls in one harness].\n'
            '\n'
            'Read the microseconds, not the inferences. The crossing counts as ONE\n'
            'inference and costs real time, so inferences say a Python operation is\n'
            '3.1x a Prolog one while wall clock says 18x. That is a fine price for\n'
            'reaching NumPy or an LLM and a bad one for arithmetic in a loop.\n'
            '\n'
            'A registered predicate keeps its nondeterminism: one that offers three\n'
            'solutions gives the MeTTa function three answers.\n'
            '\n'
            'A predicate follows the compiled calling convention, inputs first and\n'
            'one output last:\n'
            '\n'
            '    m.register_prolog(\n'
            '        "\'vec-dot\'(A, B, Out) :- ... .",\n'
            '        names=["vec-dot"],\n'
            '    )\n'
            '    m.eval("(vec-dot (1 2) (3 4))")[0]\n'
            '\n'
            'or, for a library shipping a file beside its Python:\n'
            '\n'
            '    m.register_prolog(path=Path(__file__).parent / "fast.pl",\n'
            '                      names=["vec-dot", "vec-norm"])\n'
            '\n'
            'Every name is registered explicitly rather than discovered, because\n'
            'registering a name whose predicate is absent records no arity and then\n'
            'compiles every call to it into a partial application instead of\n'
            'failing, which is a silent wrong answer rather than an error. This\n'
            'raises instead: a name with no predicate behind it is refused before\n'
            'it can do that.\n'
            '\n'
            "The refusals are the engine's, through check_prolog_function_names/3\n"
            'and import_prolog_functions/2, so this and the MeTTa spelling enforce\n'
            'one rule rather than two copies of it. Three names are refused: one\n'
            'with no predicate behind it, a builtin, and a special form.\n'
            '\n'
            'Nothing is registered unless every name can be, so a typo in the list\n'
            'changes nothing. The consulted SOURCE does stay loaded on failure,\n'
            'which is deliberate rather than overlooked: loading it again is the\n'
            'retry, and it is idempotent, since the source is identified by a hash\n'
            'of its own content.\n'
            '\n'
            '**This is a method on a space and it registers PROCESS-WIDE.** So do\n'
            'op and define. Only equations are space-scoped, so an anonymous\n'
            'space() isolates one of the three things you can register and\n'
            'shares the other two. That is deliberate rather than overlooked: a\n'
            'Prolog predicate lives in `user`, every space has to be able to call\n'
            'it, and a library loaded inside a named space would define itself\n'
            'where the registration could not see it. The method sits on the space\n'
            'because that is where the rest of the surface is, not because the\n'
            'registration is scoped to it.\n'
            '\n'
            'The name is owned by one tier. A second registration of the same name\n'
            'from another tier is refused, in both directions, naming the owner, so\n'
            'two libraries cannot silently take the same name from each other.\n'
            '\n'
            'A parameter a MeTTa caller should reach unevaluated needs a type\n'
            'declaration, which this call does not take yet:\n'
            '\n'
            '    m.register_prolog("\'shape-of\'(A, Out) :- Out = [shape, A].",\n'
            '                      names=["shape-of"])\n'
            '    m.run("(: shape-of (-> Atom Atom))")\n'
            '    m.eval("(shape-of (+ 1 2))")[0] # (shape (+ 1 2)), not (shape 3)\n'
            '\n'
            'Declare it BEFORE anything calls the function. A call site compiled\n'
            'while the declaration is absent keeps evaluating the argument even\n'
            'after it lands.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_builtin_name_is_refused_and_the_builtin_still_works', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declaration_without_an_extension_still_reports_its_names', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declared_det_function_answers_normally'),
        binding=Binding('import_prolog_functions', Wire.goal),
        refuses=(
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:register-prolog]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='register-foreign-library',
        kind=Kind.provider,
        signatures=(
            Signature('self, path: str | os.PathLike[str], *, entry: str | None=None, names: _abc.Sequence[str]=()', returns='tuple[str, ...]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_register_foreign_library'),
        docs=(
            'Load a compiled `.so` and register its predicates as MeTTa functions.\n'
            '\n'
            "The C tier is the cheapest one on this page's cost table, one\n"
            'inference per call, and reaching it used to mean hand-writing two\n'
            'Prolog directives into `register_prolog`:\n'
            '\n'
            '    m.register_foreign_library(Path(__file__).parent / "cbump.so",\n'
            '                               entry="install_cbump", names=["c-bump"])\n'
            '\n'
            '`entry` is the C initialiser, `install_cbump` in\n'
            '`install_t install_cbump(void)`; leave it out for a library whose\n'
            'entry is plain `install`.\n'
            '\n'
            'The path is resolved to an ABSOLUTE one here, which is the trap this\n'
            'exists to close: `use_foreign_library/2` accepts a path relative to\n'
            'the working directory, resolves it, and SWI deprecates that and warns\n'
            'on every load, so a library that shipped one worked from the repo root\n'
            'and warned or failed anywhere else. A file that is not there is\n'
            "refused here rather than inside the engine's loader.\n"
            '\n'
            'Everything after the load is `register_prolog`, so the same refusals\n'
            'apply: a name with no predicate behind it, a builtin, a special form,\n'
            'and a name another tier owns.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_compiled_library_registers_from_python', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_absent_compiled_library_is_refused_here', 'extensions/python/tests/ch14_seeing_your_program/test_trace.py::test_a_foreign_predicate_does_not_break_tracing'),
        refuses=(
            Refusal(RefusalKind.source, 'extensions/python/tests/repository/test_door_refusals.py::test_foreign_library_refuses_a_missing_source'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='register-library-path',
        kind=Kind.provider,
        signatures=(
            Signature('self, directory: Any, name: str', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_register_library_path'),
        docs=(
            'Point MeTTa at a directory of files your package ships.\n'
            '\n'
            "    # in your package's __init__\n"
            '    m.register_library_path(Path(__file__).parent / "prolog", "pettorch")\n'
            '\n'
            'Subject first, as every register_* call: the directory being\n'
            'registered, then the library name it serves.\n'
            '\n'
            '`(library pettorch fast.pl)` then resolves, from MeTTa and from\n'
            '`register_prolog(path=...)`. Without it a pip-installed library is\n'
            'under neither `<engine>/../lib` nor a git checkout, so it has to pass\n'
            'absolute paths and compute them from `__file__` by hand.\n'
            '\n'
            "This is SWI's own `file_search_path/2`, so an alias registered here is\n"
            'one every SWI tool already understands, and aliases compose: the\n'
            'second argument of one may be another alias. Registering the same\n'
            'directory twice is a no-op; a directory that is not there is refused\n'
            'here rather than at the first import that needs it.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_an_explicitly_shared_library_alias_keeps_all_directories', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_unwinds_every_framework_registration'),
        binding=Binding('register_metta_library_path', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='unregister-prolog',
        kind=Kind.provider,
        signatures=(
            Signature('self, extension: str', returns='tuple[str, ...]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_unregister_prolog'),
        docs=(
            'Release everything one extension registered, and its clauses.\n'
            '\n'
            'The unit is the extension, not the name. `register_prolog` used to\n'
            'load a bunch of loose predicates: the engine recorded that each name\n'
            'was a function and nothing at all about the library it came from, so\n'
            'there was no uninstall to write and a partly-failed registration left\n'
            'debris nobody could enumerate.\n'
            '\n'
            "    :- metta_extension(pettorch, [version('0.3.1')]).\n"
            '    :- metta_export("(: vec-dot (-> Number Number Number))").\n'
            '\n'
            '    m.register_prolog(path="fast.pl")     # names come from the file\n'
            '    m.unregister_prolog("pettorch")       # everything it installed\n'
            '\n'
            "PostgreSQL's rule, and its reason: an individual member cannot be\n"
            'dropped on its own, only the whole extension, which is what stops one\n'
            'registry keeping a claim on a name another route already replaced.\n'
            "The clauses go too, through SWI's own `unload_file/1`, so a name is\n"
            'not left callable through a predicate nothing records.\n'
            '\n'
            'Answers the names it released. Raises when no extension of that name\n'
            'is loaded, rather than reporting success for a no-op.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_provider_only_file_registers_no_functions_and_is_accepted', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_extension_unloads_whole', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_unloaded_extension_does_not_leave_its_names_behind'),
        binding=Binding('metta_py_unregister_extension', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='subscribe',
        kind=Kind.scope,
        signatures=(
            Signature('self, pattern: Any, callback: Callable | None=None, *, on: SubscriptionEdge=SubscriptionEdge.add, where: Any | None=None, queue_max: int | None=None'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_subscribe'),
        docs=(
            'A standing query on this space: every added (or removed, or\n'
            'both) atom unifying with the pattern becomes an Event.\n'
            '\n'
            '    seen = []\n'
            '    sub = m.subscribe(S.order(V.id), lambda e: seen.append(e))\n'
            '    m.add(S.order(1))          # seen[0].bindings["id"] == 1\n'
            '    sub.cancel()\n'
            '\n'
            'With a callback, delivery is synchronous. An unscoped write delivers\n'
            'before it returns; a transaction delivers its ordered segment only\n'
            'after the complete commit, while rollback and speculation deliver\n'
            'nothing. The callback may write back; the engine re-enters cleanly,\n'
            "and an infinite add-triggers-add loop is the author's own.\n"
            'Without one, events queue on the subscription and drain() empties\n'
            'them: the mailbox reading. That queue is bounded by `queue_max`,\n'
            'and a write arriving at a full queue raises SubscriberError rather\n'
            'than discarding the oldest event: nobody draining is a bug in the\n'
            'consumer, and a silently shortened history is how it stays hidden.\n'
            'A removal event fires only when something was removed, and carries\n'
            'the pattern that was asked for rather than the occurrence that\n'
            'left. The two are the same atom for a ground removal and differ\n'
            'for a pattern one: removal is multiset subtraction, so\n'
            '`remove(S.alert(V.q))` takes one of the alerts and the event\n'
            'cannot say which. Re-read the space when you need to know;\n'
            '`m.live(pattern)` is the worked instance, and it is the rung above\n'
            'this one: a view is this subscription maintaining what a match would\n'
            'have answered.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_subscribe_is_the_function_watcher', 'extensions/python/tests/ch16_events_and_standing_queries/test_dispatch_index.py::test_dispatch_through_the_index_delivers_the_same_subscribers_in_the_same_order', 'extensions/python/tests/ch16_events_and_standing_queries/test_events.py::test_subscribe_bridge_and_reaction_are_expressible_over_the_public_event_stream'),
        async_signature=Signature('self, pattern: Any, *, on: str = "add", where: Any | None = None, queue_max: int = SUBSCRIPTION_QUEUE_MAX', returns=None),
        async_reason='the synchronous callback runs during delivery on the engine worker, while async consumers resume on their event loop. A caller callback cannot run on both threads; the async event stream is the delivery across that boundary and therefore has no callback parameter',
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:subscribe]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='prolog',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_prolog'),
        docs=(
            "Drop into the engine's own interactive Prolog toplevel, the\n"
            'deepest debugging lever there is: listing/1 shows compiled\n'
            'equations, trace/0 steps through them, and quitting the toplevel\n'
            "returns here with the session intact. janus's own janus.prolog(),\n"
            'surfaced where the debugging happens.\n'
            '\n'
            'This is the only Prolog-facing surface here besides register_prolog,\n'
            'and that is a decision rather than a gap. There is no public\n'
            '"call any Prolog goal" method: the supported way to reach your own\n'
            'Prolog from Python is to register it and call it as a MeTTa function,\n'
            'which keeps one set of conversion rules, one error taxonomy and one\n'
            "lock. A raw goal is janus's job and janus is importable directly.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_the_interactive_door_reaches_the_owned_runtime',),
        binding=Binding('janus.prolog', Wire.goal),
        async_excluded='an interactive Prolog toplevel belongs to a terminal thread',
    ),
    Door(
        owner=Owner.space,
        name='derivation',
        kind=Kind.introspection,
        signatures=(
            Signature('self, target: Any, depth: int | None=None, *, timeout: float | None=None, inferences: int | None=None', returns='list[Any]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_derivation'),
        docs=(
            'Every proof of an answer, as trees in MeTTa terms.\n'
            '\n'
            'Each tree names the equations that fired and the stored atoms at the\n'
            'leaves, read from the translated_from links the engine keeps for\n'
            'every compiled clause. Meta-interpreted, so slower than evaluation;\n'
            'a diagnostic, not an evaluation path. The default walks each proof\n'
            'without a depth cutoff. A positive depth returns a partial tree with\n'
            'Truncated nodes when its budget ends, so an empty list means no proof.\n'
            '`timeout` and `inferences` guard the whole search. An evaluation error\n'
            'inside a proof surfaces as itself rather than as an empty proof list.\n'
            '\n'
            'Building a proof executes every premise it records, including\n'
            'effectful operations. Engine writes persist and repeated derivations\n'
            'accumulate them, just as repeated evaluations do. Use\n'
            '``with space.speculative():`` when the proof should return while its\n'
            'engine writes are discarded. That scope cannot undo Python side\n'
            'effects, I/O, or subscription callbacks that already fired, so do not\n'
            'derive an effectful target when those effects must not happen.\n'
            '\n'
            'A `bind()` scope binds host values into the term, for the reason\n'
            'eval_status needs it: the substitution lands BEFORE the search, so the\n'
            'proof of an evaluation that binds anything was unaskable. Name keys\n'
            'mean symbols and atom keys mean themselves, so `bind({V.x: 5})` fills\n'
            'a variable hole. It takes no `theory` or\n'
            '`interpreter`, because a meta-interpreted diagnostic does not select an\n'
            'evaluation relation.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_per_space.py::test_derivation_follows_the_spaces_module', 'extensions/python/tests/ch05_equations_and_evaluation/test_per_ask_evaluation.py::test_derivation_binds_host_values_like_the_doors_beside_it', 'extensions/python/tests/ch14_seeing_your_program/test_derivation.py::test_a_cut_inside_once_stays_inside_it'),
    ),
    Door(
        owner=Owner.space,
        name='why',
        kind=Kind.introspection,
        signatures=(
            Signature('self, pattern: Any, *, where: Any | None=None', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_why'),
        docs=(
            'Why a pattern matches nothing here, in words.\n'
            '\n'
            'Checks the cheap explanations in order: unknown function, wrong\n'
            'arity, no stored atoms with that head. Honest when it cannot tell,\n'
            'and honest about the PREMISE too: a pattern that does match is a\n'
            'question with a false premise, and this refuses it the way\n'
            'Answers.why() always did rather than answering it. Asking why\n'
            '`(job $id $pri)` matched nothing, when it matches two atoms, used to\n'
            'answer "2 job atom(s) exist here but none unifies with it"\n'
            '[measured 2026-08-31].\n'
            '\n'
            "`where` is match()'s guard, and asking with one is where the answer\n"
            'gets interesting: a query can be empty because the pattern found\n'
            'nothing OR because the guard rejected everything it found, and only\n'
            'the guarded question can tell you which.\n'
            '\n'
            'One implementation, because there were two and they agreed word for\n'
            'word on every genuine miss while disagreeing about the premise.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_why', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_lint_and_why_agree_on_whether_a_head_is_known', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_why_and_lint_agree_about_a_call_at_an_undefined_arity'),
    ),
    Door(
        owner=Owner.space,
        name='define',
        kind=Kind.provider,
        signatures=(
            Signature(parameters='self, fn: _builtins.type[_T], /, *, accessors: bool=..., methods: bool=...', returns='_builtins.type[_T]', type_parameters='', declarations=('overload', 'dataclass_transform(eq_default=False)'), type_ignores=('overload-overlap',)),
            Signature(parameters='self, fn: Callable[_P, _R], /, *, name: str | None=..., accessors: bool=..., methods: bool=...', returns='Defined[_P, _R]', type_parameters='', declarations=('overload',), type_ignores=()),
            Signature(parameters='self, *, name: str', returns='Callable[[Callable[_P, _R]], Defined[_P, _R]]', type_parameters='', declarations=('overload',), type_ignores=()),
            Signature(parameters='self, *, prolog: str | os.PathLike[str], name: str | None=None', returns='Callable[[Callable[_P, _R]], PrologBacked[_P, _R]]', type_parameters='', declarations=('overload',), type_ignores=()),
            Signature(parameters='self, fn: Callable[..., Any] | None=None, *, prolog: str | os.PathLike[str] | None=None, name: str | None=None, accessors: bool=True, methods: bool=True', returns='Any', type_parameters='', declarations=(), type_ignores=()),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_define'),
        docs=(
            'Compile a Python function into MeTTa equations, decorator-style.\n'
            '\n'
            'With `prolog=`, the Prolog file is registered and becomes the\n'
            'function, and the Python stays as the reference twin rather than\n'
            'being compiled:\n'
            '\n'
            '    @m.define(prolog=Path(__file__).parent / "fast.pl")\n'
            '    def vec_dot(a, b):\n'
            '        return sum(x * y for x, y in zip(a, b))\n'
            '\n'
            '    m.eval("(vec-dot (1 2) (3 4))")[0] # the Prolog answer\n'
            '    vec_dot.py((1, 2), (3, 4))          # the reference answers\n'
            '\n'
            'Rewriting a defined function in Prolog for speed used to mean\n'
            'deleting the Python and the differential oracle with it. Here both\n'
            'are declared together and `metta.testing.check_twin` proves they\n'
            "agree on ground inputs. The file must register the function's own\n"
            "MeTTa name and at the twin's arity, inputs then one output, and\n"
            'says so if it does not; its `metta_export` declaration owns the\n'
            'types, so annotations on the Python are documentation only.\n'
            '\n'
            'Written for whoever is fluent in Python rather than s-expressions:\n'
            'the body is read as syntax and lowered deterministically, refusals\n'
            'name the construct, the line and what to write instead, and the\n'
            'original stays reachable as .py, a twin the equations can be checked\n'
            'against on any ground input.\n'
            '\n'
            '    @m.define\n'
            '    def add_one(n):\n'
            '        return n + 1\n'
            '\n'
            '    add_one(5)                  # [6], evaluated by the engine\n'
            '    S.add_one(5)                # (add_one 5), staged as data\n'
            '    add_one.py(5)               # 6, ordinary Python\n'
            '\n'
            "The equation's implicit name applies the factories' total mechanical\n"
            'map, replacing each underscore with a hyphen. ``name=`` is the exact\n'
            'quoted-name escape for punctuation that map cannot preserve:\n'
            '\n'
            '    @m.define(name="add-one")\n'
            '    def add_one(n):\n'
            '        return n + 1\n'
            '\n'
            'The same attribute mapping applies to the definition name itself:\n'
            '``def not_provable`` lands as ``not-provable``. An authored\n'
            'MeTTa underscore therefore uses explicit ``name="not_provable"``.\n'
            '\n'
            'A generator compiles to nondeterminism (each yield one answer), a\n'
            "lambda to the engine's own |->, a comprehension to map-atom and\n"
            'filter-atom, and match(Pattern(x, y), template) to a match against\n'
            'the running space, lowercase free names in the pattern binding as\n'
            'variables.\n'
        ),
        evidence=('extensions/python/tests/ch09_types/test_refinements.py::test_a_defined_head_refuses_a_violating_argument_by_name_and_accepts_the_rest', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_define_decorator_declares_field_types', 'extensions/python/tests/ch11_python_as_a_notation/test_authoring_surface.py::test_calling_a_defined_object_evaluates_and_an_unmatched_call_answers_itself'),
        alias='define',
        async_signature=Signature('self, fn: Callable | None = None, /, *, prolog: Any = None, name: Any = None, accessors: bool = True, methods: bool = True', returns='Any'),
        async_reason="the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the worker would register on the caller's thread rather than the engine's. Only the applied form crosses",
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:define]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='rules',
        kind=Kind.provider,
        signatures=(
            Signature('self, fn: Callable[..., Any]', returns='_Rules'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_rules'),
        docs=(
            'Collect and land a non-exclusive equation bundle in this space.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_authoring_surface.py::test_a_rules_generator_scopes_its_variables_to_its_parameters', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_rules_lower_emits_queryable_declaration_and_registers_the_head', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_rules_lower_refuses_an_empty_rule_set_before_mutating'),
    ),
    Door(
        owner=Owner.space,
        name='pre-add',
        kind=Kind.write,
        signatures=(
            Signature('self, fn: Defined[..., Any] | Callable[..., Any]', returns='Defined[..., Any]'),
        ),
        answers=AnswersAs.callable,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_pre_add'),
        docs=(
            "Compile or accept one unary judge and claim this space's write hook.\n"
            '\n'
            'The common decorator stack places ``@pre_add`` above ``@define``, so\n'
            'an existing Defined keeps the module that owns its equations. A raw\n'
            'function is compiled into this space before claiming the hook.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_library_surface_wave2.py::test_pre_add_compiles_the_four_verdict_judge', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_aio.py::test_async_rules_and_pre_add_land_as_awaitable_calls'),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:pre-add]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='type',
        kind=Kind.introspection,
        signatures=(
            Signature('self, atom: Any', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_type'),
        docs=(
            "Return this space's first ``get-type`` answer, including undefined.\n"
        ),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_p5_annotations.py::test_an_atom_in_annotation_position_is_the_type_itself', 'extensions/python/tests/ch09_types/test_inference.py::test_declaring_adds_exactly_the_proposals', 'extensions/python/tests/ch09_types/test_structural_aliases.py::test_a_failed_cycle_and_conflict_leave_previous_behavior_intact'),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_door_refuses_a_missing_engine_answer[type]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='infer-types',
        kind=Kind.write,
        signatures=(
            Signature('self, *, declare: bool=False', returns='list[Atom]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_infer_types'),
        docs=(
            'Propose a `(: head (-> ...))` for every head here that has none.\n'
            '\n'
            '    m.infer_types()                 # the proposals, nothing added\n'
            '    m.infer_types(declare=True)     # add exactly those proposals\n'
            '\n'
            'One walk of the stored atoms names the narrowest kind covering the\n'
            'children observed at each argument position: all numbers `Number`,\n'
            'all strings `String`, all booleans `Bool`, all symbols `Symbol`, all\n'
            "expressions sharing one head that head's declared result type when it\n"
            'has one and `Expression` otherwise, mixed `Atom`. A variable observed\n'
            'at a position stands for anything and constrains nothing, so a\n'
            'position with only variables is `%Undefined%`. That is\n'
            "`pandas.api.types.infer_dtype` moved from a column's values to an\n"
            "argument position's children, its `skipna` included.\n"
            '\n'
            "An equation head's RESULT is what its body answers: a literal's own\n"
            'type, or the declared result of the head the body calls, which is how\n'
            '`(= (double $x) (* $x 2))` proposes `(-> %Undefined% Number)`.\n'
            'Anything else, a bare symbol included, is `%Undefined%`, because a\n'
            "symbol's own type is `%Undefined%` here too. A head observed at two\n"
            'arities gets one proposal per arity, and a head this space already\n'
            'declares gets none.\n'
            '\n'
            '`declare=True` adds exactly the returned atoms and nothing else, so\n'
            "`get-type` then answers them. One thing changes with the program's\n"
            'BEHAVIOUR and is worth reading before a proposal is accepted: `Atom`\n'
            'in an argument position is a metatype and stops the engine evaluating\n'
            'that argument, so a mixed position turns `(f (+ 1 2))` from `3` into\n'
            'the term `(+ 1 2)` [measured 2026-09-07]. Proposing and adding are\n'
            'two calls for that reason.\n'
            '\n'
            'Cost is O(atoms x arity): one pass over the space, plus one type\n'
            'lookup per distinct head. `metta.stubs()` and `inspect.signature()`\n'
            'show the same arrows, marked inferred, without adding anything.\n'
        ),
        evidence=('extensions/python/tests/ch09_types/test_inference.py::test_a_catalogue_row_is_not_data_about_a_head', 'extensions/python/tests/ch09_types/test_inference.py::test_a_declared_head_is_skipped', 'extensions/python/tests/ch09_types/test_inference.py::test_a_nested_call_carries_its_heads_declared_result'),
    ),
    Door(
        owner=Owner.space,
        name='doc',
        kind=Kind.introspection,
        signatures=(
            Signature('self, atom: Any', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_, Tier.module, Tier.context,),
        body=Body('metta._space', 'Space._door_doc'),
        docs=(
            "Return this space's structured ``get-doc`` answer for one subject.\n"
            '\n'
            'The answer is the ``(@doc ...)`` atom the engine holds for the\n'
            'subject, whether it was documented in MeTTa source or built from a\n'
            'Python docstring:\n'
            '\n'
            '    m.doc(S.area)\n'
            '    # (@doc-formal (@item area) (@kind function) (@desc "Circle area.") ...)\n'
            '\n'
            'A subject with no documentation raises, exactly as ``type`` raises\n'
            'for a subject ``get-type`` cannot answer.\n'
        ),
        evidence=('extensions/python/tests/ch08_data/test_library_card.py::test_a_card_documents_what_the_library_documents', 'extensions/python/tests/ch09_types/test_refinements.py::test_doc_and_timezone_stay_in_the_annotation_claim', 'extensions/python/tests/ch11_python_as_a_notation/test_define.py::test_one_docstring_reaches_help_dot_doc_and_get_doc'),
        alias='doc',
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_door_refuses_a_missing_engine_answer[doc]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='fn',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='_FunctionNamespace', declarations=('property',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_fn'),
        docs=(
            'Functions visible here, as bound attribute or exact-name handles.\n'
            '\n'
            '    car = m.fn.car_atom\n'
            '    car(m.parse("(1 2 3)"))     # [1]\n'
            '    m.fn["=="](1, 1).one()      # True\n'
            '\n'
            'Underscores transliterate to hyphens. Brackets preserve exact\n'
            'punctuation, and an unknown name raises at access rather than\n'
            'becoming a later empty evaluation.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_fn_decodes_exactly_as_value', 'extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_fn_doors_split_the_same_way', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call'),
        is_property=True,
    ),
    Door(
        owner=Owner.space,
        name='integrate',
        kind=Kind.provider,
        signatures=(
            Signature('self, target: Any', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_integrate'),
        docs=(
            'Install a library integration; see metta.integrate.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_restores_registry_preimages', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_unwinds_every_framework_registration', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_outer_installation_unwinds_its_completed_dependency'),
    ),
    Door(
        owner=Owner.space,
        name='handles',
        kind=Kind.provider,
        signatures=(
            Signature('self, pattern: str | Atom, fidelity: Fidelity, *, det: Determinism | None=None', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_handles'),
        docs=(
            'Declare how faithfully a space answers queries of one shape.\n'
            '\n'
            'The declaration is one (handles ...) atom in &metta, and queries\n'
            'are routed by the most specific declared shape that matches:\n'
            "Exact licenses pushing the caller's bound to the provider, Partial\n"
            'and Sound stay candidates the engine re-unifies, and Refuse makes\n'
            'the query a loud error instead of a silent partial answer. Write\n'
            '(in $x) at a position to match only queries arriving with it\n'
            'bound, so a scan-only source is three words:\n'
            '\n'
            '    rows.handles("(edge (in $a) $b)", "Refuse")\n'
            '\n'
            'Coherence is checked eagerly in the same transaction as the\n'
            'write: a new entry that can disagree with an existing one on some\n'
            'query fails here, naming both, rather than on the first query\n'
            'that falls into their overlap. The atom is returned; removing it\n'
            'from &metta withdraws the declaration.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_a_sql_backed_space_under_declared_handles', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_declare_handles_keeps_repeated_variables_shared', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_declare_handles_rejects_a_conflict_eagerly'),
        binding=Binding('metta_py_declare_handles', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='annotations',
        kind=Kind.provider,
        signatures=(
            Signature('self, subject_or_algebra: str, algebra: str | None=None, *, capabilities: _abc.Iterable[str]=()', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_annotations'),
        docs=(
            "Declare the algebra a context's answer annotations live in.\n"
            '\n'
            'A context is a space name or an operation name. bool is the\n'
            'default at which everything vanishes; ranked admits ordered\n'
            'annotations, which is what (top k ...) consumes. A custom name must\n'
            'first be introduced with :meth:`algebra`. A one-argument call uses\n'
            'this space as the context; the two-argument form keeps an operation\n'
            'context as the explicit first subject. Capabilities are\n'
            "checked against the algebra's requirements before the catalog write;\n"
            'amplitude programs, for example, must explicitly declare ``finite``,\n'
            '``contractive`` and ``staged`` [tested:\n'
            'test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside;\n'
            'commit=f88aa8be03cb64cb59d3307515ded8701f418321]. Declaring replaces any earlier row for the\n'
            'context, so the reader never meets two disagreeing atoms.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_annotations_validates_and_replaces', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_prov_annotations_carry_source_terms', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_top_orders_mixed_integer_and_float_annotations_by_value'),
    ),
    Door(
        owner=Owner.space,
        name='algebra',
        kind=Kind.provider,
        signatures=(
            Signature('self, name: str, *, combine: str, extend: str, zero: Any, one: Any, laws: _abc.Iterable[str]=(), carrier: _abc.Iterable[Any]=(), type: Any=None, requires: _abc.Iterable[str]=(), order: SemiringOrder | None=None', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_algebra'),
        docs=(
            'Declare operations with carrier membership and optional checked laws.\n'
            '\n'
            '``type`` accepts a Python type, MeTTa type atom, or Boolean predicate\n'
            'and checks every input and result. A type alone grants no laws or\n'
            'fusion. ``carrier`` enumerates the finite domain required for exhaustive\n'
            'law checking; it may accompany ``type`` to constrain that domain.\n'
            'Use ``prov`` and ``.under()`` to reinterpret uncertified tensor traces.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_drop_retires_algebra_before_redeclaration', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_rollback_releases_an_algebra_mirror', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_rollback_restores_a_replaced_algebra_mirror'),
    ),
    Door(
        owner=Owner.space,
        name='covers',
        kind=Kind.write,
        signatures=(
            Signature('self, effect: EffectClass | str', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_covers'),
        docs=(
            'Declare the strongest effect this reified world can handle.\n'
            '\n'
            'Coverage is a catalog fact ``(covers <space> <effect>)``. World\n'
            'evaluation always admits pureStructural plans. A stronger joined plan\n'
            'runs only when this declaration is at least as strong; redeclaring\n'
            'replaces the previous row atomically.\n'
            '\n'
            '    orders.covers("writesState")\n'
            '    world = orders.reify()\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_arrow_products.py::test_world_coverage_uses_the_annotated_effect', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_a_closed_world_releases_its_plan_image', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_a_collected_world_does_not_take_the_name_a_live_mint_released'),
    ),
    Door(
        owner=Owner.space,
        name='compensates',
        kind=Kind.write,
        signatures=(
            Signature('self, operation: str, compensation: str', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_compensates'),
        docs=(
            'Declare one recovery operation for an effectful operation.\n'
            '\n'
            'The catalog row is ``(compensates operation compensation)``. The\n'
            'source operation must already be registered at writesState or\n'
            'oracleIO, because weaker operations leave no saga receipt. The\n'
            'recovery name must already be a host operation or compiled MeTTa\n'
            'function. It receives the complete ``(did ...)`` receipt. The runner writes\n'
            'the call as ``(quote <receipt>)`` so the receipt is not evaluated\n'
            'on the way in; the quote is a barrier and does not survive, so the\n'
            'handler is handed the receipt itself.\n'
            'Redeclaring replaces the old row atomically.\n'
        ),
        evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_a_refused_recovery_receipt_still_compensates_the_effect_it_could_not_record', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_saga_compensates_in_reverse_commit_order', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_a_discarded_step_runs_no_compensation'),
    ),
    Door(
        owner=Owner.space,
        name='add-tagged-fact',
        kind=Kind.write,
        signatures=(
            Signature('self, tag: Any, proposition: Any', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_add_tagged_fact'),
        docs=(
            'Store ``(fact tag proposition)``, the normative annotation form.\n'
        ),
        evidence=('extensions/python/tests/ch18_performance/test_algebra_rates.py::test_invalid_rates_are_refused_before_the_tagged_fact_lands', 'extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_tagged_call_answers_use_the_carrier_without_hijacking_other_calls', 'extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_tagged_derivations_flow_through_match_and_reinterpret_without_requery'),
    ),
    Door(
        owner=Owner.space,
        name='add-tagged-rule',
        kind=Kind.write,
        signatures=(
            Signature('self, tag: Any, head: Any, *premises: Any', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_add_tagged_rule'),
        docs=(
            'Store one rule generated by the algebra-agnostic tag threader.\n'
        ),
        evidence=('extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_tagged_derivations_flow_through_match_and_reinterpret_without_requery', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_tagged_algebra_debits_inferences_across_operations', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_tagged_algebra_forwards_bounds_to_every_evaluating_door'),
    ),
    Door(
        owner=Owner.space,
        name='image',
        kind=Kind.write,
        signatures=(
            Signature('self, type_name: str, setting: ImageMode', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_image'),
        docs=(
            'Choose how one Python type crosses one context boundary.\n'
            '\n'
            'opaque carries the live object by identity; transparent projects its\n'
            "structural MeTTa image; auto makes that choice from the value's size\n"
            'and replayability. A later declaration for the same context and type\n'
            'replaces the earlier one, so an attached provider reads one policy.\n'
            'Use ``_`` as the type name for a context-wide fallback.\n'
        ),
        evidence=('extensions/python/ext/metta-pydantic/tests/test_pydantic.py::test_the_row_is_registered_against_the_image_point', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_restores_registry_preimages', 'extensions/python/tests/ch20_extending_the_engine/test_catalog_kinds.py::test_the_image_declaration_is_catalog_validated'),
    ),
    Door(
        owner=Owner.space,
        name='sample',
        kind=Kind.evaluation,
        signatures=(
            Signature('self, query: str | Atom, *, k: int=10, seed: int=7', returns='list[Atom]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_sample'),
        docs=(
            'Choose ``k`` tagged alternatives with replacement by ``(rate n)``.\n'
            '\n'
            'The argument names and list result follow ``random.choices``. A local\n'
            'seeded generator makes repeated calls reproducible without changing\n'
            "Python's process-global random state.\n"
        ),
        evidence=('extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_space_sample_is_seeded_and_uses_k_vocabulary', 'extensions/python/tests/ch18_performance/test_algebra_rates.py::test_declared_rates_make_seeded_selection_match_their_distribution'),
    ),
    Door(
        owner=Owner.space,
        name='consumption',
        kind=Kind.write,
        signatures=(
            Signature('self, kind: SourceKind', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_consumption'),
        docs=(
            "Declare a space's consumption discipline.\n"
            '\n'
            'repeated is the default: the source re-enumerates. linear is a\n'
            'one-shot source, a cursor or a feed: its SECOND consumption is a\n'
            'loud error naming the space, where the undeclared floor answers a\n'
            'silently empty set from the drained object; re-registering the\n'
            'provider resets the mark, because a fresh provider is a fresh\n'
            'source. peek promises reads do not consume, which the conformance\n'
            'kit checks by enumerating twice. The Python door is named\n'
            '``consumption`` so ``source()`` can show program text; the MeTTa\n'
            'catalog row deliberately keeps its language-level ``source`` head.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_a_linear_source_refuses_its_second_consumption', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_consumption_validates', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_explain_answers_the_route_and_the_route_is_honest'),
    ),
    Door(
        owner=Owner.space,
        name='on-error',
        kind=Kind.write,
        signatures=(
            Signature('self, subject_or_pattern: str | Atom, pattern_or_mode: str | Atom, mode: OnError | None=None', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_on_error'),
        docs=(
            "Declare what a context's failure becomes, per query shape.\n"
            '\n'
            "abort is the undeclared floor: the provider's error propagates.\n"
            'keep delivers the failure as one (Error <query> <reason>) answer\n'
            "beside the answers that already streamed, the language's own\n"
            'error-as-alternative reading. empty ends the stream silently, BY\n'
            'declaration, which is what separates it from a swallowed error.\n'
            'Shapes route most-specific-first exactly as (handles ...) entries\n'
            'do. Control signals and transport failures are never kept or\n'
            "emptied: an interrupt is the caller's, and an absent backend has\n"
            'said nothing about the data.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_on_error_validates', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_an_op_keeps_its_failure_as_the_error_atom', 'extensions/python/tests/ch11_python_as_a_notation/test_ops.py::test_relational_candidate_shape_errors_are_contract_errors'),
        binding=Binding('metta_py_add', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='merge',
        kind=Kind.write,
        signatures=(
            Signature('self, pattern: str | Atom, policy: AnswerPolicy', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_merge'),
        docs=(
            "Declare how the engine merges one query shape's answers\n"
            'ACROSS contexts, for the multi-context idiom\n'
            '(match (superpose (&a &b)) ...).\n'
            '\n'
            "depth is today's space-after-space order and the undeclared\n"
            'floor. fair interleaves the streams round-robin. best-first is a\n'
            'k-way ordered merge by annotation, sound only when every merged\n'
            'context declares (emits <ctx> best-first), and loudly refused\n'
            'without. Shapes route most-specific-first as everywhere.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_best_first_merge_orders_across_contexts', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_declared_fair_merge_interleaves', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_merge_validates'),
        binding=Binding('metta_py_add', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='context',
        kind=Kind.write,
        signatures=(
            Signature('self, world: World', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_context'),
        docs=(
            "Record what a space's absence means.\n"
            '\n'
            'Negation as failure reads absence as falsity, which is only\n'
            'sound over a world the answerer holds whole, so a negated goal\n'
            'may consult a foreign space only when it declares closed-world;\n'
            'an undeclared one refuses under negation loudly. Native spaces\n'
            "are the engine's own database and closed by construction.\n"
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_context_validates', 'extensions/python/ext/metta-otel/tests/test_otel.py::test_spans_nest_by_the_events_own_depth', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_explain_answers_the_route_and_the_route_is_honest'),
    ),
    Door(
        owner=Owner.space,
        name='agenda',
        kind=Kind.write,
        signatures=(
            Signature('self, policy: AgendaPolicy, function: str | None=None', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_agenda'),
        docs=(
            'Declare which reaction fires first when several match one write.\n'
            '\n'
            'declaration is the default and the order they were declared, which is\n'
            'what the engine produced by accident before this was a policy;\n'
            'recency is the most recently declared first; specificity is the most\n'
            "tests in the pattern first; priority reads each reaction's own\n"
            'declared number, highest first; and user names a MeTTa function that\n'
            'SCORES a reaction, highest first. Every policy breaks ties on\n'
            'declaration order.\n'
            '\n'
            '    alarms.reacts("(alert $w)", "(insert &log (all $w))")\n'
            '    alarms.reacts("(alert fire)", "(insert &log (fire))", priority=9)\n'
            '    alarms.agenda("priority")\n'
        ),
        evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_every_declaration_door_removes_every_stale_duplicate',),
        refuses=(
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:agenda]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='reacts',
        kind=Kind.write,
        signatures=(
            Signature('self, pattern: str | Atom, operation: str | Atom, priority: int | None=None', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_reacts'),
        docs=(
            'Declare a reaction, stored as an (on ...) atom: when an atom\n'
            'matching PATTERN lands in the space, OPERATION runs under the\n'
            "match's bindings.\n"
            '\n'
            'The managed heads are (insert <ctx> <atom>), (retract <ctx>\n'
            '<atom>) and (revise <ctx> <old> <new>), engine-routed rules\n'
            'going through the same write paths as direct writes. Declaring\n'
            "installs the engine's write hook, which is why reactions go\n"
            'through here or metta_install_bridges rather than a bare\n'
            'add-atom.\n'
            '\n'
            'A subscription bridge is the NEIGHBOUR, not a special case of this:\n'
            "a reaction's operation runs engine-side, so it reaches registered\n"
            'spaces, while the bridge rule delivers Python-side to anything\n'
            'with add and remove, an unregistered or remote target included.\n'
            'Same multi-context-systems idea, two delivery tiers.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_bridge_cascade_is_bounded', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_bridge_inserts_under_the_matched_bindings', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_revise_bridge_replaces'),
        binding=Binding('metta_install_bridges', Wire.goal),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:reacts]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='admits',
        kind=Kind.write,
        signatures=(
            Signature('self, type_name: str', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_admits'),
        docs=(
            "Type a pool's membership: only TYPE-carrying atoms enter.\n"
            '\n'
            'A thread pool is a space whose atoms are spaces, and this is its\n'
            'declaration: (admits &pool Space) plus per-atom (: <space> Space)\n'
            'declarations make membership a type judgement the ontology\n'
            'already knows how to make.\n'
        ),
        evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_admission_routes.py::test_relative_admits_declaration_installs_the_receiver_contract', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_admission_is_sugar_over_the_pre_add_hook', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_admission_types_the_pool'),
        binding=Binding('metta_admission_claim', Wire.goal),
    ),
    Door(
        owner=Owner.space,
        name='capacity',
        kind=Kind.write,
        signatures=(
            Signature('self, limit: int', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_capacity'),
        docs=(
            'Bound a pool: an add beyond LIMIT atoms is refused loudly.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_capacity_bounds_the_pool', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_capacity_validates', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_admission_routes.py::test_relative_capacity_declaration_installs_the_receiver_contract'),
        binding=Binding('metta_admission_claim', Wire.goal),
        refuses=(
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:capacity]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='atomicity',
        kind=Kind.write,
        signatures=(
            Signature('self, atomicity: Atomicity', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_atomicity'),
        docs=(
            "Declare what a space's writes promise inside a transaction.\n"
            '\n'
            'Named for what it declares rather than for the atom it stores, which\n'
            'stays `(writes <ctx> ...)`: `writes` on a Space is the effect\n'
            'decorator for an OPERATION, and one object cannot spell two concepts\n'
            'one way.\n'
            '\n'
            'transactional providers implement metta.foreign.Transactional and\n'
            "are committed or rolled back WITH the engine's transaction;\n"
            "best-effort is the author's declared acceptance of a write that\n"
            'survives a rollback; atomic-single refuses transactional writes.\n'
            'Undeclared spaces refuse them loudly too, because a foreign write\n'
            'silently surviving a rolled-back transaction is the wrong answer\n'
            'the declaration exists to replace.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_failed_file_transaction_rolls_a_foreign_provider_back', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_failed_transaction_rolls_both_stores_back', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_file_transaction_enlists_and_commits_a_foreign_provider'),
    ),
    Door(
        owner=Owner.space,
        name='emits',
        kind=Kind.write,
        signatures=(
            Signature('self, policy: AnswerPolicy', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_emits'),
        docs=(
            'Declare the order a context emits its own answers in.\n'
            '\n'
            'best-first is the promise (top k ...) needs before its bound may\n'
            'reach the provider: the first k of a best-first emission ARE the\n'
            'k best. Distinct from the (merge <pattern> <policy>) strategy,\n'
            'which is how the ENGINE merges answers across several contexts.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_emits_validates', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_best_first_merge_orders_across_contexts', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_top_pushes_the_bound_under_three_declarations'),
    ),
    Door(
        owner=Owner.space,
        name='events',
        kind=Kind.write,
        signatures=(
            Signature('self, delivery: Delivery | None=None, order: EventOrder=EventOrder.unordered', returns='Atom | Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync, Tier.async_,),
        body=Body('metta._space', 'Space._door_events'),
        docs=(
            'Return the event stream, or declare what this context promises.\n'
            '\n'
            'Subscribability is a promise about the context, not something its\n'
            'methods alone establish. A native space needs no declaration:\n'
            "every write into it runs the engine's own hooks, so it delivers\n"
            'per-write-exactly and ordered by construction. A FOREIGN context\n'
            'declares, and one that declares nothing refuses a subscription\n'
            'instead of serving one that silently misses writes.\n'
            '\n'
            '    shared.events("at-most-once")   # redis pub/sub\n'
            '    mirror.events("per-write-exactly", "ordered")\n'
            '\n'
            'delivery is at-most-once, at-least-once or per-write-exactly, and\n'
            'order is ordered or unordered, defaulting to unordered because an\n'
            'omitted promise is the weaker one. A Python provider says the same\n'
            'thing by overriding delivers(), which registration writes here.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_events_delivers_leftovers_queued_before_cancel', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_events_times_out_quiet_and_refuses_callback_mode', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_subscription_is_a_context_manager_and_events_stream'),
    ),
    Door(
        owner=Owner.space,
        name='runtime',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='Runtime', declarations=('property',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_runtime'),
        docs=(
            'The engine bridge itself, for callers going under the surface.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
    ),
    Door(
        owner=Owner.space,
        name='metta',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='MeTTa', declarations=('property',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'Space._door_metta'),
        docs=(
            'The owning evaluation context, so a handle can reach every\n'
            'context-level method: ``m.metta.space(S.kb)`` creates a sibling space\n'
            "in THIS handle's own context rather than the process default, which\n"
            "is the creation method the twins' known-issue asked for. The context\n"
            "BORROWS this handle's space as its home, so answering it mints\n"
            'nothing, and two answers compare equal because they share the\n'
            'runtime and the home.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
    ),
    Door(
        owner=Owner.space,
        name='alpha',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Any', returns='Expression'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.alpha'),
        docs=(
            'The alpha-equality TERM, (=alpha self other); alpha_eq answers now.\n'
            '\n'
            'The nearest-relative spelling of the head whose `=` marker Python\n'
            'cannot carry, exactly as eq() spells ==; compiled bodies write the\n'
            'same test as a bare alpha(x, y) call, and fn["=alpha"] stays the\n'
            'exact form.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='alpha-eq',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Atom', returns='bool'),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.alpha_eq'),
        docs=(
            'Whether two atoms differ only by consistent variable renaming.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='args',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='tuple[Atom, ...]', declarations=('property',)),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.args'),
        docs=(
            'Read Space.args.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
        is_property=True,
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:args]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='children',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='tuple[Atom, ...]', declarations=('property',)),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.children'),
        docs=(
            'Read Space.children.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
        is_property=True,
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:children]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='eq',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Any', returns='Expression'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.eq'),
        docs=(
            'The equality TERM, (== self other); == itself compares atoms.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='ge',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Any', returns='Expression'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.ge'),
        docs=(
            'The greater-or-equal TERM, (>= self other).\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='gt',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Any', returns='Expression'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.gt'),
        docs=(
            'The strictly-greater TERM, (> self other).\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='head',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='Atom | None', declarations=('property',)),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.head'),
        docs=(
            'Read Space.head.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
        is_property=True,
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:head]'),
        ),
    ),
    Door(
        owner=Owner.space,
        name='le',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Any', returns='Expression'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.le'),
        docs=(
            'The less-or-equal TERM, (<= self other).\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='lt',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Any', returns='Expression'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.lt'),
        docs=(
            'The strictly-less TERM, (< self other).\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='map',
        kind=Kind.introspection,
        signatures=(
            Signature('self, transform: Callable[[Atom], Atom]', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.map'),
        docs=(
            'Transform every node, children before parents, without recursion.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='ne',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Any', returns='Expression'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.ne'),
        docs=(
            'Read Space.ne.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='subs',
        kind=Kind.introspection,
        signatures=(
            Signature('self, bindings: Mapping[Atom, Any] | Any', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.subs'),
        docs=(
            'Replace each atom the bindings name, everywhere it occurs.\n'
            '\n'
            '    pattern = S.job(V.who, V.rank)\n'
            '    pattern.subs(pattern.unify(S.job(S.ada, 9)))   # (job ada 9)\n'
            '    S.hired(V.who).subs(space.match(pattern)[0])   # (hired ada)\n'
            '    S.greet(S.name).subs({S.name: "ada"})          # (greet "ada")\n'
            '\n'
            'The KEY says what is being replaced, so a variable hole and a\n'
            'placeholder symbol are different substitutions rather than one\n'
            'ambiguous string. ``unify`` produces variable keys; a ``bind()`` scope\n'
            'at the evaluation methods accepts either.\n'
            '\n'
            'An answer ``Row`` is accepted directly, because its columns ARE the\n'
            "query's variable names. It is the library's other producer of\n"
            'bindings, and it could not be fed back either.\n'
            '\n'
            'Sugar over :meth:`map`, which stays available as the lower-level method:\n'
            'this is ``atom.map(lambda item: bindings.get(item, item))`` with the\n'
            'keys and values encoded. Nothing consumed a substitution before this,\n'
            'so both producers answered in a currency the library did not accept,\n'
            'and two tests had written the recursive walk by hand.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='unify',
        kind=Kind.introspection,
        signatures=(
            Signature('self, other: Atom, *more: Atom', returns='Mapping[Atom, Atom] | None'),
        ),
        answers=AnswersAs.mapping,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.unify'),
        docs=(
            'Unify with the others, returning bindings or ``None``.\n'
            '\n'
            'Variadic means SIMULTANEOUS: every operand must agree under ONE\n'
            'substitution, folded through one shared binding store, so several\n'
            'rule heads unify at once the way two always did. The keys are the\n'
            'VARIABLES themselves, which is the currency :meth:`subs` accepts,\n'
            'so ``template.subs(pattern.unify(fact))`` is the round trip. They\n'
            'were plain names once, and a name cannot say whether it means a\n'
            'variable or a symbol in a language that has both.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
    ),
    Door(
        owner=Owner.space,
        name='vars',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='tuple[Variable, ...]', declarations=('property',)),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._atoms_core', 'Atom.vars'),
        docs=(
            'The variables in first-appearance order; none means ground.\n'
            '\n'
            'The variables THEMSELVES, not their names, so what this answers is\n'
            'what :meth:`subs` and :meth:`unify` accept and a round trip composes:\n'
            '``template.subs(dict(zip(pattern.vars, values)))``. Names were what it\n'
            'answered once, and a name cannot say whether it means a variable or a\n'
            'symbol on a surface that has both. ``not atom.vars`` still reads\n'
            '"ground", because an empty tuple is still empty.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any,
        inherited=True,
        is_property=True,
    ),
    Door(
        owner=Owner.context,
        name='close',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_close'),
        docs=(
            "Release the context's own home space; closing twice is a no-op.\n"
            '\n'
            "A borrowed home, the process default included, is the caller's\n"
            'and survives; only a home this context minted is dropped, and the\n'
            'drop takes the whole world with it: every space minted inside the\n'
            "context, by this object or by the program's own new-space, is\n"
            "released first, since it read the home's equations and cannot\n"
            'outlive it. A space the program declared with (inherits ...) still\n'
            'refuses, naming the heir, because that relationship is the\n'
            "program's own.\n"
            '\n'
            'What a context OPENED by name it borrows and leaves alone, the way\n'
            'it leaves a borrowed home alone: ``m.space("&kb")`` may be a space\n'
            'that already existed, that another context is reading, or that the\n'
            'engine owns, and closing a reader is not how any of those end.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_drop_recovery.py::test_backing_close_failure_keeps_the_name_and_cleanup_retryable', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_borrowed_home_survives_close', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_context_close_leaves_a_named_space_it_only_opened'),
        state=State.any,
    ),
    Door(
        owner=Owner.context,
        name='closed',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self', returns='bool', declarations=('property',)),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_closed'),
        docs=(
            "Whether :meth:`close` has released this context's own home.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
    ),
    Door(
        owner=Owner.context,
        name='self',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='Space', declarations=('property',)),
        ),
        answers=AnswersAs.space,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_self'),
        docs=(
            "The context's home space handle, its own ``&self``.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
    ),
    Door(
        owner=Owner.context,
        name='runtime',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='Runtime', declarations=('property',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_runtime'),
        docs=(
            'The engine bridge itself, for callers going under the surface.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=State.any,
        is_property=True,
    ),
    Door(
        owner=Owner.context,
        name='info',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='dict[str, str | None]'),
        ),
        answers=AnswersAs.mapping,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_info'),
        docs=(
            'Return backend versions and the consulted MeTTa runtime tree.\n'
        ),
        evidence=('extensions/python/tests/ch01_getting_started/test_backend_info.py::test_backend_info_reports_versions_and_consulted_tree',),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_info_refuses_an_unreported_engine_version'),
        ),
    ),
    Door(
        owner=Owner.context,
        name='lock',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='Lock'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_lock'),
        docs=(
            'Pin the knowledge this context has loaded, as a `Lock`.\n'
            '\n'
            '    m.load("kb/facts.metta")\n'
            '    m.lock().write("metta.lock")\n'
            '    python -m metta lock kb/facts.metta -o metta.lock\n'
            '\n'
            'One `[[library]]` row per shipped library imported, one `[[source]]`\n'
            'row per other file loaded with the space it landed in, one `[[pin]]`\n'
            'row per repository revision acquired, and an `[engine]` table naming\n'
            'this build and a digest over its own sources: what a second machine\n'
            'needs to load exactly this program. `metta.Lock.read` reads one back\n'
            'and :meth:`check` says what a tree no longer matches.\n'
            '\n'
            "The scope is the PROCESS, not this context. The engine's loads,\n"
            'registrations and git pins are process-wide, and a program that loads\n'
            'knowledge into `&kb` from one place and reads it from another is one\n'
            "program; a lock naming only one context's own loads would omit the\n"
            'rest of what has to be reproduced. Two contexts in one process\n'
            'therefore take the same lock.\n'
            '\n'
            'A lock taken while a source is still loading is refused, because it\n'
            'would record a program that is only half there.\n'
        ),
        evidence=('extensions/python/tests/ch01_getting_started/test_lock.py::test_a_drifted_engine_names_the_field_that_moved', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_drift_refusal_names_every_entry_and_its_repair', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_is_readable_toml_with_the_documented_tables'),
    ),
    Door(
        owner=Owner.context,
        name='check',
        kind=Kind.introspection,
        signatures=(
            Signature('self, lock: Lock', returns='list[Drift]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_check'),
        docs=(
            'Every entry of a lock this tree no longer matches, as `Drift` rows.\n'
            '\n'
            '    for drift in m.check(metta.Lock.read("metta.lock")):\n'
            '        print(drift)\n'
            '\n'
            'An empty list is agreement. Nothing is loaded to answer it: each entry\n'
            'names something on disk, so the answer is what a fresh process would\n'
            'find rather than what this one happens to hold. `metta run --locked`\n'
            'is the same check with a refusal instead of a list.\n'
        ),
        evidence=('extensions/python/tests/ch01_getting_started/test_lock.py::test_a_drifted_engine_names_the_field_that_moved', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_round_trips_through_its_file', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_removed_source_drifts_as_not_present'),
    ),
    Door(
        owner=Owner.context,
        name='space',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self, name: str | Symbol | Expression | Space | None=None, backing: Any=None, *, inherits: Space | None=None, restricted: bool=False, grants: _abc.Iterable[str]=(), journal: str | os.PathLike[str] | None=None, schema: _abc.Mapping[str, Any] | None=None, sync: JournalSync=JournalSync.none, rename: _abc.Mapping[str, str] | None=None, _created_at: tuple[str, int] | None=None', returns='Space'),
        ),
        answers=AnswersAs.space,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_space'),
        docs=(
            'Create one native, provider-backed, remote, or journaled space.\n'
            '\n'
            'The BACKING value derives the implementation, so the common calls\n'
            'carry no options at all: with no name the engine mints an anonymous\n'
            'handle; a ``Space`` reopens that same space, which is what an engine\n'
            'answer naming one arrives as; a ``SpaceProvider`` backing is\n'
            'attached directly; an HTTP(S) URL becomes a remote provider (build\n'
            'the transport with ``metta.remote.connect`` when it needs a token,\n'
            'headers, or its own timeout, and hand THAT in as the backing); and\n'
            '``journal=`` constructs ``PersistentFactSpace`` from ``schema=`` or\n'
            'a schema mapping supplied as the backing. ``sync`` paces the\n'
            'journal and ``rename`` performs its one-open schema migration; neither\n'
            'means anything without ``journal``, so either refuses alone.\n'
            '\n'
            '``inherits``, ``restricted`` and ``grants`` choose the space MODEL and\n'
            "are independent of whether the space is named. MeTTa's own\n"
            '``!(new-space &locked (restricted))`` names a restricted space, and\n'
            '``metta.space(S.locked, restricted=True)`` is that call. Declaring a\n'
            'model on a name that already carries the same one is a no-op; a\n'
            'different one raises, because a space cannot have two models.\n'
            '\n'
            'The context OWNS what it mints and BORROWS what it opens by name:\n'
            ':meth:`close` releases the anonymous mints and leaves ``&kb``,\n'
            '``&metta`` and every other named space exactly as it found them,\n'
            'whether or not the handle is still referenced.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_context_owns_and_releases_its_minted_home', 'extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol'),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[context:space]'),
        ),
    ),
    Door(
        owner=Owner.context,
        name='fn',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='_FunctionNamespace', declarations=('property',)),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.readOnlyLookup,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_fn'),
        docs=(
            "The bound function namespace of this context's self space.\n"
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_fn_decodes_exactly_as_value', 'extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_fn_doors_split_the_same_way', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call'),
        is_property=True,
    ),
    Door(
        owner=Owner.context,
        name='unregister-op',
        kind=Kind.provider,
        signatures=(
            Signature('self, name: str', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_unregister_op'),
        docs=(
            'Release an operation installed through :meth:`op`.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_shared_class_declarations_survive_one_unregister', 'extensions/python/tests/ch11_python_as_a_notation/test_ops.py::test_unregistering_a_name_a_system_predicate_shares_does_not_throw', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_unregister_removes_the_effect_atom_with_the_op_facts'),
    ),
    Door(
        owner=Owner.context,
        name='capture',
        kind=Kind.scope,
        signatures=(
            Signature('self', returns='CapturedOutput'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_capture'),
        docs=(
            'Capture printed engine text across this context.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_capture_composes_with_limits', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_eval_capture', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_capture_collects_held_engine_output'),
    ),
    Door(
        owner=Owner.context,
        name='atomic',
        kind=Kind.scope,
        signatures=(
            Signature('self', returns='ScopedExecution'),
        ),
        answers=AnswersAs.context,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_atomic'),
        docs=(
            'Scope source execution to committing transactions.\n'
        ),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_an_atomic_scope_makes_one_python_write_one_transaction', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_atomic_run_commits_or_rolls_back_whole', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_atomic_rolls_back_after_a_late_cursor_failure'),
    ),
    Door(
        owner=Owner.context,
        name='transaction',
        kind=Kind.scope,
        signatures=(
            Signature('self, target: Callable[[], _R], /', returns='_R', declarations=('overload',)),
            Signature('self, target: Atom | str, /', returns='list[Atom | Undefined]', declarations=('overload',)),
            Signature('self, target: Any, /', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_transaction'),
        docs=(
            'Run one callable or term in an engine transaction.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_composes_with_transaction', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_transaction_term_uses_empty_answer_rollback_law', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_saga_refuses_transaction_speculation_and_batch_boundaries'),
    ),
    Door(
        owner=Owner.context,
        name='register-prolog',
        kind=Kind.provider,
        signatures=(
            Signature('self, *args: Any, **kwargs: Any', returns='tuple[str, ...]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_register_prolog'),
        docs=(
            'Install a declared Prolog extension.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_builtin_name_is_refused_and_the_builtin_still_works', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declaration_without_an_extension_still_reports_its_names', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declared_det_function_answers_normally'),
    ),
    Door(
        owner=Owner.context,
        name='register-foreign-library',
        kind=Kind.provider,
        signatures=(
            Signature('self, *args: Any, **kwargs: Any', returns='tuple[str, ...]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_register_foreign_library'),
        docs=(
            'Install a compiled SWI foreign library.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_compiled_library_registers_from_python', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_absent_compiled_library_is_refused_here', 'extensions/python/tests/ch14_seeing_your_program/test_trace.py::test_a_foreign_predicate_does_not_break_tracing'),
    ),
    Door(
        owner=Owner.context,
        name='register-library-path',
        kind=Kind.provider,
        signatures=(
            Signature('self, directory: Any, name: str', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_register_library_path'),
        docs=(
            'Register one named Prolog library directory.\n'
        ),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_an_explicitly_shared_library_alias_keeps_all_directories', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_unwinds_every_framework_registration'),
    ),
    Door(
        owner=Owner.context,
        name='unregister-prolog',
        kind=Kind.provider,
        signatures=(
            Signature('self, extension: str', returns='tuple[str, ...]'),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_unregister_prolog'),
        docs=(
            'Release one declared Prolog extension.\n'
        ),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_provider_only_file_registers_no_functions_and_is_accepted', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_extension_unloads_whole', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_unloaded_extension_does_not_leave_its_names_behind'),
    ),
    Door(
        owner=Owner.context,
        name='prolog',
        kind=Kind.introspection,
        signatures=(
            Signature('self', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta._space', 'MeTTa._door_prolog'),
        docs=(
            "Enter SWI-Prolog's interactive toplevel.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_the_interactive_door_reaches_the_owned_runtime',),
    ),
    Door(
        owner=Owner.rows,
        name='insert',
        kind=Kind.write,
        signatures=(
            Signature('self, i: int, item: Iterable[Any]', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_insert'),
        docs=(
            'Read Rows.insert.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_mutations_preserve_invariants',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='append',
        kind=Kind.write,
        signatures=(
            Signature('self, item: Iterable[Any]', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_append'),
        docs=(
            'Read Rows.append.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_mutations_preserve_invariants',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='extend',
        kind=Kind.write,
        signatures=(
            Signature('self, other: Iterable[Iterable[Any]]', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.writesState,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_extend'),
        docs=(
            'Read Rows.extend.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_mutations_preserve_invariants',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='copy',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Rows'),
        ),
        answers=AnswersAs.rows,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_copy'),
        docs=(
            'Read Rows.copy.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_copy_and_pickle_protocols',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='column',
        kind=Kind.query,
        signatures=(
            Signature('self, name: str', returns='Column'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_column'),
        docs=(
            'Project one exact column name.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='group-by',
        kind=Kind.query,
        signatures=(
            Signature('self, column: str', returns='dict[Atom, Rows]'),
        ),
        answers=AnswersAs.mapping,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_group_by'),
        docs=(
            'Group rows by the atom in one exact column.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='first',
        kind=Kind.query,
        signatures=(
            Signature('self, *, default: Any=_MISSING', returns='Row | Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_first'),
        docs=(
            "Return the first row, or the caller's explicit default.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_rows_refuse_an_asserted_scalar[first]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='one',
        kind=Kind.query,
        signatures=(
            Signature('self, *, default: Any=_MISSING', returns='Row | Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_one'),
        docs=(
            'THE row, when the query is asserted to have exactly one answer;\n'
            'none or several raise naming the count, so a lookup that silently\n'
            'picked an arbitrary row cannot hide.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_rows_refuse_an_asserted_scalar[one]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='raise-for-errors',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Self'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_raise_for_errors'),
        docs=(
            'Raise when any cell carries an `(Error ...)` atom; answer self\n'
            'otherwise, so the call chains.\n'
            '\n'
            '    m.match(pattern).raise_for_errors()\n'
            '\n'
            'Query rows are BINDINGS, not evaluation answers, so a stored\n'
            'error record stays data through every Rows method, one() and\n'
            'first() included; this is the explicit bridge for callers who\n'
            'want the raise_for_status reading. One error raises it plainly,\n'
            'several raise one ExceptionGroup carrying each.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='why',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_why'),
        docs=(
            'Explain why this eager query returned no rows.\n'
            '\n'
            "The explanation reads the space's current state. A nonempty result\n"
            'has nothing to explain, and a manually constructed or transformed\n'
            'Rows has no query to inspect, so both uses fail loudly.\n'
            '\n'
            'One of nine observability methods: metta.derivation answers HOW a\n'
            'result was derived, and prepare(...).explain() answers what a\n'
            "query will do before it runs; the guide's observability page maps\n"
            'the family.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[rows:why]'),
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[rows:why]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='explain',
        kind=Kind.query,
        signatures=(
            Signature('self, *, analyze: bool=False, allow_writes: bool=False', returns='Explanation'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_explain'),
        docs=(
            'What the engine did with the query that produced these rows.\n'
            '\n'
            'The same answer `Space.explain` gives, over the match form this result\n'
            'came from: the seam entry, pushdown, source, writes, error mode and the\n'
            'PLAN, `generic-join` with its variable order and columns or\n'
            '`nested-loop` with the conjunct the matcher leads with. Nothing is\n'
            'pulled and nothing is re-matched.\n'
            '\n'
            '`analyze=True` RE-RUNS the query inside `stats()` and adds\n'
            '`(inferences N)`, `(answers N)` and `(cputime S)`; it refuses a query\n'
            'whose operations write unless `allow_writes=True`.\n'
            '\n'
            'The longhand is `m.explain(form)` on the match form itself, and under\n'
            'that `m.run("!(explain <form>)")`.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='build',
        kind=Kind.query,
        signatures=(
            Signature('self, cls: type[BuildT], /', returns='list[BuildT]', type_parameters='BuildT', declarations=('overload',)),
            Signature('self, column: str, cls: type[BuildT]', returns='list[BuildT]', type_parameters='BuildT', declarations=('overload',)),
            Signature('self, column: str | type, cls: type | None=None', returns='list'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_build'),
        docs=(
            'Rebuild constructor atoms through the two-way translator.\n'
            '\n'
            '``build(column, cls)`` projects a named column. ``build(cls)`` is the\n'
            'query reconstruction form when exactly one column holds complete\n'
            'constructor expressions.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[rows:build]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='into',
        kind=Kind.query,
        signatures=(
            Signature('self, cls: type', returns='list'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_into'),
        docs=(
            'Each row as one ``cls``, matched by field name.\n'
            '\n'
            '``match(..., into=cls)`` is sugar for this and says so: the\n'
            'conversion was only ever reachable through that keyword, so a\n'
            "prepared query's solve(), or any other Rows, could not ask for it\n"
            'even though rows_into() never cared where the rows came from\n'
            '[measured 2026-08-31]. build(cls) is the neighbouring method and a\n'
            'different question: it rebuilds ONE column of complete constructor\n'
            'expressions, where this maps every column onto a field.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='to-dicts',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='list[dict[str, Any]]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_to_dicts'),
        docs=(
            'Return one Python-native column-to-value mapping per row.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='table',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='dict[str, list[Any]]'),
        ),
        answers=AnswersAs.mapping,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_table'),
        docs=(
            'The columns as a dict of plain values, the one shape every\n'
            'DataFrame constructor takes: pl.DataFrame(rows.table()),\n'
            'pd.DataFrame(rows.table()). Grounded values unwrap to Python;\n'
            'symbols and structure become their text.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[rows:table]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='arrow',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='ArrowView'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_arrow'),
        docs=(
            'These rows wearing nothing but the Arrow protocol.\n'
            '\n'
            "`Rows` is a sequence, and polars' `DataFrame()` constructor tests for\n"
            'a sequence before it looks for the capsule, so `pl.DataFrame(rows)`\n'
            'reads the atoms row by row instead. `pl.DataFrame(rows.arrow())` is\n'
            'the stream. Consumers that ask for the protocol first, pyarrow,\n'
            'DuckDB, pandas 3 and `pl.scan_arrow_c_stream`, take `rows` itself.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='to',
        kind=Kind.query,
        signatures=(
            Signature('self, library: Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_to'),
        docs=(
            'These rows as a frame of `library`: the general frame door.\n'
            '\n'
            '    rows.to(polars)          # the module itself, never its name\n'
            '    rows.to("polars")        # the escape, for a library not imported here\n'
            '\n'
            'Sugar over `__arrow_c_stream__` where the library reads it, which is\n'
            'typed BY the projection rather than inferred from Python objects, and\n'
            'over the projected columns where it does not; either way the values\n'
            "are the same. The library is the caller's dependency, and its absence\n"
            'raises naming the need. Which libraries are reachable is the `frame`\n'
            "point's rows: a library registers once and every rows object answers\n"
            'it, with no method added here.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[rows:to]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='pipe',
        kind=Kind.query,
        signatures=(
            Signature('self, fn: Callable[..., Any], *args: Any, **kwargs: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_pipe'),
        docs=(
            "fn(self, *args, **kwargs), pandas' chaining shape, so a\n"
            'pipeline reads left to right instead of inside out:\n'
            '\n'
            '    m.match(pattern).pipe(clean).pipe(score, weight=2)\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.rows,
        name='render',
        kind=Kind.query,
        signatures=(
            Signature('self, source: Any, /, **values: Any', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Rows._door_render'),
        docs=(
            'These rows through a template, as text: `metta.render` with `rows` bound.\n'
            '\n'
            '    rows.render("| {rows:table}")\n'
            '    rows.render(t"{len(rows)} answers")   # 3.14\n'
            '\n'
            'The longhand is `metta.render(source, rows=rows)`. The receiver is\n'
            'bound under the name `rows` on both result faces, so one template\n'
            'renders an eager result and a lazy one alike; a template carries its\n'
            'own values, so the binding is what the STRING face resolves `{rows}`\n'
            'against. That binding is always there, so this door always reads its\n'
            'text as fields, where `metta.render("{x}")` with no values leaves the\n'
            'braces alone. Every row is written, where `__rich__` stops at\n'
            '`config.display_rows`: a document is not a terminal.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='columns',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='tuple[str, ...]', declarations=('property',)),
        ),
        answers=AnswersAs.tuple,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_columns'),
        docs=(
            'Caller-variable names available for projection.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        is_property=True,
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='index',
        kind=Kind.query,
        signatures=(
            Signature('self, value: T, start: int=0, stop: int | None=None', returns='int'),
        ),
        answers=AnswersAs.integer,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_index'),
        docs=(
            'Return a row position, with a remedy for column-name collisions.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='column',
        kind=Kind.query,
        signatures=(
            Signature('self, name: str', returns='Answers[Any]'),
        ),
        answers=AnswersAs.answers,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_column'),
        docs=(
            'Project one exact caller-variable column.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='group-by',
        kind=Kind.query,
        signatures=(
            Signature('self, column: str', returns='dict[Atom, Rows]'),
        ),
        answers=AnswersAs.mapping,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_group_by'),
        docs=(
            'Materialize binding rows grouped by one atom-valued column.\n'
        ),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='rows',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Answers[Row]', declarations=('property',)),
        ),
        answers=AnswersAs.answers,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_rows'),
        docs=(
            'The caller-binding row paired with each evaluation answer.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        is_property=True,
        refuses=(
            Refusal(RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_answer_rows_refuses_an_answer_without_bindings'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='into',
        kind=Kind.query,
        signatures=(
            Signature('self, cls: type', returns='list'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_into'),
        docs=(
            'Materialize, then convert through Rows.into.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='build',
        kind=Kind.query,
        signatures=(
            Signature('self, *args: Any', returns='list[Any]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_build'),
        docs=(
            'Materialize, then rebuild one column through Rows.build.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='to-dicts',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='list[dict[str, Any]]'),
        ),
        answers=AnswersAs.sequence,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_to_dicts'),
        docs=(
            'Materialize as plain column-to-value records.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='table',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='dict[str, list[Any]]'),
        ),
        answers=AnswersAs.mapping,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_table'),
        docs=(
            'Materialize as a column mapping.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='to',
        kind=Kind.query,
        signatures=(
            Signature('self, library: Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_to'),
        docs=(
            'Materialize, then build a frame of `library`: Rows.to.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='arrow',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='ArrowView'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_arrow'),
        docs=(
            'These answers wearing nothing but the Arrow protocol.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='pipe',
        kind=Kind.query,
        signatures=(
            Signature('self, fn: Callable[..., Any], *args: Any, **kwargs: Any', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_pipe'),
        docs=(
            'Materialize and pass the eager Rows face to ``fn``.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='raise-for-errors',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Self'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_raise_for_errors'),
        docs=(
            'Raise stored error cells after materializing the row view.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='why',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_why'),
        docs=(
            'Explain an empty query after materializing it.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='explain',
        kind=Kind.query,
        signatures=(
            Signature('self, *, analyze: bool=False, allow_writes: bool=False', returns='Explanation'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_explain'),
        docs=(
            'What the engine did with the query behind this view, pulling nothing.\n'
            '\n'
            '`why()` materializes because an empty answer set is what it explains;\n'
            'this one reads the query the view holds, so a lazy stream stays exactly\n'
            'where it was and an infinite one is explainable at all. Otherwise it is\n'
            '`Rows.explain` and answers the same `Explanation`.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='render',
        kind=Kind.query,
        signatures=(
            Signature('self, source: Any, /, **values: Any', returns='str'),
        ),
        answers=AnswersAs.text,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_render'),
        docs=(
            "These answers through a template, as text: `Rows.render`'s lazy twin.\n"
            '\n'
            'The receiver is bound under the same name, `rows`, so a template\n'
            'written for one face renders the other unchanged. Rendering reads the\n'
            'answers, so an unbounded view is bounded first, the way `to_dicts`\n'
            'and `table` are.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='one',
        kind=Kind.query,
        signatures=(
            Signature('self, *, default: Any=_MISSING', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_one'),
        docs=(
            'Return at most one decoded value, defaulting only on absence.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_answers_refuse_an_asserted_scalar[one]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='first',
        kind=Kind.query,
        signatures=(
            Signature('self, *, default: Any=_MISSING', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_first'),
        docs=(
            "Return the first decoded value, or the caller's explicit default.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(
            Refusal(RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_answers_refuse_an_asserted_scalar[first]'),
        ),
        state=State.any,
    ),
    Door(
        owner=Owner.answers,
        name='close',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.sync,),
        body=Body('metta.results', 'Answers._door_close'),
        docs=(
            'Release the engine cursor this view holds, now rather than later.\n'
            '\n'
            '    with metta.answers(S.fact(V.n)) as rows:\n'
            '        for row in rows:\n'
            '            if enough(row):\n'
            '                break\n'
            '\n'
            'A lazy view owns a cursor and the engine behind it, and a view that is\n'
            'abandoned part-way holds both until the collector runs. `Space` has\n'
            'owned a resource and said so from the start, with `drop()` and the\n'
            '`with` form; this is the same vocabulary for the other type that owns\n'
            'one, which had only a finalizer.\n'
            '\n'
            'The finalizer stays as the backstop, and being only a backstop is the\n'
            'point: a `__del__` runs during interpreter shutdown with module globals\n'
            'already cleared, which is how an abandoned cursor printed\n'
            '"Exception ignored ... catching classes that do not inherit from\n'
            'BaseException" out of a torn-down module [measured 2026-08-31].\n'
            '\n'
            'Closing twice is a no-op, as it is for `drop()`. Answers already pulled\n'
            'stay readable, because they are cached values rather than engine state;\n'
            'only what has NOT been pulled is given up.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=State.any,
    ),
    Door(
        owner=Owner.remote_space,
        name='delivers',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='tuple[str, str] | None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_delivers'),
        docs=(
            'Nothing: the wire carries no event.\n'
            '\n'
            'The wire has four operations, match, enumerate, add and remove, and\n'
            "none of them carries an event, while a remote space's contents change\n"
            'on the server, which is the whole reason it is remote. So a watcher\n'
            'here would hear only the writes this process made and silently miss\n'
            'every other one [measured 2026-08-19: an attached space delivered the\n'
            'one atom this process wrote and nothing for the atom the server\n'
            'added]. Declaring nothing is what refuses the subscription; the\n'
            'sentence below is what a caller reads.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_door_contracts_preserve_capability_refusals',),
        state=State.any,
    ),
    Door(
        owner=Owner.remote_space,
        name='refusal',
        kind=Kind.query,
        signatures=(
            Signature('self, capability: str, /, **_request: Any', returns='str | None'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_refusal'),
        docs=(
            'Read RemoteSpace.refusal.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_door_contracts_preserve_capability_refusals',),
        state=State.any,
    ),
    Door(
        owner=Owner.remote_space,
        name='match',
        kind=Kind.query,
        signatures=(
            Signature('self, pattern: Atom, *, limit: int | None=None', returns='Iterator[Atom]'),
        ),
        answers=AnswersAs.stream,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_match'),
        docs=(
            "Candidates for a pattern; `limit` crosses as the wire's optional\n"
            '`bound` field. Sending it is sound whatever the server does: a\n'
            'server that honors it exactly saves the work, one that ignores it\n'
            'over-answers, and the local engine re-unifies and truncates either\n'
            'way. Whether it is honored is advertised in\n'
            '`server_capabilities()`.\n'
            '\n'
            'One crossing carries the whole answer set unless this space was\n'
            'built with a `batch`, in which case the ask/next/stop lifecycle\n'
            'carries it a chunk at a time and an engine that stops pulling\n'
            'stops the server.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=Remote('match', 'MatchRequest', 'Atoms', 'Every candidate for a pattern in one reply; the eager door, which computes the whole answer set before anything crosses.'),
    ),
    Door(
        owner=Owner.remote_space,
        name='stream',
        kind=Kind.query,
        signatures=(
            Signature('self, pattern: Atom, *, batch: int=_DEFAULT_BATCH, limit: int | None=None, arrow: bool=False', returns='RemoteCursor'),
        ),
        answers=AnswersAs.stream,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_stream'),
        docs=(
            'The lazy method: answers pulled a chunk at a time, so taking two\n'
            "of a large enumeration costs the server two answers' work instead\n"
            "of the whole join's.\n"
            '\n'
            'match() remains eager, matching the in-process split between match()\n'
            'and stream(). Reach for this to take answers\n'
            'until you have seen enough, or when the answer set is larger than\n'
            'one HTTP body.\n'
            '\n'
            "`limit` is the wire's `bound` and carries the same advice it\n"
            'carries on match(): a server that can honor it exactly stops at\n'
            'the count, one that cannot ignores it and over-answers. It is not\n'
            'truncated again here, because a server may answer candidates\n'
            'rather than answers, and cutting an over-approximated stream at\n'
            'the count is the under-approximation the protocol forbids. The\n'
            'first ask crosses when the cursor is built, as the in-process\n'
            'cursor opens its engine when it is built.\n'
            '\n'
            '`arrow=True` asks for Arrow record batches instead of tagged atoms: the\n'
            'server fixes ONE schema for the whole stream when the cursor opens, from\n'
            "what it declares about the pattern's positions, and each chunk crosses\n"
            'as a complete IPC stream at that schema. Such a cursor answers\n'
            '`to_arrow()` and the PyCapsule protocol rather than atoms, because\n'
            'converting a batch back to atoms would go through canonical text and\n'
            'lose what the tagged wire carries exactly.\n'
        ),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_the_lifecycle_answers_exactly_what_the_eager_door_answers',),
        remote=Remote('ask', 'AskRequest', 'Answer', "Open an answer stream and take its first chunk. The reply's cursor is the continuation and doubles as the more-flag."),
    ),
    Door(
        owner=Owner.remote_space,
        name='server-capabilities',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='dict[str, Any]'),
        ),
        answers=AnswersAs.mapping,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_server_capabilities'),
        docs=(
            "The server's own advertisement from GET /health: `capabilities`\n"
            'names the protocol operations it admits, so a client can ask before\n'
            'writing, and `bound` says whether /match honors the bound field\n'
            'exactly. A transport built by connect() knows its URL; a\n'
            'hand-built transport must carry its own `health` callable, or\n'
            'this refuses rather than guessing.\n'
        ),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_server_capabilities_refuses_a_health_less_transport', 'extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_a_gateway_is_a_drop_in_transport', 'extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_health_advertises_the_projection'),
    ),
    Door(
        owner=Owner.remote_space,
        name='atoms',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Iterator[Atom]'),
        ),
        answers=AnswersAs.stream,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_atoms'),
        docs=(
            'Read RemoteSpace.atoms.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=Remote('atoms', 'SpaceRequest', 'Atoms', 'Every atom the named space holds, duplicates included.'),
    ),
    Door(
        owner=Owner.remote_space,
        name='add',
        kind=Kind.write,
        signatures=(
            Signature('self, atom: Atom', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_add'),
        docs=(
            'Store one atom on the serving side.\n'
            '\n'
            'A lost response raises OutcomeUnknown. Its retry() replays the\n'
            'original acknowledgement when the server advertised idempotency;\n'
            'otherwise retry refuses to send and the caller must reconcile with\n'
            'the server. Calling add again starts a NEW logical mutation.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=Remote('add', 'AddRequest', 'Added', 'Store one atom in the named space.'),
    ),
    Door(
        owner=Owner.remote_space,
        name='add-many',
        kind=Kind.write,
        signatures=(
            Signature('self, atoms: list[Atom]', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_add_many'),
        docs=(
            "One request carries the batch, the engine's own bulk-write law on\n"
            'the wire: a batch is a transport optimisation and never a semantic\n'
            'one, and the engine already routes only plain stores through it.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=Remote('add_many', 'AddManyRequest', 'AddedCount', 'Store a batch in one request. A batch is a transport optimisation and never a semantic one.'),
    ),
    Door(
        owner=Owner.remote_space,
        name='remove',
        kind=Kind.write,
        signatures=(
            Signature('self, atom: Atom', returns='bool'),
        ),
        answers=AnswersAs.boolean,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteSpace._door_remove'),
        docs=(
            'Read RemoteSpace.remove.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol',),
        remote=Remote('remove', 'RemoveRequest', 'Removed', 'Remove ONE stored atom unifying with this one. Two copies need two removals.'),
    ),
    Door(
        owner=Owner.remote_cursor,
        name='__next__',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Atom'),
        ),
        answers=AnswersAs.atom,
        effect=EffectClass.oracleIO,
        determinism=Determinism.nondet,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteCursor._door___next__'),
        docs=(
            'Read the next remote answer.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        remote=Remote('next', 'NextRequest', 'Answer', 'The next chunk of an open stream. A short chunk ends it.'),
    ),
    Door(
        owner=Owner.remote_cursor,
        name='to-arrow',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteCursor._door_to_arrow'),
        docs=(
            'The whole remaining stream as one pyarrow Table.\n'
            '\n'
            '    with space.stream(pattern, arrow=True) as answers:\n'
            '        table = answers.to_arrow()\n'
            '\n'
            'Every chunk crosses as its own complete IPC stream at ONE schema, fixed\n'
            'by the server when the cursor opened, so the batches concatenate. The\n'
            "columns are the pattern's variables at the types the served space\n"
            'declares for them, plus `atom`, the canonical text of each instantiated\n'
            'answer, which stays exact where a typed column cannot hold a cell.\n'
            '\n'
            'The longhand is the ask/next/stop lifecycle with\n'
            '`Accept: application/vnd.apache.arrow.stream` and reading each body with\n'
            '`pyarrow.ipc.open_stream`; this is that loop, drained.\n'
        ),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote_arrow.py::test_a_client_cursor_drains_to_one_table',),
    ),
    Door(
        owner=Owner.remote_cursor,
        name='__arrow_c_stream__',
        kind=Kind.query,
        signatures=(
            Signature('self, requested_schema: Any=None', returns='Any'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteCursor._door___arrow_c_stream__'),
        docs=(
            "The drained stream as the Arrow PyCapsule Interface's own object.\n"
            '\n'
            'Sugar over `to_arrow()`, so a consumer that dispatches on the protocol\n'
            'rather than on a type reaches the same batches\n'
            '[source: https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html].\n'
        ),
        evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_remote_arrow.py::test_a_client_cursor_answers_the_capsule_protocol',),
    ),
    Door(
        owner=Owner.remote_cursor,
        name='__iter__',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Iterator[Atom]'),
        ),
        answers=AnswersAs.stream,
        effect=EffectClass.pureStructural,
        determinism=Determinism.nondet,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteCursor._door___iter__'),
        docs=(
            'Iterate the receiver.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        state=State.any,
    ),
    Door(
        owner=Owner.remote_cursor,
        name='close',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteCursor._door_close'),
        docs=(
            "Release the server's cursor; idempotent, and distinct from\n"
            'exhaustion, which released it already.\n'
            '\n'
            'The token survives a failed /stop and the cursor stays open, because\n'
            "a close that discarded it first could never release the server's\n"
            'cursor afterwards: every later close returned at the flag while the\n'
            'server held the engine to its idle deadline [tested\n'
            'test_a_failed_stop_leaves_the_remote_cursor_retryable].\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor', 'extensions/python/tests/ch19_spaces_backed_by_anything/test_remote.py::test_a_failed_stop_leaves_the_remote_cursor_retryable'),
        state=State.any,
        remote=Remote('stop', 'StopRequest', 'Stopped', 'Release a stream early, and say whether there was one to release.'),
    ),
    Door(
        owner=Owner.remote_cursor,
        name='__enter__',
        kind=Kind.query,
        signatures=(
            Signature('self', returns='Self'),
        ),
        answers=AnswersAs.value,
        effect=EffectClass.pureStructural,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteCursor._door___enter__'),
        docs=(
            'Enter the receiver lifetime.\n'
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        state=State.any,
    ),
    Door(
        owner=Owner.remote_cursor,
        name='__exit__',
        kind=Kind.lifecycle,
        signatures=(
            Signature('self, exc_type, exc, tb', returns='None'),
        ),
        answers=AnswersAs.none,
        effect=EffectClass.oracleIO,
        determinism=Determinism.det,
        tiers=(Tier.remote,),
        body=Body('metta.remote', 'RemoteCursor._door___exit__'),
        docs=(
            "Stop the server's cursor without letting the stop displace the\n"
            'diagnosis: a transport that broke mid-stream breaks the /stop too,\n'
            'and the failure a caller needs to read is the first one. Both are\n'
            "raised together, the same shape serve()'s own startup path uses.\n"
        ),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_remote_generated_doors_release_their_cursor',),
        state=State.any,
    ),
    Door(
        owner=Owner.space, name="value", kind=Kind.introspection,
        signatures=(Signature("self", returns="Any"),), answers=AnswersAs.value,
        effect=EffectClass.pureStructural, determinism=Determinism.det, tiers=(Tier.sync,),
        body=Body("metta._atoms_core", "Grounded.value"),
        docs="The inherited payload slot remains unset: a Space is a Handle, and reading value raises AttributeError.",
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=State.any, inherited=True, is_property=True,
    ),
)
