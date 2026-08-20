"""Purpose: project Python values and type declarations into MeTTa atoms.
Guarantees:
  - projection is recursive and keeps every nested declaration [tested
    test_nesting_is_the_pytree_rule]
  - handle, symbol, expression, and operations images stay distinct [tested
    test_unregistered_object_stays_a_handle,
    test_enum_projects_to_symbols_with_declarations]
  - the four builtin containers share MeTTa's bare-expression image and keep
    reconstruction detail in the full-annotation hook
    [tested: test_the_four_containers_share_one_parameterised_treatment;
     commit=4b340e87ea282045d5bfa7c00a722353dd69a968]
  - scalar Enum subclasses and composite Flags retain the member and type
    declarations that distinguish them from their scalar payloads
    [tested: test_int_str_and_flag_enums_each_project_with_their_declarations;
     commit=49d2fc7b551ad057dfa018c350874bdee0e07cba]
  - a TypedDict's full annotation selects the same named constructor image
    and field declaration as its value
    [tested: test_a_typed_dict_annotation_agrees_with_its_value;
     commit=1b1aa89517584ce3b4abe1024b7a9f85e2c1263d]
  - explicit projection discovers __metta__ on the class and never asks an
    instance proxy whether an arbitrary attribute exists
    [tested: test_dunder_metta_is_read_off_the_class_not_the_instance;
     commit=b50e0538e7e63fe159d8574ae3551f6a4e7fe4f5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import itertools
import operator
from collections.abc import Iterable
from collections.abc import Iterator as IteratorABC
from enum import Enum, EnumType
from typing import Any, NamedTuple, cast

from ._atoms_core import explicit_metta_atom
from ._convert_registry import (
    _default_registration,
    _lookup,
    _record_registration,
    _Registration,
    constructor_for,
    ensure_registered,
    resolved_hints,
)
from ._parameterized import hook_for as _parameterized_hook
from ._parameterized import runtime_annotation
from ._type_annotations import type_atoms_for
from .atoms import Atom, Expr, Gnd, S, Sym, encode, val


class Projected(NamedTuple):
    """What a projection produced: the atom, and the declarations typing it.

    The declarations are (: ...) atoms; adding them to a space once makes
    every later projection of the same type participate in get-type.
    """

    atom: Atom
    declarations: tuple[Expr, ...]


def project(value: Any, annotation: Any = None) -> Projected:
    """One Python value into MeTTa, by the image its type chose.

    The rule, from what the object is rather than from taste: match on its
    parts wants a symbol or an expression, since those are what the matcher
    sees through; identity mattering wants a handle, since a copy would lie.
    Defaults: an Enum member becomes its symbol, a dataclass or NamedTuple a
    constructor expression with parts projected recursively, and everything
    unregistered a grounded handle carried whole, unified by identity.

    project is the explicit spelling; encode() stays value-preserving
    (a dataclass through encode is a handle). The two intents are different:
    encode carries, project translates.
    """
    direct = _project_direct(value)
    if direct is not None:
        return direct
    parameterized = annotation if annotation is not None else runtime_annotation(value)
    hook = _parameterized_hook(parameterized) if parameterized is not None else None
    if hook is not None:
        atom, parts = hook.project(value, parameterized, project)
        nested = [declaration for part in parts for declaration in part.declarations]
        if hook.declarations is not None:
            nested.extend(hook.declarations(parameterized, type_atoms_for))
        return Projected(atom, _dedup(nested))
    return _project_object(value)


def _project_direct(value: Any) -> Projected | None:
    if isinstance(value, Atom):
        return Projected(value, ())
    if isinstance(value, Enum):
        return None
    if isinstance(value, (bool, int, float, str)):
        return Projected(encode(value), ())
    return None


def _project_object(value: Any) -> Projected:
    cls = type(value)
    registration = _registration_for(cls)
    if registration is None:
        return _project_unregistered(value, cls)
    return _project_registered(value, cls, registration)


def _registration_for(cls: type) -> _Registration | None:
    registration = _lookup(cls)
    if registration is not None:
        return registration
    registration = _default_registration(cls)
    if registration is not None:
        # Memoized, so the reverse direction knows the constructor a default
        # projection used without an explicit registration.
        _record_registration(cls, registration)
    return registration


def _project_unregistered(value: Any, cls: type) -> Projected:
    atom = explicit_metta_atom(value)
    if atom is None:
        return Projected(val(value), ())
    return Projected(atom, ())


#Sixteen top-level elements: about 55 inferences of conversion at the
#measured 3.4-per-element slope (220.54 inferences for a flat 64-item
#argument against 10.51 raw), three raw crossings' worth, which is where
#converting stops being obviously cheaper than handing over a handle the
#program may never look inside. A constant, not a knob: a threshold nobody
#tunes is a decision surface nobody has to own.
_AUTO_TRANSPARENT_LIMIT = 16


def auto_image(value: Any) -> str:
    """"opaque" or "transparent" for one value, in O(1), reproducibly.

    The auto rung of the image knob: never a third behaviour, only a choice
    between the two declared ones. Scalars and small sized containers cross
    transparent; unsized values (a generator, an iterator, anything
    length_hint cannot answer) and large containers stay opaque, because an
    unsized value cannot be converted without draining it and a large one
    costs more to convert than the program is likely to read. A value whose
    type declared an image does not reach this function: resolution order is
    per call, per operation, per type, then auto.
    """
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return "transparent"
    # An iterator is a LINEAR source: converting it drains it, which is a
    # side effect no image choice is allowed to have, so it stays a handle
    # even when its length hint is tiny. This is the source-discipline rule
    # (linear against repeated) surfacing inside auto.
    if isinstance(value, IteratorABC):
        return "opaque"
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        if len(value) <= _AUTO_TRANSPARENT_LIMIT:
            return "transparent"
        return "opaque"
    # Re-readable sized values outside the literal containers: a range, a
    # custom Sequence. length_hint answers -1 for the unsized, which stays
    # opaque because measuring it would consume it.
    hint = operator.length_hint(value, -1)
    if 0 <= hint <= _AUTO_TRANSPARENT_LIMIT:
        return "transparent"
    return "opaque"


def explicit_projection(value: Any) -> Atom | None:
    """The atom an AUTHOR's opt-in gives this value, or None.

    Consulted by the operation result path: only an explicit register_type
    or a __metta__ method projects there. The defaults project() memoizes
    for an Enum, dataclass, NamedTuple or pydantic model deliberately do
    NOT, because an operation author who returns a plain object gets a
    handle unless somebody said otherwise: the image floor is opaque, and
    a project() call elsewhere in the process must not change what an
    operation answers.
    """
    cls = type(value)
    registration = _lookup(cls)
    if registration is not None and registration.explicit:
        return _project_registered(value, cls, registration).atom
    return explicit_metta_atom(value)


def _project_registered(value: Any, cls: type, registration: _Registration) -> Projected:
    if registration.image == "symbol":
        return _project_registered_symbol(value, cls, registration)
    if registration.image == "handle":
        return Projected(val(value), ())
    if registration.image == "operations":
        raise TypeError(
            f"{cls.__name__} is registered with the operations image: its "
            f"behaviour crosses as registered operations, not as data. Use "
            f"petta.integrate.wrap_object to register its methods, and carry "
            f"the instance with petta.val."
        )
    return _project_expression(value, cls, registration)


def _project_registered_symbol(value: Any, cls: type, registration: _Registration) -> Projected:
    if registration.to_atom is None:
        return _project_symbol(value, cls, registration)
    text = str(registration.to_atom(value))
    return Projected(
        Sym(text),
        (Expr([S[":"], Sym(text), Sym(registration.type_name)]),),
    )


def _project_symbol(value: Any, cls: type, registration: _Registration) -> Projected:
    if isinstance(value, Enum):
        member = Sym(value.name)
        type_name = registration.type_name
        decls = [Expr([S[":"], Sym(type_name), S.Type])]
        enum_cls = cast(EnumType, cls)
        decls.extend(
            Expr([S[":"], Sym(member.name), Sym(type_name)])
            for member in cast(Iterable[Enum], enum_cls)
        )
        current = Expr([S[":"], Sym(member.name), Sym(type_name)])
        if current not in decls:
            decls.append(current)
        return Projected(member, tuple(decls))
    text = str(value)
    return Projected(
        Sym(text),
        (Expr([S[":"], Sym(text), Sym(registration.type_name)]),),
    )


def _project_expression(value: Any, cls: type, registration: _Registration) -> Projected:
    to_atom = registration.to_atom
    if to_atom is None:
        raise TypeError(
            f"{cls.__name__} is registered as an expression but has no "
            f"to_atom; register one, or give the class __metta__"
        )
    children = to_atom(value)
    if not isinstance(children, (list, tuple)):
        children = (children,)
    projected = [project(c) for c in children]
    decls: list[Expr] = []
    for p in projected:
        decls.extend(p.declarations)
    if registration.field_types:
        decls.extend(declarations(cls))
    else:
        decls.append(_constructor_declaration(registration, projected))
    atom = Expr([Sym(registration.type_name), *(p.atom for p in projected)])
    return Projected(atom, _dedup(decls))


def _constructor_declaration(registration: _Registration, projected: list[Projected]) -> Expr:
    """(: Person (-> String Number Person)), argument types read off the parts."""
    arg_types = [_projected_type_atom(part) for part in projected]
    return Expr(
        [
            S[":"],
            Sym(registration.type_name),
            Expr([S["->"], *arg_types, Sym(registration.type_name)]),
        ]
    )


def _projected_type_atom(projected: Projected) -> Atom:
    """Read a symbol projection's exact declaration before inferring shape."""
    for declaration in projected.declarations:
        if (
            len(declaration.children) == 3
            and declaration.head == S[":"]
            and declaration.children[1] == projected.atom
            and isinstance(declaration.children[2], Sym)
        ):
            return declaration.children[2]
    return S[_type_name_of(projected.atom)]


def _type_name_of(atom: Atom) -> str:
    if isinstance(atom, Gnd):
        v = atom.value
        if isinstance(v, bool):
            return "Bool"
        if isinstance(v, (int, float)):
            return "Number"
        if isinstance(v, str):
            return "String"
        return "%Undefined%"
    if isinstance(atom, Expr) and atom.children and isinstance(atom.head, Sym):
        name = atom.head.name
        constructor = constructor_for(name)
        if constructor is not None:
            return constructor[1].type_name
    return "%Undefined%"


def declarations(cls: type) -> tuple[Expr, ...]:
    """The (: ...) atoms a type contributes, without projecting an instance.
    Constructor arrows carry the field annotations' own types, mapped the
    way registration maps signatures, so a dataclass field typed float
    declares Number rather than %Undefined%; a Union field superposes one
    arrow per member, the checker's own reading of alternatives."""
    hook = _parameterized_hook(cls)
    if hook is not None and hook.declarations is not None:
        return hook.declarations(cls, type_atoms_for)
    if issubclass(cls, Enum):
        return _enum_declarations(cls)
    found = _registration_for(cls)
    if found is None or found.image != "expression":
        return ()
    return _expression_declarations(cls, found)


def _enum_declarations(cls: type[Enum]) -> tuple[Expr, ...]:
    type_name = ensure_registered(cls).type_name
    declared = [Expr([S[":"], Sym(type_name), S.Type])]
    declared.extend(Expr([S[":"], Sym(member.name), Sym(type_name)]) for member in cls)
    return tuple(declared)


def _expression_declarations(cls: type, registration: _Registration) -> tuple[Expr, ...]:
    fields = registration.fields or ()
    hints = resolved_hints(cls)
    alternative_lists = [
        type_atoms_for(hints[f]) if f in hints else [S["%Undefined%"]] for f in fields
    ]
    return _declarations_for_alternatives(registration.type_name, alternative_lists)


def _declarations_for_alternatives(
    type_name: str, alternatives: list[list[Atom]]
) -> tuple[Expr, ...]:
    declared = (
        Expr([S[":"], Sym(type_name), Expr([S["->"], *combo, Sym(type_name)])])
        for combo in itertools.product(*alternatives)
    )
    return tuple(dict.fromkeys(declared))


def _dedup(decls: list[Expr]) -> tuple[Expr, ...]:
    return tuple(dict.fromkeys(decls))
