"""Purpose: read the engine's common property bags for scoped head names.

Guarantees: get_property and the library card use metta_py_head_claims,
which projects metta_head_property/3 [tested:
test_get_property_matches_metta_and_explain; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
Native expression identities carry an explicit space scope, distinct from a
library's source list [tested:
test_a_parametric_namespace_lists_resolves_and_inherits_native_functions; commit=WORKTREE].
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import metta.doors as _doors
from metta._atoms.factories import Atom, Symbol, _atom_from_wire
from metta._lazy import lazy


@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.tuple,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch20_extending_the_engine/test_references.py::test_get_property_matches_metta_and_explain',),
    alias='get_property',
    binding=_doors.Binding('metta_py_head_claims', _doors.Wire.atoms),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/ch20_extending_the_engine/test_references.py::test_get_property_requires_a_head_name'),),
)
def get_property(space: _root.Space, head: str | Symbol, /) -> tuple[Atom, ...]:
    """Return visibility, origins and declared properties of a head.

        space.get_property("car-atom")

    The answers are the atoms ``(get-property car-atom)`` enumerates, including
    every defining origin. An unknown file is empty text and an unknown line
    is -1. The query does not compile a lazy definition.
    """
    if not isinstance(head, (str, Symbol)):
        message = "get_property requires a head name as str or Symbol"
        raise TypeError(message)
    rows = space._rt.apply_must("metta_py_head_claims", ["space", space._space], [str(head)])
    return tuple(_atom_from_wire(wire) for wire in rows[0][1])


if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
