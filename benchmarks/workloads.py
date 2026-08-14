"""Purpose: share exact pure-Python workloads between pytest and perf.
Guarantees:
  - wire_codec derives its atom-node count from the term it transforms
    [tested test_pure_workload_counts_are_derived]
  - json_wire round-trips the same 200-answer DAS-shaped payload through
    every measured iteration [tested test_pure_workload_counts_are_derived]
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
JSON_TRIPS = 2_000


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


def json_payload() -> dict:
    """Build the fixed query envelope and 200 result handles."""
    return {
        "command": "query",
        "params": {
            "query": {
                "syntax": "metta",
                "tokens": ["(Similarity human %x)"],
            },
            "max_answers": 200,
        },
        "answers": [
            {
                "assignment": {"x": f"{index:064x}"},
                "importance": index / 200,
                "strength": 0.9,
            }
            for index in range(200)
        ],
    }


def json_wire(payload: dict, trips: int = JSON_TRIPS) -> int:
    """Encode and decode a DAS-shaped payload, returning round trips."""
    from petta import _json

    decoded = None
    for _ in range(trips):
        decoded = _json.loads(_json.dumps(payload))
    if decoded != payload:
        raise AssertionError("JSON wire workload changed its payload")
    return trips


def term_operators(terms: int = TERM_COUNT) -> int:
    """Build comparison terms and return the number built."""
    for index in range(terms):
        (V.age >= index) & (V.age <= index + 10) | ~V.retired
    return terms
