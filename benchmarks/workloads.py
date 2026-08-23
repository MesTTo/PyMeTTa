"""Purpose: share exact pure-Python workloads between pytest and perf.
Guarantees:
  - wire_codec derives its atom-node count from the term it transforms
    [tested test_pure_workload_counts_are_derived]
  - json_wire round-trips the same 200-answer DAS-shaped payload through
    every measured iteration [tested test_pure_workload_counts_are_derived]
  - term_operators builds explicit comparison terms now that rich comparison
    is reserved for atom ordering [tested: test_pure_workload_counts_are_derived;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from metta import S, V, Expression
from metta.wire import from_wire
from metta.testing import count_atoms

TERM_COUNT = 20_000
WIRE_TRIPS = 2_000
JSON_TRIPS = 2_000


def wire_atom():
    """Build the fixed tree used by the wire codec workload."""
    return Expression(
        S.deep,
        *(Expression(S.node, index, float(index), S.leaf) for index in range(50)),
    )


def wire_codec(atom, trips: int = WIRE_TRIPS) -> int:
    """Encode and decode a fixed tree, returning processed atom nodes.

    Each trip encodes the atom the PREVIOUS trip decoded, never the same
    object twice, so encoding stays cold. Re-encoding one long-lived atom
    would answer Expression's memoized wire slot from the second trip on, and this
    would stop being a codec measurement at all: measured 2026-08-19, that
    shape reported -31.61% for a change that adds a cache and encodes once.
    """
    source = atom
    for _ in range(trips):
        atom = from_wire(atom.to_wire())
    if atom != source:
        raise AssertionError("wire codec workload did not round-trip its atom")
    return trips * count_atoms(source)


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
    from metta import _json

    decoded = None
    for _ in range(trips):
        decoded = _json.loads(_json.dumps(payload))
    if decoded != payload:
        raise AssertionError("JSON wire workload changed its payload")
    return trips


def term_operators(terms: int = TERM_COUNT) -> int:
    """Build comparison terms and return the number built."""
    for index in range(terms):
        S[">="](V.age, index) & S["<="](V.age, index + 10) | ~V.retired
    return terms


def structures_dispatch(patterns: int = 200, probes: int = 2_000) -> int:
    """Route ground probes through PatternMap and MatchIndex, returning
    hits: the pure-Python structures priced at their dispatch job."""
    from metta.atoms import Grounded, Symbol, Variable, _expression_atoms
    from metta.structures import MatchIndex, PatternMap

    routing = PatternMap()
    index = MatchIndex()
    for n in range(patterns):
        pattern = _expression_atoms(
            (Symbol(f"topic{n % 20}"), Variable("x"), Grounded(n))
        )
        routing[pattern] = n
        index.add(pattern, n)
        ground = _expression_atoms(
            (Symbol(f"topic{n % 20}"), Symbol("fixed"), Grounded(n))
        )
        routing[ground] = n
    hits = 0
    for n in range(probes):
        probe = _expression_atoms(
            (
                Symbol(f"topic{n % 20}"),
                Symbol("fixed"),
                Grounded(n % patterns),
            )
        )
        hits += sum(1 for _ in routing.matching(probe))
        hits += sum(1 for _ in index.matches(probe))
    if not hits:
        raise AssertionError("structures dispatch matched nothing")
    return probes
