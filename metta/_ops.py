"""Purpose: register the Python operation callables the engine dispatches into.

shim.pl calls dispatch/dispatch_many for encoded operations and dispatch_raw
variants for raw ones; the registry maps a MeTTa function name to the Python
callable behind it, decoding arguments to atoms-or-values and encoding results
back. Importable as petta_ops, the name the Prolog side uses.
Guarantees:
  - operation records distinguish MeTTa names from declaration-space names
    [tested: test_canonical_context_types_replace_public_newtypes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - protocol type registrations can be removed by exact identity [tested
    test_protocol_and_reflector_registrations_can_be_removed]
  - a release that FAILS reaches the caller. Left to the deallocator,
    CPython prints "Exception ignored while closing generator" and the call
    answers normally [measured 2026-08-19: an OSError raised while releasing
    reached stderr and nobody else] [tested
    test_a_nondeterministic_ops_generator_releases_what_it_holds]
  - resolved parameter and return annotations select conversion in both
    directions, so an annotation cannot describe one image while carrying
    another [tested: test_a_typed_dict_annotation_agrees_with_its_value;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - type_names removes every __petta_wire_value__ carrier before reading the
    MRO, so transport classes never become MeTTa types [tested:
    test_a_python_tuple_answers_the_same_through_both_doors;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - raw operation results pass only exact primitives bare; every other
    Python value uses the identity-interned object carrier [tested:
    test_operation_results_preserve_python_object_identity;
    commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
  - Atom annotations select syntax-level delivery, while an `(arguments ...
    atoms)` seam declaration selects Atom wrappers after ordinary evaluation
    without a pass_atoms boolean [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - exact tuple and dict yields from encoded generators cross as candidate
    parameter bindings, with width and names checked before the engine unifies
    them [tested:
    test_relational_tuple_candidates_unify_in_all_directions_without_changing_multiplicity,
    test_sparse_relational_dict_candidates_bind_parameter_names;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - each operation record carries its canonical EffectClass and exposes
    ``pure`` only as the structural-rank projection [tested:
    test_every_effect_rank_registers_and_reflects; commit=WORKTREE]
  - an active saga capture records one ``(did op args result)`` atom for
    every successful writesState-or-stronger operation answer, including
    relational, inverse, and raw dispatch [tested:
    test_every_effectful_dispatch_shape_leaves_one_committed_receipt;
    commit=WORKTREE]
Owns:
  - the answer stream a nondeterministic operation returns. It is one-shot
    and can hold a file, a cursor or a lock between yields, so the code that
    consumed it closes it before returning rather than leaving that to the
    collector [tested
    test_a_nondeterministic_ops_generator_releases_what_it_holds]
Guarded by:
  - _PROTOCOL_TYPES_LOCK protects protocol type registrations [tested
    test_protocol_and_reflector_registrations_can_be_removed]
Decides:
  - closing that stream is this module's job rather than the consumer's,
    because a Prolog cut, a resource guard and an exception all abandon it
    from outside Python and only the code holding it can say when it is done
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import inspect
import threading
import types
import typing
from collections.abc import Callable, Iterable
from contextlib import closing
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from ._api_types import _OperationName, _SpaceId
from ._atoms_core import _is_primitive, _unbox_wire_value, boxed
from ._convert_build import build
from ._convert_project import explicit_projection, project
from .answer import Answer
from .atoms import (
    Atom,
    Box,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _atom_from_wire,
    _decode,
    _encode,
)
from .errors import NotReducible, PettaError, is_transport_failure
from .vocabularies import EffectClass

__all__ = [
    "OPERATION_REGISTRATION",
    "REGISTRY",
    "Operation",
    "dispatch",
    "dispatch_inverse",
    "dispatch_inverse_raw",
    "dispatch_many",
    "dispatch_raw",
    "dispatch_raw_many",
    "live_registration",
]

# The wire form the shim treats as failure rather than a value: the operation
# looked at its arguments and answered nothing.
_DECLINED = ["x", "declined"]


@dataclass
class _ReceiptCapture:
    """The pending ordinary-data receipts owned by one saga step."""

    receipts: list[_CapturedReceipt]
    effectful_names: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _CapturedReceipt:
    """One provisional receipt and whether the engine can roll its effect back."""

    atom: Expression
    enlisted: bool


_RECEIPT_CAPTURE: ContextVar[_ReceiptCapture | None] = ContextVar(
    "petta_receipt_capture",
    default=None,
)


def _begin_receipt_capture(
    receipts: list[_CapturedReceipt],
) -> Token[_ReceiptCapture | None]:
    """Route this context's effectful operation answers into ``receipts``."""
    return _RECEIPT_CAPTURE.set(_ReceiptCapture(receipts))


def _end_receipt_capture(token: Token[_ReceiptCapture | None]) -> None:
    """Restore the capture active before ``_begin_receipt_capture``."""
    _RECEIPT_CAPTURE.reset(token)


def _suspend_receipt_capture() -> Token[_ReceiptCapture | None]:
    """Keep compensation execution out of an enclosing saga's journal."""
    return _RECEIPT_CAPTURE.set(None)


def _select_receipt_operations(names: list[str]) -> None:
    """Freeze the engine's effectful operation plan for this saga step."""
    capture = _RECEIPT_CAPTURE.get()
    if capture is None:
        msg = "the saga receipt plan arrived outside its active capture scope"
        raise RuntimeError(msg)
    capture.effectful_names = frozenset(names)


def _capture_atom_receipt(op: Operation, arguments: list[Atom], result: Atom) -> None:
    """Append one provisional receipt for engine-side effect filtering."""
    capture = _RECEIPT_CAPTURE.get()
    if capture is None or str(op.name) not in capture.effectful_names:
        return
    capture.receipts.append(
        _CapturedReceipt(
            Expression(
                [
                    Symbol("did"),
                    Symbol(str(op.name)),
                    Expression(arguments),
                    result,
                ]
            ),
            enlisted=False,
        )
    )


def _substitute_receipt_atom(atom: Atom, theta: dict[str, Atom]) -> Atom:
    """Apply one explicit Answer's bindings to receipt arguments."""
    if isinstance(atom, Variable):
        return theta.get(atom.name, atom)
    if isinstance(atom, Expression):
        return Expression(
            [_substitute_receipt_atom(child, theta) for child in atom.children]
        )
    return atom


def _capture_encoded_receipt(
    op: Operation,
    argument_wires: list,
    result_wire: list,
) -> None:
    """Turn one successful encoded dispatch answer into ordinary atom data."""
    if _RECEIPT_CAPTURE.get() is None:
        return
    arguments = [_atom_from_wire(wire) for wire in argument_wires]
    if result_wire and result_wire[0] == "a":
        theta = {
            str(name): _atom_from_wire(wire)
            for name, wire in result_wire[1]
        }
        arguments = [_substitute_receipt_atom(atom, theta) for atom in arguments]
        result = (
            Expression()
            if len(result_wire) == 4
            else _atom_from_wire(result_wire[4])
        )
    else:
        result = _atom_from_wire(result_wire)
    _capture_atom_receipt(op, arguments, result)


def _capture_raw_receipt(op: Operation, arguments: list[Any], result: Any) -> None:
    """Preserve raw transport identity in one provisional receipt."""
    if _RECEIPT_CAPTURE.get() is None:
        return
    _capture_atom_receipt(
        op,
        [_raw_receipt_atom(argument) for argument in arguments],
        _raw_receipt_atom(result),
    )


def _raw_receipt_atom(value: Any) -> Atom:
    """Project primitives and box every opaque raw value by identity."""
    return _encode(value) if _is_primitive(value) else _encode(boxed(value))


@dataclass(frozen=True)
class Operation:
    """One registered MeTTa function backed by Python."""

    name: _OperationName
    fn: Callable[..., Any]
    kind: str  # det | many | raw_det | raw_many
    arity: int
    effect: EffectClass
    pass_atoms: bool = False  # derived from (arguments name atoms)
    space: _SpaceId | None = None  # where the type declarations were added
    declarations: tuple = ()  # the (: ...) atoms, for unregistration
    catalog: tuple = ()  # policy atoms owned in &petta
    arities: tuple = ()  # every registered arity, for reflection facts
    inverse: Callable[..., Any] | None = None  # the backwards direction
    parameter_names: tuple[str, ...] = ()
    parameter_annotations: tuple[Any, ...] = ()
    return_annotation: Any = Any

    @property
    def pure(self) -> bool:
        """The legacy projection: true is rank 0, false is any rank 1-4.

        The projection deliberately has no inverse: ``False`` cannot recover
        which observable capability the operation declared.
        """
        return self.effect is EffectClass.pureStructural


REGISTRY: dict[str, Operation] = {}

# The attribute a registration wrapper carries so a reader resolves the Python
# object rather than guessing from its source spelling. Private metadata on
# the wrapper: it never enters the operation's call path.
OPERATION_REGISTRATION = "__metta_operation_registration__"


def live_registration(fn: Any) -> Operation | None:
    """The registration a callable carries, while the registry still owns it."""
    operation = getattr(fn, OPERATION_REGISTRATION, None)
    if isinstance(operation, Operation) and REGISTRY.get(operation.name) is operation:
        return operation
    return None


def _decode_arg(wire: Any, pass_atoms: bool, annotation: Any = Any) -> Any:  # noqa: FBT001  -- the boolean is established API data and positional compatibility is part of the call shape
    atom = _atom_from_wire(wire)
    if pass_atoms or _receives_atom(annotation):
        return atom
    if annotation is not Any and annotation is not inspect.Parameter.empty:
        return build(atom, annotation)
    # Grounded values unwrap to Python; symbols, variables and expressions
    # stay atoms, which is the structure an operation may want to inspect.
    return _decode(atom) if isinstance(atom, Grounded) else atom


def _receives_atom(annotation: Any) -> bool:
    """Whether an annotation asks for syntax rather than an evaluated value."""
    while typing.get_origin(annotation) is typing.Annotated:
        annotation = typing.get_args(annotation)[0]
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        members = [member for member in typing.get_args(annotation) if member is not type(None)]
        return bool(members) and all(_receives_atom(member) for member in members)
    return isinstance(annotation, type) and issubclass(annotation, Atom)


def _encode_result(value: Any, annotation: Any = Any) -> list:
    if isinstance(value, Answer):
        # The explicit answer: bindings for the call's variables, crossing
        # as the seam's own wire form beside the plain atoms.
        return value.to_wire()
    if value is None:
        # None is not a MeTTa value. A deterministic operation returning it
        # answers nothing, the semidet reading; return Expression() for unit.
        return _DECLINED
    if isinstance(value, Atom):
        return value.to_wire()
    if annotation is not Any and annotation is not inspect.Parameter.empty:
        return project(value, annotation).atom.to_wire()
    # An author's opt-in projects: an explicit register_type or a __metta__
    # method makes the value cross as its declared image, so an operation
    # returning a registered type answers (Pt 3 4) rather than an opaque
    # handle. Everything undeclared keeps today's behaviour exactly, the
    # opaque floor; the memoized defaults project() creates never fire here.
    projected = explicit_projection(value)
    if projected is not None:
        return projected.to_wire()
    return _encode(value).to_wire()


def dispatch(name: str, tagged_args: list) -> list:
    """One answer, encoded; the declined sentinel for no answer."""
    op = REGISTRY[name]
    annotations = (*op.parameter_annotations, *(Any for _ in tagged_args))
    args = [
        _decode_arg(argument, op.pass_atoms, annotation)
        for argument, annotation in zip(tagged_args, annotations, strict=False)
    ]
    try:
        value = op.fn(*args)
        encoded = _encode_result(value, op.return_annotation)
        if encoded != _DECLINED:
            _capture_encoded_receipt(
                op,
                tagged_args,
                encoded,
            )
    except NotReducible:
        return _DECLINED
    else:
        return encoded


def dispatch_inverse(name: str, tagged_result: Any):
    """Run an operation BACKWARDS: one result in, argument tuples out.

    The inverse is a relation, not a function, so this always enumerates: a
    plain callable's single answer is yielded once and a generator's answers
    are yielded in turn. Returning None or raising NotReducible means the result
    has no preimage, which is failure rather than an error, exactly as it is
    forwards.

    Each answer is a sequence of the operation's arguments, encoded the same
    way a forward answer is. A one-argument operation may return the bare
    value rather than a one-tuple, because writing `(x,)` for it reads as a
    typo and forgetting the comma would otherwise iterate a string.
    """
    op = REGISTRY[name]
    for arguments in _preimages(
        name,
        _decode_arg(tagged_result, op.pass_atoms, op.return_annotation),
    ):
        annotations = (*op.parameter_annotations, *(Any for _ in arguments))
        encoded_arguments = [
            _encode_result(argument, annotation)
            for argument, annotation in zip(arguments, annotations, strict=False)
        ]
        _capture_encoded_receipt(op, encoded_arguments, tagged_result)
        yield encoded_arguments


def dispatch_inverse_raw(name: str, result: Any):
    """The same relation for a raw operation, with janus's own conversions.

    An operation registered raw takes those conversions forwards, so its
    inverse takes them backwards. Sending the inverse through the wire
    encoding instead gave one function pair two value conventions: `str` for a
    symbol going out and `Symbol` coming back.
    """
    op = REGISTRY[name]
    unboxed_result = _unbox(result)
    for arguments in _preimages(name, unboxed_result):
        _capture_raw_receipt(op, list(arguments), unboxed_result)
        yield [_rebox(argument) for argument in arguments]


def _preimages(name: str, result: Any):
    """Every preimage the inverse gives for one result, as argument sequences.

    A one-argument operation may answer the bare value rather than a one-tuple,
    because writing `(x,)` for it reads as a typo and forgetting the comma
    would otherwise iterate a string.
    """
    op = REGISTRY[name]
    if op.inverse is None:
        # Only an operation whose clause carries the mode test can reach here,
        # so the two registries disagreeing is a bug rather than a user error.
        msg = f"{name} was called backwards and declares no inverse"
        raise PettaError(msg)
    try:
        answers = op.inverse(result)
    except NotReducible:
        return
    if answers is None:
        return
    # A plain callable answers ONE preimage, so it is wrapped rather than
    # iterated and there is nothing to close; a generator inverse is a
    # stream this owns.
    stream = answers if inspect.isgeneratorfunction(op.inverse) else [answers]
    try:
        for answer in stream:
            if answer is None:
                continue
            yield answer if isinstance(answer, (tuple, list)) else [answer]
    finally:
        close = getattr(stream, "close", None)
        if close is not None:
            close()


def dispatch_many(name: str, tagged_args: list, mode: str = "abort"):
    """A generator of encoded answers; each yield is one MeTTa answer.

    A declared error mode is enforced here, where the exceptions are
    native: keep reduces the failed call to its (Error <call> <reason>) atom
    as the final answer and empty ends the stream. Abort and transport errors
    cross in a reserved terminal frame because raising during ``py_iter``
    would discard the original exception. Control signals remain outside the
    handler and pass through untouched.
    """
    op = REGISTRY[name]
    annotations = (*op.parameter_annotations, *(Any for _ in tagged_args))
    args = [
        _decode_arg(argument, op.pass_atoms, annotation)
        for argument, annotation in zip(tagged_args, annotations, strict=False)
    ]
    relation_schema = _relation_schema(op, len(tagged_args))
    # closing/1 rather than a bare loop: the stream is one-shot and this is
    # what consumed it. A "many" operation is a generator function by
    # construction (ops._operation_kind), so close() is always there.
    try:
        with closing(op.fn(*args)) as answers:
            for value in answers:
                if value is None:
                    continue
                relation = _encode_relation_candidate(op, value, relation_schema)
                if relation is not None:
                    receipt_arguments = list(tagged_args)
                    for index, candidate in relation[1]:
                        receipt_arguments[index] = candidate
                    _capture_encoded_receipt(
                        op,
                        receipt_arguments,
                        Expression().to_wire(),
                    )
                    yield relation
                    continue
                encoded = _encode_result(value, op.return_annotation)
                _capture_encoded_receipt(
                    op,
                    tagged_args,
                    encoded,
                )
                yield encoded
    # KeyboardInterrupt and SystemExit are BaseException, outside this
    # handler by construction, so control signals pass through untouched.
    except Exception as error:
        if _failed_during_generator_close(error):
            raise
        must_abort = (
            mode == "abort"
            or isinstance(error, _RelationContractError)
            or is_transport_failure(error)
        )
        if must_abort:
            yield _stream_error(error)
        elif mode == "keep":
            call = Expression(
                [
                    Symbol(name),
                    *(
                        _encode(_decode_arg(a, True, Atom))  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
                        for a in tagged_args
                    ),
                ]
            )
            reason = f"{type(error).__name__}: {error}"
            yield Expression([Symbol("Error"), call, Grounded(reason)]).to_wire()


class _RelationContractError(PettaError):
    """A malformed candidate row, which error modes must never reinterpret."""


@dataclass(frozen=True)
class _RelationSchema:
    """One call arity's positional names, types, lookup, and ambiguities."""

    names: tuple[str, ...]
    annotations: tuple[Any, ...]
    positions: dict[str, int]
    repeated: frozenset[str]


def _relation_schema(op: Operation, arity: int) -> _RelationSchema:
    """Index one call signature once, outside its candidate stream."""
    names = op.parameter_names[:arity]
    annotations = (
        *op.parameter_annotations,
        *(Any for _ in range(max(0, arity - len(op.parameter_annotations)))),
    )
    positions: dict[str, int] = {}
    repeated: set[str] = set()
    for index, name in enumerate(names):
        if name in positions:
            repeated.add(name)
        else:
            positions[name] = index
    return _RelationSchema(
        names,
        annotations,
        positions,
        frozenset(repeated),
    )


def _failed_during_generator_close(error: Exception) -> bool:
    """Tell a release failure from an ordinary mid-iteration failure.

    ``contextlib.closing`` calls the owned generator's ``close`` while handling
    ``GeneratorExit`` from this stream. A release error then carries that
    control signal as its direct context and must propagate rather than yield,
    because yielding while closing raises ``RuntimeError: generator ignored
    GeneratorExit`` and hides the resource failure.
    """
    return isinstance(error.__context__, GeneratorExit)


def _stream_error(error: Exception) -> list:
    """Carry a terminal generator failure as data until Prolog can throw it.

    Raising while Janus is pulling ``py_iter/2`` loses the Python exception
    behind a bare ``SystemError``. The shim recognizes this reserved frame and
    hands the live object to ``petta_py_failure/2``, the same structured error
    boundary deterministic operations use.
    """
    return ["x", "raise", type(error).__name__, error]


def _encode_relation_candidate(
    op: Operation,
    value: Any,
    schema: _RelationSchema,
) -> list | None:
    """Encode one positional or sparse relation row by call-argument index."""
    if type(value) is tuple:
        if len(value) != len(schema.names):
            msg = (
                f"relational operation {op.name} yielded a tuple of width "
                f"{len(value)}, but this call takes {len(schema.names)} arguments"
            )
            raise _RelationContractError(msg)
        fields: Iterable[tuple[int, Any]] = enumerate(value)
    elif type(value) is dict:
        invalid = [
            key
            for key in value
            if not isinstance(key, str) or key not in schema.positions
        ]
        if invalid:
            expected = ", ".join(schema.names) or "no parameters"
            msg = (
                f"relational operation {op.name} yielded unknown parameter "
                f"key(s) {invalid!r}; this call accepts {expected}"
            )
            raise _RelationContractError(msg)
        ambiguous = [name for name in value if name in schema.repeated]
        if ambiguous:
            msg = (
                f"relational operation {op.name} cannot use sparse key(s) "
                f"{ambiguous!r} for repeated variadic parameters; yield a "
                f"positional tuple of width {len(schema.names)}"
            )
            raise _RelationContractError(msg)
        fields = (
            (index, value[name])
            for index, name in enumerate(schema.names)
            if name in value
        )
    else:
        return None
    return [
        "r",
        [
            _encode_relation_field(
                op,
                index,
                schema.names[index],
                candidate,
                schema.annotations[index],
            )
            for index, candidate in fields
        ],
    ]


def _encode_relation_field(
    op: Operation,
    index: int,
    name: str,
    candidate: Any,
    annotation: Any,
) -> list:
    """Encode one candidate atom, rejecting whole-answer boundary values."""
    if candidate is None:
        msg = (
            f"relational operation {op.name} yielded None for parameter "
            f"{name!r}; omit a sparse dict key to leave that position "
            "unconstrained"
        )
        raise _RelationContractError(msg)
    if isinstance(candidate, Answer):
        msg = (
            f"relational operation {op.name} yielded Answer for parameter "
            f"{name!r}; wrap the whole tuple or dict result in Answer(value=...) "
            "instead of placing Answer inside a relation row"
        )
        raise _RelationContractError(msg)
    return [index, _encode_result(candidate, annotation)]


def _unbox(value: Any) -> Any:
    return _unbox_wire_value(value)


def _rebox(value: Any) -> Any:
    """Whatever janus would rewrite goes back boxed; primitives pass raw.

    A raw result reaching Prolog goes through janus conversion exactly as an
    argument does, so an ndarray returned bare would explode into a list of
    element objects; the box is the envelope that keeps it one value.
    """
    if value is None or _is_primitive(value) or isinstance(value, Box):
        return value
    return boxed(value)


def dispatch_raw(name: str, args: list) -> Any:
    """Raw call: janus's own conversions in, the bare return value out.

    For operations over object references and numbers, where the encoding
    would cost more than the call. Symbols arrive as str and booleans as
    janus values here; use an encoded operation when that fidelity matters.
    Boxed arguments unbox on the way in and opaque results box on the way
    out, so an operation body only ever sees real objects. None crosses as
    janus @none, which the shim reads as no answer; NotReducible maps onto it.
    """
    op = REGISTRY[name]
    unboxed_args = [_unbox(argument) for argument in args]
    try:
        value = _refuse_raw_answer(op.fn(*unboxed_args))
        if value is not None:
            _capture_raw_receipt(op, unboxed_args, value)
        return _rebox(value)
    except NotReducible:
        return None


def dispatch_raw_many(name: str, args: list):
    op = REGISTRY[name]
    unboxed_args = [_unbox(argument) for argument in args]
    try:
        with closing(op.fn(*unboxed_args)) as answers:
            for answer in answers:
                _refuse_raw_relation_candidate(answer)
                value = _refuse_raw_answer(answer)
                if value is not None:
                    _capture_raw_receipt(op, unboxed_args, value)
                yield _rebox(value)
    except Exception as error:
        if _failed_during_generator_close(error):
            raise
        yield _stream_error(error)


def _refuse_raw_relation_candidate(value: Any) -> None:
    """Reject relation rows before Janus can mistake them for raw values."""
    if type(value) not in (tuple, dict):
        return
    msg = (
        "a raw generator yielded a relational tuple or dict; raw arguments "
        "cannot carry unbound variables, so register the operation with "
        'transport="encoded"'
    )
    raise PettaError(msg)


def _refuse_raw_answer(value: Any) -> Any:
    """A raw operation is the opaque fast path and its results skip the wire,
    so an Answer here would cross as an inert handle and its bindings would
    silently never bind. Refusing is the honest reading; bindings need the
    wire, so the operation selects transport="encoded".
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(value, Answer):
        msg = (
            "a raw operation answered metta.Answer; raw results skip the "
            "wire the bindings cross on, so register the operation with "
            'transport="encoded" to answer bindings'
        )
        raise PettaError(
            msg
        )
    return value


def type_names(obj: Any) -> list[str]:
    """Every type name an object carries, for the engine's typing bridge:
    its classes in resolution order short of object, then every satisfied
    protocol. Computed on the boxed value's contents, and returned as text,
    which janus cannot damage.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    value = _unbox(obj)
    names = [c.__name__ for c in type(value).__mro__ if c.__name__ != "object"]
    names.extend(extra_types(value))
    return names


# -------------------------------------------------------------- extra typing
#
# (predicate, type name) pairs; an object satisfying a predicate carries the
# name as an additional type candidate. Consulted by the engine through the
# shim's seam:grounded_extra_type/2 bridge.

PROTOCOL_TYPES: list[tuple[Any, str]] = []
_PROTOCOL_TYPES_LOCK = threading.RLock()


def register_protocol_type(predicate: Callable[[Any], bool], name: str) -> None:
    """Register one predicate and public type-name pair."""
    with _PROTOCOL_TYPES_LOCK:
        PROTOCOL_TYPES.append((predicate, name))


def unregister_protocol_type(predicate: Callable[[Any], bool], name: str) -> None:
    """Remove the latest exact predicate and type-name registration."""
    with _PROTOCOL_TYPES_LOCK:
        for index in range(len(PROTOCOL_TYPES) - 1, -1, -1):
            registered_predicate, registered_name = PROTOCOL_TYPES[index]
            if registered_predicate is predicate and registered_name == name:
                PROTOCOL_TYPES.pop(index)
                return
    msg = f"no object type protocol {name!r} uses that predicate"
    raise KeyError(msg)


def extra_types(obj) -> list[str]:
    names = []
    with _PROTOCOL_TYPES_LOCK:
        registrations = tuple(PROTOCOL_TYPES)
    for predicate, name in registrations:
        try:
            if predicate(obj):
                names.append(name)
        except Exception as exc:
            # A broken probe is the registrant's bug: surface it with the
            # protocol's name attached, never as a type quietly missing.
            msg = f"the type predicate for protocol {name!r} raised on {type(obj).__name__}: {exc}"
            raise RuntimeError(
                msg
            ) from exc
    return names
