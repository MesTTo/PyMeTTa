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

from .atoms import Atom, Gnd, decode, encode, from_wire
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


def dispatch_raw(name: str, args: list) -> Any:
    """Raw call: janus's own conversions in, the bare return value out.

    For operations over object references and numbers, where the encoding
    would cost more than the call. Symbols arrive as str and booleans as
    janus values here; use an encoded operation when that fidelity matters.
    None crosses as janus @none, which the shim reads as no answer, so the
    semidet rule holds on this path too; Decline is mapped to it here.
    """
    try:
        return REGISTRY[name].fn(*args)
    except Decline:
        return None


def dispatch_raw_many(name: str, args: list):
    yield from REGISTRY[name].fn(*args)
