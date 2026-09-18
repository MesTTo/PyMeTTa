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
  - nested undefined wrappers are refused before descending into their
    payload, independently of nesting depth [tested:
    test_nested_undefined_wire_is_refused_before_descent; commit=cfe153315da5cd78e53d64f28fec3c6004fe4777]
  - undefined truth has one value-and-delay frame with no optional constraint
    payload [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - n decodes Python integers without a width conversion, so Number and
    BigInt retain every digit [tested test_janus_carries_bigint_losslessly]
  - n decodes SWI rationals as exact Fractions in leaf and expression positions;
    atoms keep their native species across later crossings and denominator-one
    payloads canonicalize to integers
    [tested: test_rational_payloads_cross_the_scalar_door,
    test_native_rational_wire_round_trip,
    test_integral_rational_wire_is_canonical; commit=615e8a68dce996a0c05b3ddddc71b80bc598442d]
  - p decodes a canonical space name into the executable Space handle for
    the active runtime [tested: test_space_handles_are_term_operands_and_round_trip;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - the tag alone decides the species: an s payload is a Symbol however it is
    spelled, because the engine's encoder asks metta_space_operand/1, the same
    test get-type asks before answering SpaceType, and writes p for every atom
    the language calls a space [tested: test_the_s_tag_stays_a_symbol_however_it_is_spelled,
    test_a_space_the_engine_made_crosses_as_a_space,
    test_the_ampersand_alone_does_not_make_a_space; commit=dee7dd651135f124376c183977b31320e1f9b3a1]
  - a reserved future name decodes to FutureSpace with the active space as its
    lifecycle owner, reusing the published runtime so a foreign landing
    thread never waits behind the home call it is completing [tested:
    test_an_async_operation_answers_a_future_space,
    test_a_transaction_commits_async_launch_before_its_landing;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - object decoding removes every __metta_wire_value__ carrier by protocol,
    while retaining an ENVELOPE (a payload that speaks the protocol)
    privately for later crossings, so transport classes cannot replace the
    carried object's identity or lose metadata
    [tested: test_bridge_answers_preserve_python_object_identity;
    commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
    [tested: test_a_py_atom_declaration_dies_with_its_grounded_value;
    commit=bbf02dd309d15e178a9c83d03b749eb7170b6a20]; a bare object payload
    crosses boxed again exactly as a fresh Grounded of the same value does
    [tested: test_a_returned_python_container_crosses_back_as_one_object;
    commit=6cfa4d2afbfd867f91ee8eec5400a811aa365086]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from fractions import Fraction
from typing import Any

from metta._atoms.model import (
    Atom,
    Expression,
    Grounded,
    _NativeHandle,
    _NativeRational,
    _new_expression,
    _set_children,
    _set_hash,
    _unbox_wire_value,
    _wire_sym,
    _wire_var,
)
from metta._errors.errors import MettaError
from metta._lazy import lazy


class _PendingExpr:
    """A wire expression mid-build; its items become an Expression once every
    nested expression below it has become one.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("built", "items")
    built: Expression

    def __init__(self) -> None:
        self.items: list[Atom | _PendingExpr] = []


def _leaf_from_wire(tag: Any, payload: Any) -> Atom:
    """One non-expression wire term, its payload validated exactly: a wrong
    payload is a boundary bug and must say so, never coerce.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if tag == "s":
        return _wire_sym(_text_payload(payload, "symbol"))
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
    # The word is `metta.vocabularies.WirePayload.text` and is spelled as text
    # here on purpose: this module is BELOW the vocabulary layer, which imports
    # metta._atoms.factories, which imports this. It reaches the reader as part of a
    # sentence rather than as a classifier, which is the one place a word may
    # cross as a string.
    if not isinstance(payload, str):
        msg = f"wire {kind} payload must be {expected}, got {payload!r}"
        raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
    return payload


def _space_from_wire(payload: Any) -> Atom:
    # Any symbol the engine registers is a space name, ampersand-prefixed or
    # not: `(= (space) my_space_name)` with a write through it registers
    # `my_space_name` and `space_names()` lists it. The prefix is how the
    # engine spells the spaces it mints, not a rule of the tag, and demanding
    # it here refused a name the engine's own registry had just handed out.
    payload = _text_payload(payload, "space")
    engine_module = lazy('metta._binding.runtime')
    space_module = lazy('metta._spaces.handle')
    active = engine_module.active_runtime()
    engine = active if active is not None else engine_module.runtime()
    space = lazy('metta._faces.space').Space(payload, _runtime=engine)
    if payload.startswith("&future-"):
        future_type = lazy('metta.parallel').FutureSpace
        owner = lazy('metta._faces.space').Space(space_module.current_space(), _runtime=space.runtime)
        return future_type(space, owner)
    return space


def _string_from_wire(payload: Any) -> Atom:
    return Grounded(_text_payload(payload, "string"))


def _number_from_wire(payload: Any) -> Atom:
    if type(payload) is Fraction:
        return Grounded(payload.numerator) if payload.denominator == 1 else _NativeRational(payload)
    if type(payload) not in (int, float):
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
    value = _unbox_wire_value(payload)
    grounded = Grounded(value)
    if value is not payload:
        # The payload spoke __metta_wire_value__: it is an ENVELOPE, the thing
        # that carries a declaration for a value that cannot be weakly
        # referenced, so it is kept privately and re-sent as itself. A bare
        # object payload carries nothing and crosses boxed again like a fresh
        # value, because janus rewrites a bare dict, list or tuple into a
        # Prolog term on the way in and the engine then never sees an object:
        # re-sending the bare dict made `(py-call (.get prefs size))` answer
        # nothing for a dict the engine had just handed back [tested:
        # test_a_returned_python_container_crosses_back_as_one_object;
        # commit=6cfa4d2afbfd867f91ee8eec5400a811aa365086].
        object.__setattr__(grounded, "_wire_value", payload)
    return grounded


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
        raise MettaError(_undefined_truth_message(self.why))

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


def _expression_from_wire(payload: Any) -> Expression:
    root = _PendingExpr()
    pendings: list[_PendingExpr] = [root]
    stack: list[tuple[Any, _PendingExpr]] = [(payload, root)]
    # Symbols and numbers decode inline, validation kept: a 2000-row answer
    # is hundreds of thousands of cells, and a dispatch call per cell was
    # half the query path's whole cost, profiled. The less common tag paths
    # stay separate so their validation remains readable.
    wire_sym, gnd, seq = _wire_sym, Grounded, (list, tuple)
    number_from_wire = _number_from_wire
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
                items.append(wire_sym(payload))
            elif tag == "n":
                items.append(gnd(payload) if type(payload) in (int, float) else number_from_wire(payload))
            elif tag == "g":
                items.append(string_from_wire(payload))
            elif tag == "p":
                items.append(_space_from_wire(payload))
            else:
                append_nontext(tag, payload, items, pendings, stack)
    return _finish_expression(pendings, root)


def _from_wire(wire: Any) -> Atom | Undefined:
    """Decode a complete evaluation answer, including its undefined truth."""
    # Undefined truth belongs to the complete answer. Its payload, like every
    # ordinary answer, crosses through the definite atom decoder below.
    if isinstance(wire, (list, tuple)) and len(wire) == 3 and wire[0] == "u":
        return Undefined(_atom_from_wire(wire[1]), str(wire[2]))
    return _atom_from_wire(wire)


def _atom_from_wire(wire: Any) -> Atom:
    """Decode a definite atom, with expression depth handled iteratively."""
    if not isinstance(wire, (list, tuple)):
        msg = f"malformed wire term: {wire!r}"
        raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
    # A leaf symbol is the dominant eval result (py-method-call crosses ten
    # thousand of them), so it interns without entering the match below.
    if len(wire) == 2 and wire[0] == "s":
        return _wire_sym(_text_payload(wire[1], "symbol"))
    match wire:
        case ["u", _, _]:
            msg = (
                "undefined truth is valid only as a complete evaluation answer, "
                "not where the wire protocol requires an atom"
            )
            raise ValueError(msg)
        case ["e", payload]:
            return _expression_from_wire(payload)
        case ["h", ident, text]:
            return _handle_from_wire(ident, text)
        case [tag, payload]:
            return _leaf_from_wire(tag, payload)
        case _:
            msg = f"malformed wire term: {wire!r}"
            raise ValueError(msg)
