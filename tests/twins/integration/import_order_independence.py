"""examples/integration/import_order_independence.metta in Python: a callee that arrives second.

The index the example imports loads a file that USES a function before it loads
the file that DEFINES it, and then calls the result. So the one claim is that
an import may be written before the import it depends on, and the caller still
answers.

The space the import writes is the handle itself, which crosses into the built
term as a grounded operand. What stays below the top rung is that `import!` has
no Python door of its own, which the residue records.
"""

from metta import S

#: The index the example imports, written from the repository root: a Python
#: program has no importing file to resolve a relative import against. A module
#: name is a NAME, so it is minted at the naming factory.
INDEX = S["examples/integration/_fixtures/imports/import_order/index"]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
BUDGET = 1


def twin(m):
    """Import the index and ask the caller whose callee arrived second."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    m.fn["import!"](m, INDEX)

    assert m.fn.import_order_caller().one() == S["import-order-ok"]
