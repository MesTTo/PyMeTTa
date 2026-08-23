"""Purpose: expose PeTTa atoms, the S/V/G factories, parsing, and matching.
Guarantees:
  - type and keyword builders produce stored terms while ``order_key`` and
    Atom.__lt__ agree on elementwise expression order [tested:
    test_typed_and_arrow_retire_49_raw_type_symbols,
    test_keyword_builders_retire_53_raw_if_mentions, and
    test_plain_sorted_uses_the_engines_elementwise_order; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - public atom classes retain the petta.atoms pickle path after internal
    module cuts [tested test_atoms_pickle_by_value,
    test_atoms_cross_a_spawned_process_boundary]
  - Atom.map transforms trees iteratively and validates replacements [tested
    test_map_atoms_handles_depth_as_data_and_validates_transform_results]
  - parse uses the engine reader and preserves source variable names [tested
    test_parse_keeps_variable_names]
  - engine results restore registered ampersand names as Space operands while
    the public wire decoder keeps explicit s and p tags distinct [tested:
    test_space_handles_are_term_operands_and_round_trip; commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - exact-type formatter registrations have exact removal counterparts [tested
    test_object_repr_registrations_can_be_removed_exactly]
  - the immutable operator lowering table is public data [tested:
    test_the_operator_table_is_generated_from_one_source_with_no_holes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - grounded atoms lift Python arithmetic to staged MeTTa terms [tested:
    test_grounded_atoms_lift_python_operators_to_terms; commit=WORKTREE]
  - if_ preserves both the engine's one-armed and three-armed forms [tested:
    test_if_builder_accepts_the_one_armed_form; commit=WORKTREE]
  - the canonical truth, unit, and context atoms are public values [tested:
    test_the_canonical_atoms_are_public_values;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from typing import Any

from . import _atom_namespace as _namespace
from . import _atom_wire as _wire
from . import _atoms_core as _core
from ._atom_wire import Undefined
from ._atoms_core import (
    Atom,
    Box,
    Expression,
    Grounded,
    Handle,
    Symbol,
    Variable,
    register_object_repr,
    unregister_object_repr,
)
from ._atoms_core import (
    encode as _encode,
)
from ._operator_lowerings import OPERATOR_LOWERINGS, OperatorLowering

_Namespace = _namespace._Namespace
_NAMESPACE_CACHE_MAX = _namespace.NAMESPACE_CACHE_MAX
_WIRE_CACHE_MAX = _core._WIRE_CACHE_MAX
_WIRE_SYMS = _core._WIRE_SYMS
_WIRE_VARS = _core._WIRE_VARS
boxed = _core.boxed
_atom_from_wire = _wire._atom_from_engine_wire
_decode = _core.decode
_from_wire = _wire._from_engine_wire
_expression_atoms = _core._expression_atoms
_register_protocol_repr = _core._register_protocol_repr
_unregister_protocol_repr = _core._unregister_protocol_repr

#: Canonical atoms shared by authored terms and expected answers. They are
#: values, not factories, so a twin never reconstructs their spelling
#: [tested: test_the_canonical_atoms_are_public_values;
#: commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
TRUE = Grounded(value=True)
FALSE = Grounded(value=False)
UNIT = Expression(())
HERE = Expression((Symbol("context-space"),))
_OMITTED = object()

__all__ = [
    "FALSE",
    "HERE",
    "OPERATOR_LOWERINGS",
    "TRUE",
    "UNIT",
    "Atom",
    "Expression",
    "G",
    "Grounded",
    "Handle",
    "OperatorLowering",
    "S",
    "Symbol",
    "Undefined",
    "V",
    "Variable",
    "and_",
    "arrow",
    "ground",
    "if_",
    "in_",
    "not_",
    "or_",
    "order_key",
    "parse",
    "register_object_repr",
    "substitute",
    "typed",
    "unify",
    "unregister_object_repr",
]

# Keep the documented and pickled class location stable across internal cuts.
for _atom_type in (Atom, Box, Expression, Grounded, Handle, Symbol, Undefined, Variable):
    _atom_type.__module__ = __name__

# ----------------------------------------------------------------- constructors


def ground(value: Any) -> Grounded:
    """Carry a Python value whole, whatever it is.

    This is the FFI boxing door. Structural wire conversion lives in
    :mod:`petta.wire`; ``ground([1, 2, 3])`` therefore carries one list by
    identity instead of turning it into an expression.
    """
    return Grounded(value)


class _GroundFactory:
    """The G(value) spelling of ground(value), parallel to S and V."""

    __slots__ = ()

    def __call__(self, value: Any) -> Grounded:
        return ground(value)


G = _GroundFactory()


S = _Namespace(Symbol)
V = _Namespace(Variable)


def _type_atom(value: Any) -> Atom:
    """Accept a type atom or project one Python annotation through one table."""
    if isinstance(value, Atom):
        return value
    from ._type_annotations import type_atom_for  # noqa: PLC0415  -- it imports atoms

    return type_atom_for(value)


def arrow(*positions: Any) -> Expression:
    """Build an arrow type as data, mapping Python types through annotations."""
    return Expression([S["->"], *(_type_atom(position) for position in positions)])


def typed(subject: Any, type_: Any) -> Expression:
    """Build ``(: subject type)`` as data; annotations are accepted as types."""
    return Expression([S[":"], _encode(subject), _type_atom(type_)])


def if_(condition: Any, consequent: Any, alternative: Any = _OMITTED) -> Expression:
    """Build either engine ``if`` arity; Python ``if`` lowers inside define."""
    if alternative is _OMITTED:
        return S["if"](condition, consequent)
    return S["if"](condition, consequent, alternative)


def not_(value: Any) -> Expression:
    """Build a quoted or stored ``not`` term."""
    return S["not"](value)


def and_(*values: Any) -> Expression:
    """Build a quoted or stored ``and`` term."""
    return S["and"](*values)


def or_(*values: Any) -> Expression:
    """Build a quoted or stored ``or`` term."""
    return S["or"](*values)


def in_(member: Any, container: Any) -> Expression:
    """Build a quoted or stored ``in`` term."""
    return S["in"](member, container)


def _expr(*children: Any) -> Expression:
    """Internal variadic constructor; public code calls a Symbol or Expression."""
    return _expression_atoms(_encode(child) for child in children)


# -------------------------------------------------------------------- reading


def _pretty(atom: Any, width: int = 78) -> str:
    """The atom laid out for reading: a subterm prints inline when it fits
    the remaining width, and otherwise breaks after its head with each
    child on its own line two deeper, the classic s-expression
    convention. The engine's (pretty-atom $x) is the same layout on the
    MeTTa side, so a dump reads identically from either tier.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def render(a: Atom, indent: int) -> str:
        inline = str(a)
        if len(inline) <= width - indent or not isinstance(a, Expression) or len(a.children) < 2:
            return inline
        joiner = "\n" + " " * (indent + 2)
        parts = [render(child, indent + 2) for child in a.children[1:]]
        return "(" + str(a.children[0]) + joiner + joiner.join(parts) + ")"

    return render(_to_atom(atom), 0)


def parse(source: str) -> Atom:
    """Read one form of MeTTa source into an atom, evaluating nothing.

    Backed by the engine's own reader, with one improvement over sread/2: the
    variable names the DCG collects are kept, so parse("(Parent $x Bob)")
    contains Variable('x') rather than a machine name, and the same pattern built
    with V.x compares equal.

    Crossed through apply() rather than once(). petta_py_parse/2 already has
    the functional shape, one ground input and one output, and every call that
    passes source text to eval(), run() or match() parses first, so this is a
    second crossing on top of the evaluation's own [measured 2026-08-16:
    eval("(structured (pair a b))") 517.02 inferences and 34.70us, against
    241.01 and 10.60us for the same term prebuilt].
    """
    engine = importlib.import_module(f"{__package__}._engine")
    return _wire._atom_from_engine_wire(engine.runtime().apply_must("petta_py_parse", source))


def _to_atom(value: Any) -> Atom:
    """Accept an Atom, MeTTa source text, or an encodable Python value."""
    if isinstance(value, Atom):
        return value
    if isinstance(value, str):
        return parse(value)
    return _encode(value)


# ------------------------------------------------------------------ inspection


def _variables(atom: Atom) -> list[str]:
    """Variable names in an atom, in first-appearance order. Iterative:
    depth is data.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    out: list[str] = []
    stack: list[Atom] = [atom]
    while stack:
        a = stack.pop()
        if isinstance(a, Variable):
            if a.name not in out:
                out.append(a.name)
        elif isinstance(a, Expression):
            stack.extend(reversed(a.children))
    return out


def _is_ground(atom: Atom) -> bool:
    """Internal predicate; public code reads ``not atom.vars``."""
    return not _variables(atom)


#: Prolog's standard order of terms: Variable < Number < Atom < String < Compound.
#: A bool is a Python int, so it is ranked with the symbols it reads as rather
#: than with the numbers it inherits from.
_ORDER_VAR, _ORDER_NUMBER, _ORDER_SYMBOL = 0, 1, 2
_ORDER_STRING, _ORDER_OBJECT, _ORDER_EXPR = 3, 4, 5


def order_key(atom: Atom) -> tuple:
    """A sort key for atoms, in Prolog's standard order of terms.

        sorted(atoms, key=order_key)

    Atom.__lt__ delegates to this key, so explicit and plain sorting agree.
    The language's list-shaped expressions compare child by child; length is
    reached only when one expression is a prefix of the other. Variables come
    before numbers, symbols, strings, objects, and expressions
    [source: SWI-Prolog 10.1 Reference Manual, Standard Order of Terms].

    Two atoms that compare equal here are not necessarily the same atom: a key
    orders, `same_atom` decides identity.
    """
    if isinstance(atom, Variable):
        return (_ORDER_VAR, atom.name)
    if isinstance(atom, Symbol):
        return (_ORDER_SYMBOL, atom.name)
    if isinstance(atom, Expression):
        children = tuple(order_key(child) for child in atom.children)
        return (_ORDER_EXPR, children)
    value = getattr(atom, "value", atom)
    # bool before int: True is an int in Python and a symbol in MeTTa.
    if isinstance(value, bool):
        return (_ORDER_SYMBOL, str(value))
    if isinstance(value, (int, float)):
        return (_ORDER_NUMBER, value)
    if isinstance(value, str):
        return (_ORDER_STRING, value)
    return (_ORDER_OBJECT, type(value).__name__, repr(value))


def _mapped_candidate(node: Atom, results: list[Atom]) -> Atom:
    """Rebuild one expression only when a mapped child changed identity."""
    if not isinstance(node, Expression):
        return node
    width = len(node.children)
    mapped_children = tuple(results[-width:]) if width else ()
    if width:
        del results[-width:]
    if any(
        mapped is not original
        for mapped, original in zip(mapped_children, node.children, strict=True)
    ):
        return _expression_atoms(mapped_children)
    return node


def _map_atoms(atom: Atom, transform: Callable[[Atom], Atom]) -> Atom:
    """Transform every node in an atom tree, children before parents.

    The walk is iterative, so nesting depth remains data rather than a Python
    recursion limit. A no-op transform preserves each unchanged Expression object.
    Nodes returned by transform are final for this pass and are not walked
    again.
    """
    if not isinstance(atom, Atom):
        msg = f"Atom.map expects an Atom, got {type(atom).__name__}"
        raise TypeError(msg)

    stack: list[tuple[Atom, bool]] = [(atom, False)]
    results: list[Atom] = []
    while stack:
        node, expanded = stack.pop()
        if isinstance(node, Expression) and not expanded:
            stack.append((node, True))
            stack.extend((child, False) for child in reversed(node.children))
            continue

        mapped = transform(_mapped_candidate(node, results))
        if not isinstance(mapped, Atom):
            msg = f"Atom.map transform must return an Atom, got {type(mapped).__name__}"
            raise TypeError(msg)
        results.append(mapped)

    return results[0]


# ----------------------------------------------------------------- equivalence


def _alpha_eq(a: Atom, b: Atom) -> bool:
    """Equality up to consistent renaming of variables, PeTTa's =alpha.

    A named function rather than ==, because two atoms must not compare
    differently depending on which variable names they happen to carry.
    """
    return _alpha(_encode(a), _encode(b), {}, {})


def _alpha(a: Atom, b: Atom, ab: dict, ba: dict) -> bool:
    stack: list[tuple[Atom, Atom]] = [(a, b)]
    while stack:
        x, y = stack.pop()
        if isinstance(x, Variable) and isinstance(y, Variable):
            if ab.setdefault(x.name, y.name) != y.name:
                return False
            if ba.setdefault(y.name, x.name) != x.name:
                return False
        elif isinstance(x, Expression) and isinstance(y, Expression):
            if len(x.children) != len(y.children):
                return False
            stack.extend(zip(x.children, y.children, strict=True))
        elif x != y:
            return False
    return True


def substitute(atom: Any, bindings: Mapping[str, Atom]) -> Atom:
    """The atom with every bound variable replaced, unify's companion:
    substitute(pattern, unify(pattern, atom)) is the matched instance.
    An unbound variable stays itself, so a partial substitution is a
    narrower pattern rather than an error.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    term = _encode(atom)
    if isinstance(term, Variable):
        bound = bindings.get(term.name)
        return bound if bound is not None else term
    if isinstance(term, Expression):
        return _expression_atoms(substitute(child, bindings) for child in term.children)
    return term


def unify(pattern: Any, atom: Any) -> Mapping[str, Atom] | None:
    """Match a pattern against an atom, returning bindings or None.

    One-way: variables on the pattern side bind; a variable on the atom side
    matches only the same variable. No occurs check, matching SWI's default
    and therefore the engine's.
    """
    bindings: dict[str, Atom] = {}
    if _unify(_encode(pattern), _encode(atom), bindings):
        return bindings
    return None


def _unify(p: Atom, a: Atom, b: dict) -> bool:
    stack: list[tuple[Atom, Atom]] = [(p, a)]
    while stack:
        x, y = stack.pop()
        if isinstance(x, Variable):
            # `_` is anonymous: it matches anything, binds nothing, and two
            # occurrences never constrain each other, the reader's own rule.
            if x.name == "_":
                continue
            seen = b.get(x.name)
            if seen is None:
                b[x.name] = y
            elif seen != y:
                return False
        elif isinstance(x, Expression) and isinstance(y, Expression):
            if len(x.children) != len(y.children):
                return False
            stack.extend(zip(x.children, y.children, strict=True))
        elif x != y:
            return False
    return True
