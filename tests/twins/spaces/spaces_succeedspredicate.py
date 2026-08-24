"""Purpose: examples/spaces/spaces_succeedspredicate.metta in Python: a predicate that binds.

lib_spaces' `succeedsPredicate` takes a space, a relation and its arguments as
one tuple, and answers whether the relation holds. Ground arguments make it a
membership test, which is the first claim; variable arguments make it a
generator, and the second claim USES what it bound.

Both claims are ordinary Python calls. A call answers what the predicate
decided, and `.rows` answers the bindings it made beside those decisions, so a
question carrying the caller's own variables hands back one row per solution
and the `if` that consumes it is Python's own. The library's own name reaches
the bound namespace once it is imported, camel case and all, because the
attribute door spells a name the catalog holds exactly.

`import!` is a directive with no Python door yet, so the library arrives
through the engine's own function, with the handle in the space position
(residue, P14.13). PERFECT: `m += lib.lib_spaces`, a library landing through
the one write door because a library IS knowledge. Its name keeps the
underscore MeTTa gives it, at both doors: `S.lib_spaces` would be the atom
`lib-spaces` and `fn.import_` would be `import-`, so each takes the bracket
that spells the name exactly.
"""

from metta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1


def twin(m):
    """Ask a predicate a ground question, then a binding one."""
    m.fn["import!"](m, S.library(S["lib_spaces"]))  # rung: import! is a directive, and no Python door claims it
    succeeds = m.fn.succeedsPredicate

    # Nothing matches, so the ground question is False.
    assert succeeds((m, S.friend, S.tim, S.tom)).one() is False

    m += (S.friend, S.a, S.b)

    # The binding question answers what it bound, one row per solution.
    assert [(row.a, row.b) for row in succeeds((m, S.friend, V.a, V.b)).rows] == [
        (S.a, S.b)
    ]
