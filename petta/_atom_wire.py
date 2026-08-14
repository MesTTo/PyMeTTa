"""Purpose: validate and decode tagged Janus wire values into atom trees.
Guarantees:
  - malformed tags and payloads raise at the boundary [tested
    test_malformed_wire_is_refused]
  - expression depth remains data rather than Python recursion [tested
    test_deep_terms_cross_and_print]
  - reverse discovery order builds children before parents and uses 16.01%
    fewer instructions than per-child readiness checks [measured 2026-08-14:
    minimum of three instructions:u runs]
  - definite atom boundaries reject undefined truth wrappers [tested
    test_atom_from_wire_rejects_undefined_truth]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from ._atoms_core import Atom, Box, Expr, Gnd, _wire_sym, _wire_var
from .errors import PettaError


class _PendingExpr:
    """A wire expression mid-build; its items become an Expr once every
    nested expression below it has become one."""

    __slots__ = ("built", "items")
    built: Expr

    def __init__(self) -> None:
        self.items: list[Atom | _PendingExpr] = []


def _leaf_from_wire(tag: Any, payload: Any) -> Atom:
    """One non-expression wire term, its payload validated exactly: a wrong
    payload is a boundary bug and must say so, never coerce."""
    if tag == "s":
        if not isinstance(payload, str):
            raise ValueError(f"wire symbol payload must be text, got {payload!r}")
        return _wire_sym(payload)
    if tag == "g":
        if not isinstance(payload, str):
            raise ValueError(f"wire string payload must be text, got {payload!r}")
        return Gnd(payload)
    if tag == "n":
        if isinstance(payload, bool) or not isinstance(payload, (int, float)):
            raise ValueError(f"wire number payload must be numeric, got {payload!r}")
        return Gnd(payload)
    if tag == "b":
        if isinstance(payload, bool):
            return Gnd(payload)
        if payload in ("true", "false"):
            return Gnd(payload == "true")
        raise ValueError(f"wire boolean payload must be true or false, got {payload!r}")
    if tag == "v":
        if not isinstance(payload, str):
            raise ValueError(f"wire variable payload must be text, got {payload!r}")
        return _wire_var(payload)
    if tag == "o":
        if isinstance(payload, Box):
            payload = payload.value
        return Gnd(payload)
    raise ValueError(f"unknown wire tag {tag!r}")


class Undefined:
    """An answer whose truth is undefined under Well Founded Semantics.

    eval() yields one of these instead of a plain atom when the answer's
    derivation hangs on unresolved tabled goals, a loop through tnot.
    value holds the answer term; why holds the delay condition the engine
    reported (call_delays); residual, filled when eval(residuals=True)
    asked for it, holds the residual program, the clauses of the loop
    itself. Truthiness is refused on purpose: undefined is neither True
    nor False, so branch on .value and .why explicitly, the reason
    KeyboardInterrupt lives outside Exception applied to truth.
    """

    __slots__ = ("residual", "value", "why")

    def __init__(self, value: Atom, why: str, residual: str | None = None) -> None:
        self.value = value
        self.why = why
        self.residual = residual

    def __bool__(self) -> bool:
        raise PettaError(
            f"this answer's truth is undefined ({self.why}); branch on "
            f".value and .why explicitly instead of treating it as a "
            f"boolean"
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Undefined)
            and self.value == other.value
            and self.why == other.why
            and self.residual == other.residual
        )

    def __hash__(self) -> int:
        return hash((Undefined, self.value, self.why, self.residual))

    def __repr__(self) -> str:
        return f"Undefined({self.value!r}, why={self.why!r})"


def from_wire(wire: Any) -> Atom | Undefined:
    """Rebuild an atom from the tagged wire form janus delivered.

    Iterative, because expression depth is data and must not meet Python's
    recursion ceiling; strict, because a malformed payload is a boundary
    bug that must surface rather than coerce.
    """
    # The u tag wraps a whole answer whose truth is undefined; it never
    # nests inside expressions, so it is handled at the entry alone.
    if isinstance(wire, (list, tuple)) and len(wire) in (3, 4) and wire[0] == "u":
        residual = wire[3] if len(wire) == 4 else None
        return Undefined(atom_from_wire(wire[1]), str(wire[2]), residual)
    if not isinstance(wire, (list, tuple)) or len(wire) != 2:
        raise ValueError(f"malformed wire term: {wire!r}")
    if wire[0] != "e":
        return _leaf_from_wire(wire[0], wire[1])

    root = _PendingExpr()
    pendings: list[_PendingExpr] = [root]
    stack: list[tuple[Any, _PendingExpr]] = [(wire[1], root)]
    # The three hottest tags decode inline, validation kept: a 2000-row
    # answer is hundreds of thousands of cells, and the dispatch call per
    # cell was half the query path's whole cost, profiled.
    wire_sym, gnd, seq = _wire_sym, Gnd, (list, tuple)
    while stack:
        children, pending = stack.pop()
        if not isinstance(children, seq):
            raise ValueError(f"wire expression payload must be a list, got {children!r}")
        items = pending.items
        for child in children:
            if not isinstance(child, seq) or len(child) != 2:
                raise ValueError(f"malformed wire term: {child!r}")
            tag, payload = child
            if tag == "s":
                if not isinstance(payload, str):
                    raise ValueError(f"wire symbol payload must be text, got {payload!r}")
                items.append(wire_sym(payload))
            elif tag == "n":
                if isinstance(payload, bool) or not isinstance(payload, (int, float)):
                    raise ValueError(f"wire number payload must be numeric, got {payload!r}")
                items.append(gnd(payload))
            elif tag == "g":
                if not isinstance(payload, str):
                    raise ValueError(f"wire string payload must be text, got {payload!r}")
                items.append(gnd(payload))
            elif tag == "e":
                nested = _PendingExpr()
                pendings.append(nested)
                items.append(nested)
                stack.append((payload, nested))
            else:
                items.append(_leaf_from_wire(tag, payload))
    # Children are discovered after their parents, so building in reverse
    # discovery order builds every nested expression before its holder.
    for pending in reversed(pendings):
        pending.built = Expr(
            [item.built if isinstance(item, _PendingExpr) else item for item in pending.items]
        )
    return root.built


def atom_from_wire(wire: Any) -> Atom:
    """Decode a wire value where the protocol requires a definite atom."""
    value = from_wire(wire)
    if isinstance(value, Undefined):
        raise ValueError(
            "undefined truth is valid only as a complete evaluation answer, "
            "not where the wire protocol requires an atom"
        )
    return value
