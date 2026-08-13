"""Purpose: the operation registry the engine dispatches into. shim.pl calls
dispatch/dispatch_many for encoded operations and dispatch_raw variants for
raw ones; the registry maps a MeTTa function name to the Python callable
behind it, decoding arguments to atoms-or-values and encoding results back.
Importable as petta_ops, the name the Prolog side uses.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .atoms import Atom, Box, Gnd, decode, encode, from_wire
from .errors import Decline

__all__ = ["REGISTRY", "Operation", "dispatch", "dispatch_many", "dispatch_raw", "dispatch_raw_many"]

# The wire form the shim treats as failure rather than a value: the operation
# looked at its arguments and answered nothing.
_DECLINED = ["x", "declined"]


@dataclass(frozen=True)
class Operation:
    """One registered MeTTa function backed by Python."""

    name: str
    fn: Callable[..., Any]
    kind: str  # det | many | raw_det | raw_many
    arity: int
    pass_atoms: bool  # give the callable atoms rather than decoded values
    space: str | None = None  # where the type declaration was added
    declaration: Any = None  # the (: ...) atom, for unregistration


REGISTRY: dict[str, Operation] = {}


def _decode_arg(wire: Any, pass_atoms: bool) -> Any:
    atom = from_wire(wire)
    if pass_atoms:
        return atom
    # Grounded values unwrap to Python; symbols, variables and expressions
    # stay atoms, which is the structure an operation may want to inspect.
    return decode(atom) if isinstance(atom, Gnd) else atom


def _encode_result(value: Any) -> list:
    if value is None:
        # None is not a MeTTa value. A deterministic operation returning it
        # answers nothing, the semidet reading; return petta.expr() for unit.
        return _DECLINED
    if isinstance(value, Atom):
        return value.to_wire()
    return encode(value).to_wire()


def dispatch(name: str, tagged_args: list) -> list:
    """One answer, encoded; the declined sentinel for no answer."""
    op = REGISTRY[name]
    args = [_decode_arg(a, op.pass_atoms) for a in tagged_args]
    try:
        return _encode_result(op.fn(*args))
    except Decline:
        return _DECLINED


def dispatch_many(name: str, tagged_args: list):
    """A generator of encoded answers; each yield is one MeTTa answer."""
    op = REGISTRY[name]
    args = [_decode_arg(a, op.pass_atoms) for a in tagged_args]
    for value in op.fn(*args):
        if value is None:
            continue
        yield _encode_result(value)


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
        return _rebox(REGISTRY[name].fn(*[_unbox(a) for a in args]))
    except Decline:
        return None


def dispatch_raw_many(name: str, args: list):
    for value in REGISTRY[name].fn(*[_unbox(a) for a in args]):
        yield _rebox(value)


# ------------------------------------------------------------ foreign spaces
#
# The shim's foreign-space hooks and the protocol-type hook resolve through
# this module, since petta_ops is the one name the Prolog side imports.

def foreign_match(space, pattern_wire):
    from .foreign import foreign_match as impl

    return impl(space, pattern_wire)


def foreign_atoms(space):
    from .foreign import foreign_atoms as impl

    return impl(space)


def foreign_add(space, atom_wire):
    from .foreign import foreign_add as impl

    return impl(space, atom_wire)


def foreign_remove(space, atom_wire):
    from .foreign import foreign_remove as impl

    return impl(space, atom_wire)


def foreign_clear(space):
    from .foreign import foreign_clear as impl

    return impl(space)


def type_names(obj: Any) -> list[str]:
    """Every type name an object carries, for the engine's typing bridge:
    its classes in resolution order short of object, then every satisfied
    protocol. Computed on the boxed value's contents, and returned as text,
    which janus cannot damage."""
    value = obj.value if isinstance(obj, Box) else obj
    names = [c.__name__ for c in type(value).__mro__ if c.__name__ != "object"]
    names.extend(extra_types(value))
    return names


# -------------------------------------------------------------- extra typing
#
# (predicate, type name) pairs; an object satisfying a predicate carries the
# name as an additional type candidate. Consulted by the engine through the
# shim's py_object_extra_type/2 bridge.

PROTOCOL_TYPES: list[tuple[Any, str]] = []


def extra_types(obj) -> list[str]:
    names = []
    for predicate, name in PROTOCOL_TYPES:
        try:
            if predicate(obj):
                names.append(name)
        except Exception as exc:
            # A broken probe is the registrant's bug: surface it with the
            # protocol's name attached, never as a type quietly missing.
            raise RuntimeError(
                f"the type predicate for protocol {name!r} raised on "
                f"{type(obj).__name__}: {exc}"
            ) from exc
    return names
