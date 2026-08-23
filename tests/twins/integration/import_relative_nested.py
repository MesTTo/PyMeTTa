"""examples/integration/import_relative_nested.metta in Python: one import, two files deep.

`root.metta` imports a sibling and a file in a subdirectory, and both of those
imports resolve against the file that wrote them rather than against the
process. Importing `root` alone therefore has to bring in all three, which is
what the two claims check.

The path is written from the repository root because a Python program has no
importing file to resolve against, which is the residue this file carries. The
space is the handle itself, which crosses into the built term as a grounded
operand.
"""

from petta import S

#: The fixture the import reads, from the repository root: the lane runs there.
ROOT = S["examples/integration/_fixtures/imports/relative/root"]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Import the root, then ask the two files it reached."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    m.fn["import!"](m, ROOT)

    assert m.fn.from_sibling().one() == 42
    assert m.fn.from_second().one() == 7
