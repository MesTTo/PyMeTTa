"""Purpose: declare Python doors and resolve package accessors from their rows.

Assumes: body references name Python implementations with the declared signature.
Guarantees: DoorOwner collections follow descriptor and MRO shadowing without
  executing descriptors [tested: tests/repository/test_door_marks.py; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Guarantees: the table imports without starting an engine, and every public
  projection is checked against it [tested: test_door_rows_need_no_engine,
  test_every_door_projection_is_current; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
  Nested values are checked against the record fields before registration
  [tested: test_door_registration_refuses_mutable_or_untyped_nested_fields;
  commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]. Public aliases preserve runtime overload lookup [tested:
  test_target_type_overloads_preserve_the_requested_class; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Owns resources: namespace objects borrow their receiver. They acquire no engine
  cursor and retain no registration after it is withdrawn [tested:
  test_a_retained_namespace_observes_replacement_and_withdrawal; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
 Guarded by: the seam lock serializes registry validation and replacement. The
  lookup cache holds immutable snapshots under _CACHE_LOCK [tested:
  test_concurrent_door_claims_have_one_winner; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
  Lookup, retained calls and generated annotations respect the receiving tier
  [tested: test_namespace_tiers_control_lookup_retained_calls_and_annotations;
  commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Decides: a package publishes namespace members or explicit receiver sugars.
  It cannot replace a core door or duplicate an existing sugar point [tested:
  test_door_registration_refuses_collisions_and_duplicate_points; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
"""

from __future__ import annotations

import ast
import importlib
import inspect
import keyword
import math
import threading
import weakref
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from enum import StrEnum
from functools import cache, cached_property
from pathlib import Path
from types import MappingProxyType, UnionType
from typing import Any, get_args, get_origin, get_type_hints

from metta.vocabularies import ArgumentDelivery, Determinism, EffectClass, RefusalKind


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

    @property
    def form(self) -> AnswerForm:
        """What this choice hands back: the door dispatches on the form."""
        return _ANSWER_FORMS[self]


class AnswerForm(StrEnum):
    """What the evaluation door hands back for an answer choice.

    Materialised choices compute every answer before the call returns; a view
    is a lazy source the caller consumes; an aggregate is one fact about the
    answer set; a stream is consumed answer by answer.
    """

    materialised = "materialised"
    view = "view"
    aggregate = "aggregate"
    stream = "stream"


#: The one statement of each choice's form. `EvaluationAnswer.form` reads it,
#: so no door restates which choices share a form.
_ANSWER_FORMS: Mapping[EvaluationAnswer, AnswerForm] = MappingProxyType({
    EvaluationAnswer.all: AnswerForm.materialised,
    EvaluationAnswer.atom: AnswerForm.materialised,
    EvaluationAnswer.one: AnswerForm.materialised,
    EvaluationAnswer.first: AnswerForm.materialised,
    EvaluationAnswer.answers: AnswerForm.view,
    EvaluationAnswer.rows: AnswerForm.view,
    EvaluationAnswer.count: AnswerForm.aggregate,
    EvaluationAnswer.exists: AnswerForm.aggregate,
    EvaluationAnswer.none: AnswerForm.aggregate,
    EvaluationAnswer.stream: AnswerForm.stream,
})
if set(_ANSWER_FORMS) != set(EvaluationAnswer):
    msg = "every evaluation answer must declare its form"
    raise ValueError(msg)


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

    @property
    def family(self) -> Family:
        """Which family of receivers this owner belongs to."""
        return _OWNER_FAMILIES[self]


class Family(StrEnum):
    """The families the owners fall into, which the table's rules read.

    Core owners are the receivers whose doors are Space and MeTTa methods, so
    their Python names are the ones a namespace may not shadow; result owners
    are the answer containers a package may add sugar to; remote owners are
    the client's projections; a namespace is a package's own door set.
    """

    core = "core"
    result = "result"
    remote = "remote"
    namespace = "namespace"


#: The one statement of each owner's family. `Owner.family` reads it.
_OWNER_FAMILIES: Mapping[Owner, Family] = MappingProxyType({
    Owner.space: Family.core,
    Owner.context: Family.core,
    Owner.rows: Family.result,
    Owner.answers: Family.result,
    Owner.remote_space: Family.remote,
    Owner.remote_cursor: Family.remote,
    Owner.namespace: Family.namespace,
})
if set(_OWNER_FAMILIES) != set(Owner):
    msg = "every door owner must declare its family"
    raise ValueError(msg)


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
        match tree.body:
            case [ast.FunctionDef(body=[ast.Expr(value=ast.Constant(value=value))]) as node] if value is Ellipsis:
                return node
        msg = "a door signature must declare one function"
        raise TypeError(msg)

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
        from metta._catalog.types import host_type  # noqa: PLC0415  -- the type projection

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
        from metta._catalog.types import host_delivery  # noqa: PLC0415 -- shared argument contract

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


class EvaluationInput(StrEnum):
    """The representation supplied to the binding's evaluation entry."""

    wire = "wire"
    term = "term"


class EvaluationCollection(StrEnum):
    """How one producer delivers its answers across the binding."""

    one = "one"
    all = "all"
    cursor = "cursor"
    count = "count"  # type: ignore[assignment]  # the vocabulary word deliberately shadows str.count
    retained = "retained"
    status = "status"


@dataclass(frozen=True, slots=True)
class EvaluationOptions:
    """The evaluation record grammar; binding code and documents are projections."""

    form: EvaluationInput = field(default=EvaluationInput.wire, metadata={"means": "Wire/text target or an already decoded term."})
    using: tuple[tuple[str, str], ...] = field(default=(), metadata={"means": "Named substitutions applied to the decoded term."})
    answers: EvaluationCollection = field(default=EvaluationCollection.all, metadata={"means": "One solution, eager bag, cursor, count, retained count, or status rows."})
    fuel: bool = field(default=True, metadata={"means": "Reuse or open the engine fuel scope."})
    inferences: int = field(default=-1, metadata={"means": "Cumulative engine-step quota; negative means unbounded.", "bound": True})
    seconds: float = field(default=-1.0, metadata={"means": "Engine time quota in seconds; negative means unbounded.", "bound": True})
    under: tuple[str, int, str] | None = field(default=None, metadata={"means": "Evaluation algebra, demand limit and direction, or no override."})
    policy: tuple[str, bool] | None = field(default=None, metadata={"means": "Execution mode and capture policy retained inside a cursor."})
    repeatable: bool = field(default=False, metadata={"means": "Refuse a separate count when the goal is not effect-safe."})
    columns: tuple[str, ...] = field(default=(), metadata={"means": "Caller variable names projected beside each cursor answer."})
    accounting: bool = field(default=False, metadata={"means": "Return the work measured inside this evaluation."})
    batch: bool = field(default=False, metadata={"means": "Return one result group per target, in input order."})
    unmatched: bool = field(default=True, metadata={"means": "Preserve an unreduced original after an empty eager bag."})


@dataclass(frozen=True, slots=True)
class Binding:
    """The engine door and the wire used to cross it."""

    door: str
    wire: Wire
    evaluation: EvaluationOptions | None = None


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


def door[F: Callable[..., Any]](kind: Kind, **metadata: Any) -> Callable[[F], F]:
    """Mark an unchanged function with its immutable operation contract.

    Pluggy's marker stores metadata and returns the same function. That keeps
    the signature, overload registry, descriptor binding and frame count intact.
    https://github.com/pytest-dev/pluggy/blob/1.6.0/src/pluggy/_hooks.py
    """
    derived = {"owner", "name", "signatures", "body", "docs"}
    unknown = metadata.keys() - ({field.name for field in fields(Door)} - derived - {"kind"})
    if unknown:
        msg = f"door metadata contains derived or unknown fields: {sorted(unknown)}"
        raise TypeError(msg)
    contract = MappingProxyType({"kind": kind} | metadata)

    def decorate(function: F) -> F:
        if hasattr(function, "__metta_door__"):
            msg = f"{getattr(function, '__qualname__', type(function).__qualname__)} already has a door mark"
            raise ValueError(msg)
        setattr(function, "__metta_door__", contract)  # noqa: B010 -- the generic callable type carries no metadata attributes
        return function

    return decorate


class DoorOwner:
    """Collect marked methods at the receiver's class construction boundary."""

    __slots__ = ()
    __door_members__: Mapping[str, Callable[..., Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect inherited marks when the receiver class becomes available."""
        super().__init_subclass__(**kwargs)
        visible = {name: value for base in reversed(cls.__mro__) for name, value in vars(base).items()}
        members = {}
        for name, value in visible.items():
            function = value.fget if isinstance(value, property) else (
                value.__func__ if isinstance(value, (classmethod, staticmethod)) else value
            )
            if callable(function) and hasattr(function, "__metta_door__"):
                inspect.get_annotations(function, eval_str=False)
                members[name] = function
        cls.__door_members__ = MappingProxyType(members)


def core_rows() -> tuple[Door, ...]:
    """Discover core contracts from marked source, without importing bodies."""
    from metta.doors._scan import core  # noqa: PLC0415 -- the schema precedes its reader

    return core()


def declarations(module: str) -> tuple[Door, ...]:
    """Read a loaded provider's marked bodies without importing their targets.

    A provider registers these rows with ``seam.door.register``. The runtime
    and generator use the same AST reader, including class-owned methods.
    """
    import sys  # noqa: PLC0415 -- the caller is an already loaded provider

    from metta.doors._scan import scan  # noqa: PLC0415 -- the schema precedes its reader

    filename = vars(sys.modules[module]).get("__file__")
    if filename is None:
        msg = f"door provider {module!r} has no readable Python source"
        raise ValueError(msg)
    return scan(Path(filename), module)


@cache
def _record_fields(record_type: type) -> tuple[tuple[str, Any], ...]:
    """Read the declared grammar once, including postponed nested types."""
    if not is_dataclass(record_type):
        msg = f"door record {record_type!r} is not a dataclass"
        raise TypeError(msg)
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
        if row.body is row.sugar_of is None:
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
    core_names = {row.python for row in result if row.owner.family is Family.core}
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
    from metta import seam  # noqa: PLC0415  -- the registry imports the row grammar lazily

    held = seam.door.rows() if discover else seam._rows_of(seam.door, discover_first=False)
    global _CACHE_ROWS, _CACHE  # noqa: PLW0603  # pylint: disable=global-statement # replace one process-wide registry snapshot under _CACHE_LOCK
    with _CACHE_LOCK:
        if held != _CACHE_ROWS or _CACHE is None:
            rows = validate((*core_rows(), *(door for row in held for door in row.doors)))
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
            door.owner.family is not Family.result or door.sugar_of is None
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
    validate((*core_rows(), *(door for held in (*standing, row) for door in held.doors)))


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
    if row.sugar_of is not None:
        overlap = set(kwargs).intersection(name for name, _ in row.sugar_of.fixed)
        if overlap:
            msg = f"door {row.key!r} fixes {', '.join(sorted(overlap))}"
            raise TypeError(msg)
    if row.body is None:
        if row.sugar_of is None:
            msg = f"door {row.key!r} has no implementation"
            raise TypeError(msg)
        base = table()[row.sugar_of.base]
        row.signature.host_signature("metta", receiver=True).bind(*args, **kwargs)
        return _invoke(base, receiver, args, kwargs | dict(row.sugar_of.fixed))
    function = row.body.resolve()
    _check_body(function, row)
    if row.body.receiver is Receiver.none:
        return function(*args, **kwargs)
    if row.body.receiver is Receiver.space:
        from metta import seam  # noqa: PLC0415  -- public receiver normalization

        receiver = seam.space_of(receiver)
    return function(receiver, *args, **kwargs)


def _check_body(function: Any, row: Door) -> None:
    """Check an installed provider's call shape before its first invocation."""
    assert row.body is not None  # nosec B101 # registration already validated this internal invariant
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
    from metta.doors._catalog import atoms  # noqa: PLC0415  -- generated catalog projection

    runtime.must("load_files(Path, [if(not_loaded)])", Path=str(Path(__file__).resolve().parents[1] / "_binding" / "door_catalog.pl"))
    result = runtime.must(
        "metta_py_publish_doors(Wires, Count)",
        Wires=[atom.to_wire() for atom in atoms(tuple(table().values()))],
    )
    return int(result["Count"])
