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
  - undefined truth has one value-and-delay frame with no optional constraint
    payload [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=WORKTREE]
  - n decodes Python integers without a width conversion, so Number and
    BigInt retain every digit [tested test_janus_carries_bigint_losslessly]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from ._atoms_core import Atom, Box, Expr, Gnd, Handle, _wire_sym, _wire_var
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
        return _symbol_from_wire(payload)
    if tag == "g":
        return _string_from_wire(payload)
    if tag == "n":
        return _number_from_wire(payload)
    if tag == "b":
        return _boolean_from_wire(payload)
    if tag == "v":
        return _variable_from_wire(payload)
    if tag == "o":
        return _object_from_wire(payload)
    raise ValueError(f"unknown wire tag {tag!r}")


def _handle_from_wire(ident: Any, text: Any) -> Atom:
    if isinstance(ident, bool) or not isinstance(ident, int):
        raise ValueError(f"wire handle id must be an integer, got {ident!r}")
    if not isinstance(text, str):
        raise ValueError(f"wire handle text must be a string, got {text!r}")
    return Handle(ident, text)


def _symbol_from_wire(payload: Any) -> Atom:
    if not isinstance(payload, str):
        raise ValueError(f"wire symbol payload must be text, got {payload!r}")
    return _wire_sym(payload)


def _string_from_wire(payload: Any) -> Atom:
    if not isinstance(payload, str):
        raise ValueError(f"wire string payload must be text, got {payload!r}")
    return Gnd(payload)


def _number_from_wire(payload: Any) -> Atom:
    if type(payload) not in (int, float):
        raise ValueError(f"wire number payload must be numeric, got {payload!r}")
    return Gnd(payload)


def _boolean_from_wire(payload: Any) -> Atom:
    if isinstance(payload, bool):
        return Gnd(payload)
    if payload in ("true", "false"):
        return Gnd(payload == "true")
    raise ValueError(f"wire boolean payload must be true or false, got {payload!r}")


def _variable_from_wire(payload: Any) -> Atom:
    if not isinstance(payload, str):
        raise ValueError(f"wire variable payload must be text, got {payload!r}")
    return _wire_var(payload)


def _object_from_wire(payload: Any) -> Atom:
    return Gnd(payload.value if isinstance(payload, Box) else payload)


class Undefined:
    """An answer whose truth is undefined under Well Founded Semantics.

    eval() yields one of these instead of a plain atom when the answer's
    derivation hangs on unresolved tabled goals, a loop through tnot.
    value holds the answer term and why holds the delay condition the engine
    reported (call_delays). Truthiness is refused on purpose: undefined is
    neither True
    nor False, so branch on .value and .why explicitly, the reason
    KeyboardInterrupt lives outside Exception applied to truth.
    """

    __slots__ = ("value", "why")

    def __init__(self, value: Atom, why: str) -> None:
        self.value = value
        self.why = why

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
        )

    def __hash__(self) -> int:
        return hash((Undefined, self.value, self.why))

    def __repr__(self) -> str:
        return f"Undefined({self.value!r}, why={self.why!r})"


def _expression_children(payload: Any) -> list | tuple:
    if not isinstance(payload, (list, tuple)):
        raise ValueError(f"wire expression payload must be a list, got {payload!r}")
    return payload


def _append_nontext_child(
    tag: Any,
    payload: Any,
    items: list[Atom | _PendingExpr],
    pendings: list[_PendingExpr],
    stack: list[tuple[Any, _PendingExpr]],
) -> None:
    if tag == "e":
        nested = _PendingExpr()
        pendings.append(nested)
        items.append(nested)
        stack.append((payload, nested))
        return
    items.append(_leaf_from_wire(tag, payload))


def _finish_expression(pendings: list[_PendingExpr], root: _PendingExpr) -> Expr:
    # Children are discovered after their parents, so reverse discovery
    # builds every nested expression before its holder.
    for pending in reversed(pendings):
        pending.built = Expr(
            [item.built if isinstance(item, _PendingExpr) else item for item in pending.items]
        )
    return root.built


def _expression_from_wire(payload: Any) -> Expr:
    root = _PendingExpr()
    pendings: list[_PendingExpr] = [root]
    stack: list[tuple[Any, _PendingExpr]] = [(payload, root)]
    # Symbols and numbers decode inline, validation kept: a 2000-row answer
    # is hundreds of thousands of cells, and a dispatch call per cell was
    # half the query path's whole cost, profiled. The less common tag paths
    # stay separate so their validation remains readable.
    wire_sym, gnd, seq = _wire_sym, Gnd, (list, tuple)
    string_from_wire, append_nontext = _string_from_wire, _append_nontext_child
    while stack:
        children, pending = stack.pop()
        children = _expression_children(children)
        items = pending.items
        for child in children:
            if not isinstance(child, seq):
                raise ValueError(f"malformed wire term: {child!r}")
            if len(child) != 2:
                # The one three-element wire is a native handle reference.
                if len(child) == 3 and child[0] == "h":
                    items.append(_handle_from_wire(child[1], child[2]))
                    continue
                raise ValueError(f"malformed wire term: {child!r}")
            tag, payload = child
            if tag == "s":
                if not isinstance(payload, str):
                    raise ValueError(f"wire symbol payload must be text, got {payload!r}")
                items.append(wire_sym(payload))
            elif tag == "n":
                if type(payload) not in (int, float):
                    raise ValueError(f"wire number payload must be numeric, got {payload!r}")
                items.append(gnd(payload))
            elif tag == "g":
                items.append(string_from_wire(payload))
            else:
                append_nontext(tag, payload, items, pendings, stack)
    return _finish_expression(pendings, root)


def from_wire(wire: Any) -> Atom | Undefined:
    """Rebuild an atom from the tagged wire form janus delivered.

    Iterative, because expression depth is data and must not meet Python's
    recursion ceiling; strict, because a malformed payload is a boundary
    bug that must surface rather than coerce.
    """
    if not isinstance(wire, (list, tuple)):
        raise ValueError(f"malformed wire term: {wire!r}")
    # The u tag wraps a whole answer whose truth is undefined; it never
    # nests inside expressions, so it is handled at the entry alone.
    match wire:
        case ["u", value, why]:
            return Undefined(atom_from_wire(value), str(why))
        case ["e", payload]:
            return _expression_from_wire(payload)
        case ["h", ident, text]:
            return _handle_from_wire(ident, text)
        case [tag, payload]:
            return _leaf_from_wire(tag, payload)
        case _:
            raise ValueError(f"malformed wire term: {wire!r}")


def atom_from_wire(wire: Any) -> Atom:
    """Decode a wire value where the protocol requires a definite atom."""
    value = from_wire(wire)
    if isinstance(value, Undefined):
        raise ValueError(
            "undefined truth is valid only as a complete evaluation answer, "
            "not where the wire protocol requires an atom"
        )
    return value
