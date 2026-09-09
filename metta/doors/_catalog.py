"""Purpose: project door contracts to typed catalog atoms at boot.

Guarantees: each row's arguments, axes, implementation, refusals, tiers,
  documentation, and evidence remain queryable [tested:
  test_boot_publishes_complete_typed_door_rows; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
  Nested constructors have distinct names, fixed arities and type
  arrows, including each optional variant [tested:
  test_nested_door_records_have_declared_types; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
  Body order metadata preserves the outer door record's storage arity
  [tested: test_boot_publishes_complete_typed_door_rows; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Owns resources: none. atoms() constructs values; door_catalog.pl owns the
  transactional publication and its previous snapshot.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, Symbol
from metta._layers import ORDERS
from metta.doors import AnswersAs, Door, EvaluationAnswer, Kind, Owner, Receiver, State, Tier, Wire
from metta.doors._order import Order, orders


def _term(head: str, *parts: Any) -> Expression:
    return Expression([Symbol(head), *(
        part if isinstance(part, Atom) else Symbol(str(part)) for part in parts
    )])


def _text(value: str) -> Grounded:
    return Grounded(value)


def _vocabulary(name: str, enum: type[StrEnum]) -> list[Atom]:
    # metta_publish_vocabulary_types derives the type and member declarations
    # when the vocabulary lands in engine/spaces/catalog.pl.
    return [_term("vocabulary", name, *enum)]


def _default(source: str | None) -> Atom:
    return _term("door-required") if source is None else _term("door-default", _text(source))


def _contract(row: Door, order: Order) -> Atom:
    args = _term("door-arguments", Expression(tuple(
        _term(
            "door-argument", arg.name.replace('_', '-'), arg.type.to_atom(),
            _default(arg.default), arg.delivery, arg.kind.name.lower().replace('_', '-'),
        )
        for arg in row.args
    )))
    sugar = row.sugar_of
    binding = row.binding
    provider = row.provider
    # Partial kind lookups enumerate storage arities in metta_catalog_clause/2.
    # [source: engine/spaces/catalog.pl:metta_catalog_clause/2;
    # commit=a0c13955d672c2eb5c2b44dc0d74b0993d1b29e2]
    # Order describes the body; nesting it keeps those existing arities stable.
    body_order = _term("door-order", Grounded(order.number)) if order.number is not None else _term(
        "door-unordered", Expression(tuple(Symbol(name) for name, present in (
            ("mixed", order.mixed), ("open", bool(order.open)),
            ("recursive", bool(order.cycles)), ("dependency", bool(order.blocked_by)),
        ) if present)),
    )
    return _term(
        "door", row.name, row.kind, row.owner, args, row.answers, row.effect, row.determinism,
        _term("door-sugar", sugar.base, Expression(tuple(
            _term("door-fixed", name.replace('_', '-'), _text(repr(value))) for name, value in sugar.fixed
        ))) if sugar else _term("door-no-sugar"),
        _term("door-binding", binding.door, binding.wire) if binding else _term("door-no-binding"),
        _term("door-provider", provider.point, provider.registrant, provider.namespace)
        if provider else _term("door-no-provider"),
        _term("door-body", _text(row.body.reference), row.body.receiver, body_order)
        if row.body else _term("door-no-body", body_order),
        _term("door-refuses", Expression(tuple(
            _term("door-refusal-witness", refusal.kind, _text(refusal.witness)) for refusal in row.refuses
        ))),
        _term("door-tiers", Expression(tuple(Symbol(tier) for tier in row.tiers))),
        _term("door-docs", _doc_subject(row)),
        _term("door-evidence", Expression(tuple(_text(evidence) for evidence in row.evidence))),
        _term("door-assumes", row.assumes.state, args),
        _term("door-guarantees", row.answers, row.guarantees.type.to_atom(), row.effect, row.determinism),
        _term("door-fails-when", Expression(tuple(Symbol(refusal.kind) for refusal in row.refuses)), Grounded(row.fails_when.propagates)),
    )


def _doc_subject(row: Door) -> Symbol:
    return Symbol('host-' + row.key.replace(':', '-'))


def _types() -> list[Atom]:
    """Declare the fixed record grammar using the engine's kind and arrow rows."""
    # closed-set: decides; policy=the catalog representation of typed door fields; reads=Door, Argument, Assumes, Guarantees and FailsWhen in metta.doors
    schemas = (
        ("layer", "PackageLayer", ("Atom", "Number")),
        ("door-required", "DoorDefault", ()),
        ("door-default", "DoorDefault", ("String",)),
        ("door-argument", "DoorArgument", ("Atom", "Type", "DoorDefault", "ArgumentDelivery", "DoorArgumentKind")),
        ("door-arguments", "DoorArguments", ("Expression",)),
        ("door-fixed", "DoorFixedArgument", ("Atom", "String")),
        ("door-no-sugar", "DoorSugar", ()),
        ("door-sugar", "DoorSugar", ("Atom", "Expression")),
        ("door-no-binding", "DoorBinding", ()),
        ("door-binding", "DoorBinding", ("Atom", "DoorWire")),
        ("door-no-provider", "DoorProvider", ()),
        ("door-provider", "DoorProvider", ("Atom", "Atom", "Atom")),
        ("door-no-body", "DoorBody", ("DoorOrder",)),
        ("door-body", "DoorBody", ("String", "DoorReceiver", "DoorOrder")),
        ("door-refusal-witness", "DoorRefusalWitness", ("RefusalKind", "String")),
        ("door-refuses", "DoorRefusals", ("Expression",)),
        ("door-tiers", "DoorTiers", ("Expression",)),
        ("door-docs", "DoorDocs", ("Atom",)),
        ("door-evidence", "DoorEvidence", ("Expression",)),
        ("door-assumes", "DoorAssumes", ("DoorState", "DoorArguments")),
        ("door-guarantees", "DoorGuarantees", ("DoorAnswers", "Type", "EffectClass", "Determinism")),
        ("door-fails-when", "DoorFailsWhen", ("Expression", "Bool")),
        ("door-order", "DoorOrder", ("Number",)),
        ("door-unordered", "DoorOrder", ("Expression",)),
        ("door", "DoorDeclaration", (
            "Atom", "DoorKind", "DoorOwner", "DoorArguments", "DoorAnswers",
            "EffectClass", "Determinism", "DoorSugar", "DoorBinding", "DoorProvider",
            "DoorBody", "DoorRefusals", "DoorTiers", "DoorDocs", "DoorEvidence",
            "DoorAssumes", "DoorGuarantees", "DoorFailsWhen",
        )),
    )
    vocabularies = (
        "door-kind", "door-owner", "door-answers", "door-wire", "door-receiver",
        "door-state", "door-argument-kind", "argument-delivery", "effect-class",
        "determinism", "refusal-kind",
    )
    by_type = {"".join(part.capitalize() for part in name.split('-')): name for name in vocabularies}
    out: list[Atom] = [_term(":", result, "Type") for result in dict.fromkeys(result for _, result, _ in schemas)]
    out.append(_term(":<", "DoorDeclaration", "Declaration"))
    for head, result, arguments in schemas:
        out.append(_term("kind", head, *(
            _term("one-of", by_type[argument]) if argument in by_type
            else "symbol" if argument == "Atom" else "term" for argument in arguments
        )))
        out.append(_term(":", head, _term("->", *arguments, result)))
    return out


def atoms(rows: Iterable[Door]) -> tuple[Atom, ...]:
    """The complete typed catalog snapshot for these exact declarations."""
    rows = tuple(rows)
    derived = orders(rows)
    kinds = (
        ("door-kind", Kind), ("door-answers", AnswersAs), ("door-tier", Tier),
        ("door-owner", Owner), ("door-receiver", Receiver), ("door-state", State),
        ("door-wire", Wire), ("evaluation-answer", EvaluationAnswer),
    )
    result: list[Atom] = [atom for name, enum in kinds for atom in _vocabulary(name, enum)]
    argument_kinds = [kind.name.lower().replace('_', '-') for kind in inspect._ParameterKind]
    result += [
        _term("vocabulary", "door-argument-kind", *argument_kinds),
        *_types(),
        *(_term("layer", package, Grounded(order)) for package, order in ORDERS.items()),
        _term(":", "host-type", _term("->", "Atom", "Atom", "Type")),
        _term(":", "host-apply", _term("->", "Type", "Expression", "Type")),
        _term(":", "host-union", _term("->", "Expression", "Type")),
        _term(":", "host-literal", _term("->", "Expression", "Type")),
    ]
    for row in rows:
        result.append(_contract(row, derived[row.key]))
        result.append(_term("@doc", _doc_subject(row), _term("@kind", "function"), _term("@desc", _text(row.docs))))
    return tuple(result)
