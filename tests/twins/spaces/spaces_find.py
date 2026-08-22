"""examples/spaces/spaces_find.metta in Python: a match used as a condition.

lib_spaces' `find` asks whether a pattern matches AND binds what it matched, so
the original nests two of them and falls back twice: no continuation gives
`MissedSecondPiece`, no starting link at all would give `MissedAllPieces`.

At the Python call door `find` answers True once per solution and nothing else:
the bindings it made are not handed back, which is the answer-protocol gap the
ledger's relational-op row owns (residue, P14.10). So the condition is asserted
for what it does say, and the chain below reads its rows through the subscript
door, where a row IS the bindings. Python's own `if` does the falling back,
which is what the original's `if` is.

`import!` is a directive with no Python door yet, so the library arrives
through `m.fn` (residue, P14.13).
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 20742 to 19354, -1388 (-6.7%), by the twin contract
#: change: the one `(test (collapse (if (find ...) ...)) ...)` term became two
#: Python `assert`s over three subscript queries, so `test`, `collapse` and
#: both `if`s left the engine while the matching they wrapped stayed in it and
#: `find` itself is still asked. The library import is the bulk of both sides.
#: Against the example's 24189 the ratio is 0.8001.
#: Prior: 20742, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 19354


def chains(space):
    """Every friendship chain the space holds, with the original's fallbacks."""
    starts = space[S.friend(V.a, V.b)]
    if not starts:
        return [S.MissedAllPieces()]
    found = []
    for start in starts:
        onward = space[S.friend(start.b, V.c)]
        found.extend(S.FoundChain(start.a, start.b, row.c) for row in onward)
        if not onward:
            found.append(S.MissedSecondPiece())
    return found


def twin(m):
    """Import lib_spaces, store two friendships, then walk them."""
    here = S[m.space_name]
    m.fn("import!")(here, S.library(S.lib_spaces))

    m += (S.friend, S.a, S.b)
    m += (S.friend, S.b, S.c)

    # What `find` says at this door: one True per solution, and no bindings.
    assert m.fn("find").all(here, S.friend(V.a, V.b)) == [True, True]

    assert chains(m) == [S.FoundChain(S.a, S.b, S.c), S.MissedSecondPiece()]
