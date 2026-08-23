"""Purpose: prove that an import may use a function defined by a later import.

The space the import writes is the handle itself, which crosses into the
built term as a grounded operand. What stays below the top rung is `import!`
having no Python door of its own, which the residue records.

Assumes:
  - the imported index loads uses before defines and then calls the resulting
    function [source: examples/integration/_fixtures/imports/import_order/index.metta lines 1-4; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - twin performs the import and checks its caller after the fixture's own
    claim succeeds [measured 2026-08-23: twin completed; command=python bindings/python/tools/twin_coverage.py examples/integration/import_order_independence.metta; fixture=fresh isolated process; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1

#: The index the example imports, written from the repository root: a Python
#: program has no importing file to resolve a relative import against.
INDEX = S["examples/integration/_fixtures/imports/import_order/index"]


def twin(m):
    """Import the index and ask the caller whose callee arrived second."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    m.fn["import!"](m, INDEX)

    assert m.fn.import_order_caller().one() == S["import-order-ok"]
