"""Purpose: runtime typecasting against the engine's own type discipline.
cast(space, value, type) answers value, narrowed to its Python-most
spelling, when the engine admits it as that type: the exact
('get-type' then 'get-metatype') acceptance the translator compiles
for a typed argument position, run in the space's scope so its ':'
declarations and &self's both answer. Protocol types registered
through petta.integrate.register_object_type participate, which makes
this duck typing through the type system: an object satisfying the
predicate casts to the protocol's name. A refused cast raises
CastError naming the value's actual type candidates, the loud spelling
of what a typed call does silently (a mismatched argument reduces to
nothing). Targets the translator never checks (Atom, %Undefined%, _)
pass unchecked here too, and a Python type spells its MeTTa reading:
bool is Bool before int is Number, str is String, any other class its
own name, the names get-type itself answers.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from ._convert_registry import _is_plain_class
from .atoms import Atom, Gnd, Sym, atom_from_wire, encode, parse
from .errors import PettaError

__all__ = ["CastError", "cast"]

# Targets the translator compiles no check for; a cast mirrors that.
_UNCHECKED = {"Atom", "%Undefined%", "_"}

# bool before int: bool subclasses int, and True is a Bool, not a Number.
_PYTHON_SPELLINGS: tuple[tuple[type, str], ...] = (
    (bool, "Bool"),
    (int, "Number"),
    (float, "Number"),
    (str, "String"),
)


class CastError(PettaError, TypeError):
    """A cast the engine's type discipline refuses."""


def _type_atom(type_: Any) -> Atom:
    """The target type as an atom: an Atom stands, source text parses,
    and a Python type spells the name get-type answers for its values."""
    if isinstance(type_, Atom):
        return type_
    if isinstance(type_, str):
        return parse(type_)
    if _is_plain_class(type_):
        for spelled, name in _PYTHON_SPELLINGS:
            if type_ is spelled:
                return Sym(name)
        return Sym(type_.__name__)
    raise TypeError(
        "a cast target must be an Atom, MeTTa source text, or a Python "
        f"type, got {type_!r}"
    )


def _narrow(value: Any) -> Any:
    """The Python-most spelling of an admitted value: a ground atom
    unwraps to its Python value, everything else answers itself."""
    if isinstance(value, Gnd):
        return value.value
    return value


def cast(space, value: Any, type_: Any) -> Any:
    """Answer value, narrowed, when space's type discipline admits it as
    type_; raise CastError naming its actual types otherwise.

        m.run("(: Ann Person)")
        assert m.cast(S.Ann, "Person") is S.Ann
        assert m.cast(3, int) == 3
    """
    target = _type_atom(type_)
    if isinstance(target, Sym) and str(target) in _UNCHECKED:
        return _narrow(value)
    atom = value if isinstance(value, Atom) else encode(value)
    answered = space.runtime.apply_must(
        "petta_py_cast", space._space, atom.to_wire(), target.to_wire()
    )
    if answered[0] == "s" and answered[1] == "ok":
        return _narrow(value)
    candidates = ", ".join(str(atom_from_wire(t)) for t in answered[1])
    raise CastError(
        f"{atom} does not admit type {target} in {space._space}: "
        f"its types are {candidates}"
    )
