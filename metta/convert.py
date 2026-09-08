"""Purpose: one door for every crossing between a Python value and an atom,
with three verbs: encode a value, decode an atom, and cast a value against the
engine's own type discipline.

There used to be three doors. `metta.wire` published `encode`, `decode`,
`from_wire` and `atom_from_wire`; `metta.convert` published the projection and
registration half; `metta.casting` published `cast` and `CastError`. All three
answer one question -- what a host value IS on the other side -- and a caller
who had encoded a value and now wanted to check its type had to find a third
module name to do it. The two other names are gone with no alias.

Guarantees:
  - encode, decode, from_wire and atom_from_wire are the codec verbs and atom
    construction stays in metta.atoms [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=WORKTREE]
  - the projection half round-trips and a registration can be withdrawn
    without leaving constructor or name ownership behind [tested:
    test_build_reverses_the_projection, test_registered_custom_type_round_trips,
    test_type_registration_can_be_removed_and_its_name_reclaimed]
  - cast and CastError are this door's third verb and are reached nowhere else
    [tested: extensions/python/tests/ch09_types/test_casting.py; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from ._atom_wire import _atom_from_wire as atom_from_wire
from ._atom_wire import _from_wire as from_wire
from ._atoms_core import decode, encode
from ._convert_build import build
from ._convert_cast import CastError, cast
from ._convert_project import Projected, auto_image, declarations, project
from ._convert_registry import (
    IMAGES,
    ensure_own_registration,
    ensure_registered,
    register_type,
    unregister_type,
)
from ._convert_registry import (
    _is_plain_class as _registry_is_plain_class,
)

_is_plain_class = _registry_is_plain_class

Projected.__module__ = __name__
CastError.__module__ = __name__

__all__ = [
    "IMAGES",
    "CastError",
    "Projected",
    "atom_from_wire",
    "auto_image",
    "build",
    "cast",
    "declarations",
    "decode",
    "encode",
    "ensure_own_registration",
    "ensure_registered",
    "from_wire",
    "project",
    "register_type",
    "unregister_type",
]
