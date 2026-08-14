"""Purpose: public atom construction, parsing, traversal, equivalence, and matching.
Guarantees:
  - public atom classes retain the petta.atoms pickle path after internal
    module cuts [tested test_atoms_pickle_by_value,
    test_atoms_cross_a_spawned_process_boundary]
  - map_atoms transforms trees iteratively and validates replacements [tested
    test_map_atoms_handles_depth_as_data_and_validates_transform_results]
  - parse uses the engine reader and preserves source variable names [tested
    test_parse_keeps_variable_names]
  - formatter registrations have exact removal counterparts [tested
    test_object_repr_registrations_can_be_removed_exactly]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from typing import Any

from . import _atom_namespace as _namespace
from . import _atoms_core as _core
from ._atom_wire import Undefined, atom_from_wire, from_wire
from ._atoms_core import (
    Atom,
    Box,
    Expr,
    Gnd,
    Sym,
    Var,
    decode,
    encode,
    register_object_repr,
    register_object_repr_protocol,
    unregister_object_repr,
    unregister_object_repr_protocol,
)

_Namespace = _namespace._Namespace
_NAMESPACE_CACHE_MAX = _namespace.NAMESPACE_CACHE_MAX
_WIRE_CACHE_FAST_MAX = _core._WIRE_CACHE_FAST_MAX
_WIRE_CACHE_MAX = _core._WIRE_CACHE_MAX
_WIRE_SYMS = _core._WIRE_SYMS
_WIRE_SYMS_FAST = _core._WIRE_SYMS_FAST
_WIRE_VARS = _core._WIRE_VARS
_WIRE_VARS_FAST = _core._WIRE_VARS_FAST
boxed = _core.boxed

__all__ = [
    "Atom",
    "Expr",
    "Gnd",
    "S",
    "Sym",
    "Undefined",
    "V",
    "Var",
    "alpha_eq",
    "atom_from_wire",
    "decode",
    "encode",
    "expr",
    "from_wire",
    "is_ground",
    "map_atoms",
    "parse",
    "register_object_repr",
    "register_object_repr_protocol",
    "sym",
    "unify",
    "unregister_object_repr",
    "unregister_object_repr_protocol",
    "val",
    "var",
    "variables",
]

# Keep the documented and pickled class location stable across internal cuts.
for _atom_type in (Atom, Box, Expr, Gnd, Sym, Undefined, Var):
    _atom_type.__module__ = __name__

# ----------------------------------------------------------------- constructors


def sym(name: str) -> Sym:
    """A symbol by name, for names that are not Python identifiers."""
    return Sym(name)


def var(name: str) -> Var:
    """A variable by name."""
    return Var(name)


def val(value: Any) -> Gnd:
    """Carry a Python value whole, whatever it is.

    MeTTa has no list type: encode([1, 2, 3]) is the expression (1 2 3), so
    petta.val([1, 2, 3]) is how to say this particular list is one grounded
    value. It crosses by reference, comes back as the same object, and
    unifies by identity.
    """
    return Gnd(value)


def expr(*children: Any) -> Expr:
    """An expression from parts, each encoded."""
    return Expr([encode(c) for c in children])


S = _Namespace(Sym)
V = _Namespace(Var)


# -------------------------------------------------------------------- reading


def parse(source: str) -> Atom:
    """Read one form of MeTTa source into an atom, evaluating nothing.

    Backed by the engine's own reader, with one improvement over sread/2: the
    variable names the DCG collects are kept, so parse("(Parent $x Bob)")
    contains Var('x') rather than a machine name, and the same pattern built
    with V.x compares equal.
    """
    engine = importlib.import_module(f"{__package__}._engine")
    row = engine.runtime().once("petta_py_parse(Src, W)", Src=source)
    return atom_from_wire(row["W"])


def _to_atom(value: Any) -> Atom:
    """Accept an Atom, MeTTa source text, or an encodable Python value."""
    if isinstance(value, Atom):
        return value
    if isinstance(value, str):
        return parse(value)
    return encode(value)


# ------------------------------------------------------------------ inspection


def variables(atom: Atom) -> list[str]:
    """Variable names in an atom, in first-appearance order. Iterative:
    depth is data."""
    out: list[str] = []
    stack: list[Atom] = [atom]
    while stack:
        a = stack.pop()
        if isinstance(a, Var):
            if a.name not in out:
                out.append(a.name)
        elif isinstance(a, Expr):
            stack.extend(reversed(a.children))
    return out


def is_ground(atom: Atom) -> bool:
    """True when the atom carries no variables."""
    return not variables(atom)


def _mapped_candidate(node: Atom, results: list[Atom]) -> Atom:
    """Rebuild one expression only when a mapped child changed identity."""
    if not isinstance(node, Expr):
        return node
    width = len(node.children)
    mapped_children = tuple(results[-width:]) if width else ()
    if width:
        del results[-width:]
    if any(
        mapped is not original
        for mapped, original in zip(mapped_children, node.children, strict=True)
    ):
        return Expr(mapped_children)
    return node


def map_atoms(atom: Atom, transform: Callable[[Atom], Atom]) -> Atom:
    """Transform every node in an atom tree, children before parents.

    The walk is iterative, so nesting depth remains data rather than a Python
    recursion limit. A no-op transform preserves each unchanged Expr object.
    Nodes returned by transform are final for this pass and are not walked
    again.
    """
    if not isinstance(atom, Atom):
        raise TypeError(f"map_atoms expects an Atom, got {type(atom).__name__}")

    stack: list[tuple[Atom, bool]] = [(atom, False)]
    results: list[Atom] = []
    while stack:
        node, expanded = stack.pop()
        if isinstance(node, Expr) and not expanded:
            stack.append((node, True))
            stack.extend((child, False) for child in reversed(node.children))
            continue

        mapped = transform(_mapped_candidate(node, results))
        if not isinstance(mapped, Atom):
            raise TypeError(f"map_atoms transform must return an Atom, got {type(mapped).__name__}")
        results.append(mapped)

    return results[0]


# ----------------------------------------------------------------- equivalence


def alpha_eq(a: Atom, b: Atom) -> bool:
    """Equality up to consistent renaming of variables, PeTTa's =alpha.

    A named function rather than ==, because two atoms must not compare
    differently depending on which variable names they happen to carry.
    """
    return _alpha(encode(a), encode(b), {}, {})


def _alpha(a: Atom, b: Atom, ab: dict, ba: dict) -> bool:
    stack: list[tuple[Atom, Atom]] = [(a, b)]
    while stack:
        x, y = stack.pop()
        if isinstance(x, Var) and isinstance(y, Var):
            if ab.setdefault(x.name, y.name) != y.name:
                return False
            if ba.setdefault(y.name, x.name) != x.name:
                return False
        elif isinstance(x, Expr) and isinstance(y, Expr):
            if len(x.children) != len(y.children):
                return False
            stack.extend(zip(x.children, y.children, strict=True))
        elif x != y:
            return False
    return True


def unify(pattern: Any, atom: Any) -> Mapping[str, Atom] | None:
    """Match a pattern against an atom, returning bindings or None.

    One-way: variables on the pattern side bind; a variable on the atom side
    matches only the same variable. No occurs check, matching SWI's default
    and therefore the engine's.
    """
    bindings: dict[str, Atom] = {}
    if _unify(encode(pattern), encode(atom), bindings):
        return bindings
    return None


def _unify(p: Atom, a: Atom, b: dict) -> bool:
    stack: list[tuple[Atom, Atom]] = [(p, a)]
    while stack:
        x, y = stack.pop()
        if isinstance(x, Var):
            # `_` is anonymous: it matches anything, binds nothing, and two
            # occurrences never constrain each other, the reader's own rule.
            if x.name == "_":
                continue
            seen = b.get(x.name)
            if seen is None:
                b[x.name] = y
            elif seen != y:
                return False
        elif isinstance(x, Expr) and isinstance(y, Expr):
            if len(x.children) != len(y.children):
                return False
            stack.extend(zip(x.children, y.children, strict=True))
        elif x != y:
            return False
    return True
