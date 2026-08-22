"""Purpose: encode Python values for PeTTa's tagged atom wire and decode them.

Guarantees:
  - encode, decode, from_wire, and atom_from_wire are the only public codec
    names; atom construction stays in petta.atoms [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from ._atom_wire import _atom_from_wire as atom_from_wire
from ._atom_wire import _from_wire as from_wire
from ._atoms_core import decode, encode

__all__ = ["atom_from_wire", "decode", "encode", "from_wire"]
