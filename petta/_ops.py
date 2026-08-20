"""Purpose: the operation registry the engine dispatches into. shim.pl calls
dispatch/dispatch_many for encoded operations and dispatch_raw variants for
raw ones; the registry maps a MeTTa function name to the Python callable
behind it, decoding arguments to atoms-or-values and encoding results back.
Importable as petta_ops, the name the Prolog side uses.
Guarantees:
  - operation records distinguish MeTTa names from declaration-space names
    [tested test_public_context_types_are_distinct]
  - protocol type registrations can be removed by exact identity [tested
    test_protocol_and_reflector_registrations_can_be_removed]
  - a release that FAILS reaches the caller. Left to the deallocator,
    CPython prints "Exception ignored while closing generator" and the call
    answers normally [measured 2026-08-19: an OSError raised while releasing
    reached stderr and nobody else] [tested
    test_a_nondeterministic_ops_generator_releases_what_it_holds]
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
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import inspect
import threading
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from typing import Any

from ._api_types import MettaName, SpaceName
from ._convert_project import explicit_projection
from .answer import Answer
from .atoms import Atom, Box, Expr, Gnd, Sym, atom_from_wire, decode, encode
from .errors import Decline, PettaError, is_transport_failure

__all__ = [
    "REGISTRY",
    "Operation",
    "dispatch",
    "dispatch_inverse",
    "dispatch_inverse_raw",
    "dispatch_many",
    "dispatch_raw",
    "dispatch_raw_many",
]

# The wire form the shim treats as failure rather than a value: the operation
# looked at its arguments and answered nothing.
_DECLINED = ["x", "declined"]


@dataclass(frozen=True)
class Operation:
    """One registered MeTTa function backed by Python."""

    name: MettaName
    fn: Callable[..., Any]
    kind: str  # det | many | raw_det | raw_many
    arity: int
    pass_atoms: bool  # give the callable atoms rather than decoded values
    space: SpaceName | None = None  # where the type declarations were added
    declarations: tuple = ()  # the (: ...) atoms, for unregistration
    arities: tuple = ()  # every registered arity, for reflection facts
    inverse: Callable[..., Any] | None = None  # the backwards direction
    pure: bool = False  # no effect a cache could hide


REGISTRY: dict[str, Operation] = {}


def _decode_arg(wire: Any, pass_atoms: bool) -> Any:  # noqa: FBT001  -- the boolean is established API data and positional compatibility is part of the call shape
    atom = atom_from_wire(wire)
    if pass_atoms:
        return atom
    # Grounded values unwrap to Python; symbols, variables and expressions
    # stay atoms, which is the structure an operation may want to inspect.
    return decode(atom) if isinstance(atom, Gnd) else atom


def _encode_result(value: Any) -> list:
    if isinstance(value, Answer):
        # The explicit answer: bindings for the call's variables, crossing
        # as the seam's own wire form beside the plain atoms.
        return value.to_wire()
    if value is None:
        # None is not a MeTTa value. A deterministic operation returning it
        # answers nothing, the semidet reading; return petta.expr() for unit.
        return _DECLINED
    if isinstance(value, Atom):
        return value.to_wire()
    # An author's opt-in projects: an explicit register_type or a __metta__
    # method makes the value cross as its declared image, so an operation
    # returning a registered type answers (Pt 3 4) rather than an opaque
    # handle. Everything undeclared keeps today's behaviour exactly, the
    # opaque floor; the memoized defaults project() creates never fire here.
    projected = explicit_projection(value)
    if projected is not None:
        return projected.to_wire()
    return encode(value).to_wire()


def dispatch(name: str, tagged_args: list) -> list:
    """One answer, encoded; the declined sentinel for no answer."""
    op = REGISTRY[name]
    args = [_decode_arg(a, op.pass_atoms) for a in tagged_args]
    try:
        return _encode_result(op.fn(*args))
    except Decline:
        return _DECLINED


def dispatch_inverse(name: str, tagged_result: Any):
    """Run an operation BACKWARDS: one result in, argument tuples out.

    The inverse is a relation, not a function, so this always enumerates: a
    plain callable's single answer is yielded once and a generator's answers
    are yielded in turn. Returning None or raising Decline means the result
    has no preimage, which is failure rather than an error, exactly as it is
    forwards.

    Each answer is a sequence of the operation's arguments, encoded the same
    way a forward answer is. A one-argument operation may return the bare
    value rather than a one-tuple, because writing `(x,)` for it reads as a
    typo and forgetting the comma would otherwise iterate a string.
    """
    op = REGISTRY[name]
    for arguments in _preimages(name, _decode_arg(tagged_result, op.pass_atoms)):
        yield [_encode_result(argument) for argument in arguments]


def dispatch_inverse_raw(name: str, result: Any):
    """The same relation for a raw operation, with janus's own conversions.

    An operation registered raw takes those conversions forwards, so its
    inverse takes them backwards. Sending the inverse through the wire
    encoding instead gave one function pair two value conventions: `str` for a
    symbol going out and `Sym` coming back.
    """
    for arguments in _preimages(name, _unbox(result)):
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
    except Decline:
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
    native, because a mid-iteration exception tunnels through py_iter
    past every Prolog catch: keep reduces the failed call to its
    (Error <call> <reason>) atom as the final answer, empty ends the
    stream; control signals and transport failures re-raise, always.
    """
    op = REGISTRY[name]
    args = [_decode_arg(a, op.pass_atoms) for a in tagged_args]
    # closing/1 rather than a bare loop: the stream is one-shot and this is
    # what consumed it. A "many" operation is a generator function by
    # construction (ops._operation_kind), so close() is always there.
    try:
        with closing(op.fn(*args)) as answers:
            for value in answers:
                if value is None:
                    continue
                yield _encode_result(value)
    # KeyboardInterrupt and SystemExit are BaseException, outside this
    # handler by construction, so control signals pass through untouched.
    except Exception as error:
        if mode == "abort" or is_transport_failure(error):
            raise
        if mode == "keep":
            call = Expr(
                [Sym(name), *(encode(_decode_arg(a, True)) for a in tagged_args)]  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
            )
            reason = f"{type(error).__name__}: {error}"
            yield Expr([Sym("Error"), call, Gnd(reason)]).to_wire()


def _unbox(value: Any) -> Any:
    return value.value if isinstance(value, Box) else value


def _rebox(value: Any) -> Any:
    """Whatever janus would rewrite goes back boxed; primitives pass raw.

    A raw result reaching Prolog goes through janus conversion exactly as an
    argument does, so an ndarray returned bare would explode into a list of
    element objects; the box is the envelope that keeps it one value.
    """
    if value is None or isinstance(value, (bool, int, float, str, Box)):
        return value
    return Box(value)


def dispatch_raw(name: str, args: list) -> Any:
    """Raw call: janus's own conversions in, the bare return value out.

    For operations over object references and numbers, where the encoding
    would cost more than the call. Symbols arrive as str and booleans as
    janus values here; use an encoded operation when that fidelity matters.
    Boxed arguments unbox on the way in and opaque results box on the way
    out, so an operation body only ever sees real objects. None crosses as
    janus @none, which the shim reads as no answer; Decline maps onto it.
    """
    try:
        return _rebox(_refuse_raw_answer(REGISTRY[name].fn(*[_unbox(a) for a in args])))
    except Decline:
        return None


def dispatch_raw_many(name: str, args: list):
    with closing(REGISTRY[name].fn(*[_unbox(a) for a in args])) as answers:
        for value in answers:
            yield _rebox(_refuse_raw_answer(value))


def _refuse_raw_answer(value: Any) -> Any:
    """A raw operation is the opaque fast path and its results skip the wire,
    so an Answer here would cross as an inert handle and its bindings would
    silently never bind. Refusing is the honest reading; bindings need the
    wire, so the operation drops raw=True.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(value, Answer):
        msg = (
            "a raw operation answered petta.Answer; raw results skip the "
            "wire the bindings cross on, so register the operation without "
            "raw=True to answer bindings"
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
    value = obj.value if isinstance(obj, Box) else obj
    names = [c.__name__ for c in type(value).__mro__ if c.__name__ != "object"]
    names.extend(extra_types(value))
    return names


# -------------------------------------------------------------- extra typing
#
# (predicate, type name) pairs; an object satisfying a predicate carries the
# name as an additional type candidate. Consulted by the engine through the
# shim's metta_grounded_extra_type/2 bridge.

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
