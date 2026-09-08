"""Purpose: the cast verb of the convert door, against the engine's own type
discipline. cast(space, value, type) answers value, narrowed to its Python-most
spelling, when the engine admits it as that type: the exact
('get-type' then 'get-metatype') acceptance the translator compiles
for a typed argument position, run in the space's scope so its ':'
declarations and &self's both answer. Protocol types registered
through metta.integrate.register_object_type participate, which makes
this duck typing through the type system: an object satisfying the
predicate casts to the protocol's name. A refused cast raises
CastError naming the value's actual type candidates, the loud spelling
of what a typed call does silently (a mismatched argument reduces to
nothing). Targets the translator never checks (Atom, %Undefined%, _)
pass unchecked here too, and a Python type spells its MeTTa reading:
bool is Bool before int is Number, str is String, any other class its
own name, the names get-type itself answers.
Guarantees:
  - a concrete Python target type remains the cast's static return type [tested
    test_target_type_overloads_preserve_the_requested_class]
  - the target is positional-only, so its implementation name is not API
    [tested test_cast_target_is_positional_only]
  - an Annotated target casts against its refined type: a value the base admits
    and a decided constraint refuses raises CastError naming that constraint
    and the value [tested: test_cast_honours_a_refinement_and_names_the_violated_constraint;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import typing
from typing import Any, overload

from ._api_types import SpaceLike
from ._convert_registry import _is_plain_class
from ._type_annotations import type_atom_for
from .atoms import Atom, Grounded, Symbol, _atom_from_wire, _encode, parse
from .errors import MettaError

#: Empty on purpose: `metta.convert` is where the two names are published,
#: beside encode, decode and the projection doors, because casting is the
#: third verb of one crossing rather than a door of its own.
__all__: list[str] = []


# Targets the translator compiles no check for; a cast mirrors that.
_UNCHECKED = {"Atom", "%Undefined%", "_"}

# bool before int: bool subclasses int, and True is a Bool, not a Number.
_PYTHON_SPELLINGS: tuple[tuple[type, str], ...] = (
    (bool, "Bool"),
    (int, "Number"),
    (float, "Number"),
    (str, "String"),
)


class CastError(MettaError, TypeError):
    """A cast the engine's type discipline refuses."""


def _type_atom(type_: Any) -> Atom:
    """The target type as an atom: an Atom stands, source text parses,
    and a Python type spells the name get-type answers for its values.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(type_, Atom):
        return type_
    if isinstance(type_, str):
        return parse(type_)
    if _is_plain_class(type_):
        for spelled, name in _PYTHON_SPELLINGS:
            if type_ is spelled:
                return Symbol(name)
        return Symbol(type_.__name__)
    if typing.get_origin(type_) is typing.Annotated:
        # A refined annotation spells `(Annotated Base C...)`, the reading a
        # signature gives it, so the same declaration casts and declares.
        return type_atom_for(type_)
    msg = (
        "a cast target must be an Atom, MeTTa source text, a Python type, "
        f"or an Annotated type, got {type_!r}"
    )
    raise TypeError(
        msg
    )


def _narrow(value: Any) -> Any:
    """The Python-most spelling of an admitted value: a ground atom
    unwraps to its Python value, everything else answers itself.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(value, Grounded):
        return getattr(value, "value", value)
    return value


@overload
def cast[CastT](space: SpaceLike, value: Any, type_: type[CastT], /) -> CastT: ...


@overload
def cast(space: SpaceLike, value: Any, type_: Atom | str, /) -> Any: ...


def cast(space: SpaceLike, value: Any, type_: Any, /) -> Any:
    """Answer value, narrowed, when space's type discipline admits it as
    type_; raise CastError naming its actual types otherwise.

        m.run("(: Ann Person)")
        assert m.cast(S.Ann, "Person") is S.Ann
        assert m.cast(3, int) == 3

    space may be a context or a space.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    home = space.self
    target = _type_atom(type_)
    if isinstance(target, Symbol) and str(target) in _UNCHECKED:
        return _narrow(value)
    atom = value if isinstance(value, Atom) else _encode(value)
    answered = home.runtime.apply_must(
        "metta_py_cast", home._space, atom.to_wire(), target.to_wire()
    )
    if answered[0] == "s" and answered[1] == "ok":
        return _narrow(value)
    if answered[0] == "r":
        # The base admits the value and one refinement does not: name that
        # constraint and the value, the engine's own BadArgValue reading.
        constraint = _atom_from_wire(answered[1])
        msg = (
            f"{atom} violates {constraint}, the refinement {target} declares, "
            f"in {home._space}"
        )
        raise CastError(msg)
    candidates = ", ".join(str(_atom_from_wire(t)) for t in answered[1])
    msg = (
        f"{atom} does not admit type {target} in {home._space}: "
        f"its types are {candidates}"
    )
    raise CastError(
        msg
    )
