"""Purpose: examples/reasoning/tilepuzzle.metta in Python: the eight-tile state graph.

Twenty-four move equations say where the blank may go from each of the nine
positions, and a breadth-first loop walks the reachable states, refusing a
duplicate, until the queue empties. The claim is the count it reaches, 181441.

The moves are one shape repeated, so a pair of loops writes them: the blank's
position and the direction are the loop variables, and the row is the eight
placeholders with the blank swapped into place. The example writes all
twenty-four out; here the shape is stated once and the loops supply the rest.

Everything stays at the container door. Every move head destructures a
nine-cell board, `bfs_loop` has two clauses under one head that are
ALTERNATIVES rather than first-match, and its body binds with `let*` over a
queue library whose names are not Python identifiers.

Three names carry a genuine underscore, `bfs_loop`, `bfs_all` and `$_1`, and
the factory attribute door maps every underscore to a hyphen, so all of them
take the bracket: `S.bfs_loop` would be the DIFFERENT head `bfs-loop`.
"""

import petta
from petta import S, V, equation, fn, if_

#: The blank, and one variable per board position.
BLANK = S["___"]
SLOTS = (V["_1"], V["_2"], V["_3"], V["_4"], V["_5"],
         V["_6"], V["_7"], V["_8"], V["_9"])

#: The two search heads, whose MeTTa names are underscored.
BFS_LOOP = S["bfs_loop"]
BFS_ALL = S["bfs_all"]

#: Source order is up, left, right, down wherever the move is legal.
DIRECTIONS = ((S.U, -3), (S.L, -1), (S.R, 1), (S.D, 3))

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 55047786, maximum 55047980
#: over 28 observations under `full-lane/218/workers=32`, so the re-pin owes
#: it an envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def _legal(blank, direction):
    """Whether ``direction`` stays on the three-by-three board from ``blank``."""
    row, column = divmod(blank, 3)
    return not (
        (direction == S.U and row == 0)
        or (direction == S.D and row == 2)
        or (direction == S.L and column == 0)
        or (direction == S.R and column == 2)
    )


def _moves():
    """Yield the source's twenty-four structured move equations in source order."""
    for blank in range(9):
        for direction, shift in DIRECTIONS:
            if not _legal(blank, direction):
                continue
            before = list(SLOTS)
            before[blank] = BLANK
            after = before.copy()
            destination = blank + shift
            after[blank], after[destination] = after[destination], after[blank]
            yield equation(S.move(tuple(before), direction)).to(tuple(after))


def twin(m):
    """State the moves and queue laws, then exhaust the reachable state graph."""
    m.add(*_moves())
    m.eval(fn["import!"](m, S.library(S["lib_datastructures"])))

    # The duplicate store is an ordinary space, and the Python variable IS its
    # binding, so it needs no name: the handle crosses a term position as
    # itself, which is what `add-unique-or-fail` receives.
    duplicates = petta.space()

    # `empty-queue` is a function, so the base case tests the queue against
    # what it produces rather than writing the call in the head, which would
    # be a pattern matched structurally.
    m += equation(BFS_LOOP(V.Q, V.N0)).to(
        if_(V.Q.eq(S["empty-queue"]()), V.N0, fn.empty())
    )
    m += equation(BFS_LOOP(V.Q, V.N0)).to(
        fn["let*"](  # rung: a let* over queue calls a compiled body cannot name (P14.4)
            (
                (V.Q1, fn.once(S.dequeue(V.S, V.Q))),
                (
                    V.Ln,
                    fn.collapse(  # rung: a collapse INSIDE a stored body, where list() is a Python read (P14.4)
                        fn["let*"](  # rung: the same let* (P14.4)
                            (
                                (V.Snew, S.move(V.S, V._)),
                                (V.receipt, S["add-unique-or-fail"](duplicates, V.Snew)),
                            ),
                            V.Snew,
                        )
                    ),
                ),
                (V.Q2, fn.foldl(S.enqueue, V.Ln, V.Q1)),
                (V.N1, V.N0 + 1),
            ),
            BFS_LOOP(V.Q2, V.N1),
        )
    )
    m += equation(BFS_ALL(V.Start)).to(
        fn["let*"](  # rung: the same let* (P14.4)
            (
                (V.receipt, S["add-unique-item-or-empty"](V.Start)),
                (V.Q1, S.enqueue(V.Start, S["empty-queue"]())),
            ),
            BFS_LOOP(V.Q1, 0),
        )
    )

    start = (BLANK, 1, 2, 3, 4, 5, 6, 7, 8)
    assert m.fn["bfs_all"](start).one() == 181441
