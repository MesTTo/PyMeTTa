"""Purpose: examples/spaces/spaces_find.metta in Python: a match used as a condition.

lib_spaces' `find` asks whether a pattern matches AND binds what it matched, so
the original nests two of them and falls back twice: no continuation gives
`MissedSecondPiece`, no starting link at all would give `MissedAllPieces`.

A call keeps both faces. Iterating `find(...)` answers what the predicate
DECIDED, one `True` per solution or a single `False` when there is none, and
`.rows` answers the bindings it made, paired position for position. So `find`
is asked here exactly as the original asks it, the decision drives Python's own
`if` the way it drives the original's, and the bindings come off the row beside
it. The library's own name reaches the bound namespace once it is imported, so
the ask is `m.fn.find(...)` and nothing is spelled twice.

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


def chains(space, find):
    """Every friendship chain the space holds, with the original's fallbacks."""
    found = []
    starts = find(space, S.friend(V.a, V.b))
    for started, start in zip(starts, starts.rows, strict=True):
        if not started:
            return [S.MissedAllPieces()]
        onward = find(space, S.friend(start.b, V.c))
        for continued, row in zip(onward, onward.rows, strict=True):
            found.append(
                S.FoundChain(start.a, start.b, row.c)
                if continued
                else S.MissedSecondPiece()
            )
    return found


def twin(m):
    """Import lib_spaces, store two friendships, then walk them."""
    m.fn["import!"](m, S.library(S["lib_spaces"]))  # rung: import! is a directive, and no Python door claims it
    find = m.fn.find

    m += (S.friend, S.a, S.b)
    m += (S.friend, S.b, S.c)

    # What `find` says at this door: one row per solution, bound.
    assert [(row.a, row.b) for row in find(m, S.friend(V.a, V.b)).rows] == [
        (S.a, S.b),
        (S.b, S.c),
    ]

    assert chains(m, find) == [S.FoundChain(S.a, S.b, S.c), S.MissedSecondPiece()]
