"""Purpose: examples/spaces/spaces_succeedspredicate.metta in Python: a predicate that binds.

lib_spaces' `succeedsPredicate` takes a space, a relation and its arguments as
one tuple, and answers whether the relation holds. Ground arguments make it a
membership test, which is the first claim; variable arguments make it a
generator, and the second claim USES what it bound.

Both claims are ordinary Python calls now. A ground question answers the
boolean, and a question carrying the caller's own variables answers one ROW per
solution, so what the predicate bound is what comes back and the `if` that
consumes it is Python's own.

`import!` is a directive with no Python door yet, so the library arrives
through the engine's own function, with the handle in the space position
(residue, P14.13). PERFECT: `m += lib.lib_spaces`, a library landing through
the one write door because a library IS knowledge. Its name keeps the underscore MeTTa gives it: `S.lib_spaces`
would be the atom `lib-spaces` and no such library exists.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Ask a predicate a ground question, then a binding one."""
    m.fn["import!"](m, S.library(S["lib_spaces"])).one()
    succeeds = m.fn["succeedsPredicate"]

    # Nothing matches, so the ground question is False.
    assert succeeds((m, S.friend, S.tim, S.tom)).one() is False

    m += (S.friend, S.a, S.b)

    # The binding question answers what it bound, one row per solution.
    assert [(row.a, row.b) for row in succeeds((m, S.friend, V.a, V.b))] == [
        (S.a, S.b)
    ]
