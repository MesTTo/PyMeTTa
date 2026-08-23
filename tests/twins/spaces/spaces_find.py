"""Purpose: examples/spaces/spaces_find.metta in Python: a match used as a condition.

lib_spaces' `find` asks whether a pattern matches AND binds what it matched, so
the original nests two of them and falls back twice: no continuation gives
`MissedSecondPiece`, no starting link at all would give `MissedAllPieces`.

The bindings now cross. A call carrying the caller's own variables answers
ROWS, so `find` is asked here exactly as the original asks it and Python's own
`if` does the falling back, which is what the original's `if` is.

What the row does not carry is `find`'s own True/False ANSWER, so the two
readings are told apart by whether the variable came back BOUND. PERFECT is the
spelling the fallback wants:

    onward = find(space, S.friend(start.b, V.c))
    if not onward:                      # no solution is no rows
        found.append(S.MissedSecondPiece())

A failing `find` answers one row whose variable is still free instead of no
rows at all, because the False the predicate answers is dropped once a caller
variable turns the answer into a binding row (residue, P14.10). `row.c.vars`
is the honest reading of that row until the answer value travels beside it.

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
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1


def chains(space, find):
    """Every friendship chain the space holds, with the original's fallbacks."""
    found = []
    for start in find(space, S.friend(V.a, V.b)):
        if start.a.vars:
            return [S.MissedAllPieces()]
        for row in find(space, S.friend(start.b, V.c)):
            if row.c.vars:
                found.append(S.MissedSecondPiece())
            else:
                found.append(S.FoundChain(start.a, start.b, row.c))
    return found


def twin(m):
    """Import lib_spaces, store two friendships, then walk them."""
    m.fn["import!"](m, S.library(S["lib_spaces"])).one()
    find = m.fn["find"]

    m += (S.friend, S.a, S.b)
    m += (S.friend, S.b, S.c)

    # What `find` says at this door: one row per solution, bound.
    assert [(row.a, row.b) for row in find(m, S.friend(V.a, V.b))] == [
        (S.a, S.b),
        (S.b, S.c),
    ]

    assert chains(m, find) == [S.FoundChain(S.a, S.b, S.c), S.MissedSecondPiece()]
