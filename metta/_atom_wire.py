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
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - n decodes Python integers without a width conversion, so Number and
    BigInt retain every digit [tested test_janus_carries_bigint_losslessly]
  - n decodes SWI rationals as exact Fractions in both leaf and expression
    positions [tested: test_rational_payloads_cross_the_scalar_door;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - p decodes a canonical space name into the executable Space handle for
    the active runtime [tested: test_space_handles_are_term_operands_and_round_trip;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - strict decoding preserves explicit s and p tags, while engine decoding
    restores only space names registered by Space plus the reserved future
    namespace [tested: test_an_ampersand_symbol_is_not_reclassified_as_a_space;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - object decoding removes every __petta_wire_value__ carrier by protocol,
    so transport classes cannot replace the carried object's identity
    [tested: test_bridge_answers_preserve_python_object_identity;
    commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib
import threading
from fractions import Fraction
from typing import Any

from ._atoms_core import (
    Atom,
    Expression,
    Grounded,
    _NativeHandle,
    _new_expression,
    _set_children,
    _set_hash,
    _unbox_wire_value,
    _wire_sym,
    _wire_var,
)
from .errors import PettaError

_SPACE_NAMES: list[frozenset[str]] = [frozenset()]
_SPACE_NAMES_LOCK = threading.RLock()


def _remember_space_name(name: str) -> None:
    with _SPACE_NAMES_LOCK:
        _SPACE_NAMES[0] = _SPACE_NAMES[0] | {name}


def _engine_ampersand_from_wire(payload: str) -> Atom:
    # Readers take an immutable snapshot without a lock. Registering a name
    # replaces the frozenset under the write lock, so free-threaded Python
    # cannot observe a set mid-mutation and ordinary symbols keep the codec's
    # measured direct path.
    if payload in _SPACE_NAMES[0] or payload.startswith("&future-"):
        return _space_from_wire(payload)
    return _wire_sym(payload)


class _PendingExpr:
    """A wire expression mid-build; its items become an Expression once every
    nested expression below it has become one.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("built", "items")
    built: Expression

    def __init__(self) -> None:
        self.items: list[Atom | _PendingExpr] = []


def _leaf_from_wire(tag: Any, payload: Any, *, engine: bool = False) -> Atom:
    """One non-expression wire term, its payload validated exactly: a wrong
    payload is a boundary bug and must say so, never coerce.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if tag == "s":
        payload = _text_payload(payload, "symbol")
        if engine and payload.startswith("&"):
            return _engine_ampersand_from_wire(payload)
        return _wire_sym(payload)
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
    if tag == "p":
        return _space_from_wire(payload)
    msg = f"unknown wire tag {tag!r}"
    raise ValueError(msg)


def _handle_from_wire(ident: Any, text: Any) -> Atom:
    if isinstance(ident, bool) or not isinstance(ident, int):
        msg = f"wire handle id must be an integer, got {ident!r}"
        raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
    return _NativeHandle(ident, _text_payload(text, "handle", "a string"))


def _text_payload(payload: Any, kind: str, expected: str = "text") -> str:
    if not isinstance(payload, str):
        msg = f"wire {kind} payload must be {expected}, got {payload!r}"
        raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
    return payload


def _space_from_wire(payload: Any) -> Atom:
    payload = _text_payload(payload, "space")
    if not payload.startswith("&"):
        msg = f"wire space payload must start with &, got {payload!r}"
        raise ValueError(msg)
    space_type = importlib.import_module(f"{__package__}._space").Space
    return space_type(payload)


def _string_from_wire(payload: Any) -> Atom:
    return Grounded(_text_payload(payload, "string"))


def _number_from_wire(payload: Any) -> Atom:
    if type(payload) not in (int, float, Fraction):
        msg = f"wire number payload must be numeric, got {payload!r}"
        raise ValueError(msg)
    return Grounded(payload)


def _boolean_from_wire(payload: Any) -> Atom:
    if isinstance(payload, bool):
        return Grounded(payload)
    if payload in ("true", "false"):
        return Grounded(payload == "true")
    msg = f"wire boolean payload must be true or false, got {payload!r}"
    raise ValueError(msg)


def _variable_from_wire(payload: Any) -> Atom:
    return _wire_var(_text_payload(payload, "variable"))


def _object_from_wire(payload: Any) -> Atom:
    return Grounded(_unbox_wire_value(payload))


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
        raise PettaError(_undefined_truth_message(self.why))

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


def _undefined_truth_message(reason: str) -> str:
    return (
        f"this answer's truth is undefined ({reason}); branch on "
        ".value and .why explicitly instead of treating it as a boolean"
    )

def _expression_children(payload: Any) -> list | tuple:
    if not isinstance(payload, (list, tuple)):
        msg = f"wire expression payload must be a list, got {payload!r}"
        raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
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


def _finish_expression(pendings: list[_PendingExpr], root: _PendingExpr) -> Expression:
    # Children are discovered after their parents, so reverse discovery
    # builds every nested expression before its holder.
    for pending in reversed(pendings):
        # This decoder already validated every child as an Atom. Keep the
        # normalized construction inline because this loop creates one node
        # per decoded expression and is the wire codec's measured hot path.
        children = [
            item.built if isinstance(item, _PendingExpr) else item
            for item in pending.items
        ]
        expression = _new_expression(Expression)
        _set_children(expression, tuple(children))
        _set_hash(expression, None)
        pending.built = expression
    return root.built


def _expression_from_wire(payload: Any, *, engine: bool = False) -> Expression:
    root = _PendingExpr()
    pendings: list[_PendingExpr] = [root]
    stack: list[tuple[Any, _PendingExpr]] = [(payload, root)]
    # Symbols and numbers decode inline, validation kept: a 2000-row answer
    # is hundreds of thousands of cells, and a dispatch call per cell was
    # half the query path's whole cost, profiled. The less common tag paths
    # stay separate so their validation remains readable.
    wire_sym, gnd, seq = _wire_sym, Grounded, (list, tuple)
    string_from_wire, append_nontext = _string_from_wire, _append_nontext_child
    while stack:
        children, pending = stack.pop()
        children = _expression_children(children)
        items = pending.items
        for child in children:
            if not isinstance(child, seq):
                msg = f"malformed wire term: {child!r}"
                raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
            if len(child) != 2:
                # The one three-element wire is a native handle reference.
                if len(child) == 3 and child[0] == "h":
                    items.append(_handle_from_wire(child[1], child[2]))
                    continue
                msg = f"malformed wire term: {child!r}"
                raise ValueError(msg)
            tag, payload = child
            if tag == "s":
                if not isinstance(payload, str):
                    msg = f"wire symbol payload must be text, got {payload!r}"
                    raise ValueError(msg)
                if engine and payload.startswith("&"):
                    items.append(_engine_ampersand_from_wire(payload))
                else:
                    items.append(wire_sym(payload))
            elif tag == "n":
                if type(payload) not in (int, float, Fraction):
                    msg = f"wire number payload must be numeric, got {payload!r}"
                    raise ValueError(msg)
                items.append(gnd(payload))
            elif tag == "g":
                items.append(string_from_wire(payload))
            elif tag == "p":
                items.append(_space_from_wire(payload))
            else:
                append_nontext(tag, payload, items, pendings, stack)
    return _finish_expression(pendings, root)


def _from_wire_mode(wire: Any, *, engine: bool) -> Atom | Undefined:
    """Rebuild an atom from the tagged wire form janus delivered.

    Iterative, because expression depth is data and must not meet Python's
    recursion ceiling; strict, because a malformed payload is a boundary
    bug that must surface rather than coerce.
    """
    if not isinstance(wire, (list, tuple)):
        msg = f"malformed wire term: {wire!r}"
        raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
    # The u tag wraps a whole answer whose truth is undefined; it never
    # nests inside expressions, so it is handled at the entry alone.
    match wire:
        case ["u", value, why]:
            return Undefined(_atom_from_wire_mode(value, engine=engine), str(why))
        case ["e", payload]:
            return _expression_from_wire(payload, engine=engine)
        case ["h", ident, text]:
            return _handle_from_wire(ident, text)
        case [tag, payload]:
            return _leaf_from_wire(tag, payload, engine=engine)
        case _:
            msg = f"malformed wire term: {wire!r}"
            raise ValueError(msg)


def _from_wire(wire: Any) -> Atom | Undefined:
    return _from_wire_mode(wire, engine=False)


def _from_engine_wire(wire: Any) -> Atom | Undefined:
    return _from_wire_mode(wire, engine=True)


def _atom_from_wire_mode(wire: Any, *, engine: bool) -> Atom:
    value = _from_wire_mode(wire, engine=engine)
    if isinstance(value, Undefined):
        msg = (
            "undefined truth is valid only as a complete evaluation answer, "
            "not where the wire protocol requires an atom"
        )
        raise ValueError(  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
            msg
        )
    return value


def _atom_from_wire(wire: Any) -> Atom:
    """Decode a wire value where the protocol requires a definite atom."""
    return _atom_from_wire_mode(wire, engine=False)


def _atom_from_engine_wire(wire: Any) -> Atom:
    """Decode an engine result, restoring known space-name provenance."""
    # A leaf symbol is the dominant eval result (py-method-call crosses ten
    # thousand of them). Keep its validated non-space path as direct as the
    # strict decoder was before engine provenance existed; ampersand names
    # alone need the registry decision.
    if isinstance(wire, (list, tuple)) and len(wire) == 2 and wire[0] == "s":
        payload = wire[1]
        if not isinstance(payload, str):
            msg = f"wire symbol payload must be text, got {payload!r}"
            raise ValueError(msg)
        if not payload.startswith("&"):
            return _wire_sym(payload)
        return _engine_ampersand_from_wire(payload)
    return _atom_from_wire_mode(wire, engine=True)
