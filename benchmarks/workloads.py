"""Purpose: share exact pure-Python workloads between pytest and perf.
Guarantees:
  - wire_codec derives its atom-node count from the term it transforms
    [tested test_pure_workload_counts_are_derived]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta import S, V, expr
from petta.atoms import from_wire
from petta.testing import count_atoms

TERM_COUNT = 20_000
WIRE_TRIPS = 2_000


def wire_atom():
    """Build the fixed tree used by the wire codec workload."""
    return expr(
        S.deep,
        *(expr(S.node, index, float(index), S.leaf) for index in range(50)),
    )


def wire_codec(atom, trips: int = WIRE_TRIPS) -> int:
    """Encode and decode a fixed tree, returning processed atom nodes."""
    decoded = None
    for _ in range(trips):
        decoded = from_wire(atom.to_wire())
    if decoded != atom:
        raise AssertionError("wire codec workload did not round-trip its atom")
    return trips * count_atoms(atom)


def term_operators(terms: int = TERM_COUNT) -> int:
    """Build comparison terms and return the number built."""
    for index in range(terms):
        (V.age >= index) & (V.age <= index + 10) | ~V.retired
    return terms
