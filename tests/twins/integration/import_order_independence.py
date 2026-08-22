"""Purpose: prove that an import may use a function defined by a later import.

Assumes:
  - the imported index loads uses before defines and then calls the resulting
    function [source: examples/integration/_fixtures/imports/import_order/index.metta lines 1-4; commit=WORKTREE]
Guarantees:
  - twin performs the import and checks its caller after the fixture's own
    claim succeeds [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/integration/import_order_independence.metta; fixture=fresh isolated process; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 7646..7710 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 7646,
    "maximum": 7710,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}
RUNG = "import! has no handle method, so its target space remains a named term"

SELF = S["&self"]
INDEX = S["examples/integration/_fixtures/imports/import_order/index"]


def twin(m):
    """Import the index and ask the caller whose callee arrived second."""
    m.eval(S["import!"](SELF, INDEX))

    assert m.eval(S["import-order-caller"]()) == [S["import-order-ok"]]
