"""Purpose: express the tile-puzzle example through the Python surface.

The twin includes all twenty-four moves and the breadth-first queue search.

Guarantees:
  - the generated move equations cover every legal blank swap and the search
    exhausts the eight-tile state graph at the source count of 181441 [measured: twin completed; command=PYTHONPATH=bindings/python python -c "import runpy; from petta import MeTTa; runpy.run_path('bindings/python/tests/twins/reasoning/tilepuzzle.py') ['twin'](MeTTa(petta_path='.'))"; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V, equation, sym

#: Move heads destructure a nine-cell board, bfs_loop has two identical heads,
#: and its queue body carries let bindings over named spaces. Those are laws at
#: the current rules/term door rather than flat compiled Python functions.
RUNG = "structured move heads and same-head breadth-first laws use the rules and term doors"

#: The blank is a source symbol Python reserves from the factory attribute door.
BLANK = sym("___")

#: One source variable per board position. The blank replaces one in each rule.
SLOTS = (V._1, V._2, V._3, V._4, V._5, V._6, V._7, V._8, V._9)

#: Source order is up, left, right, down wherever the move is legal.
DIRECTIONS = ((S.U, -3), (S.L, -1), (S.R, 1), (S.D, 3))

#: The import target and duplicate-detection space required by current terms.
SELF = S["&self"]
DUPLICATES = S["&dup"]

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 55047786..55047980 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
BUDGET = {
    "minimum": 55047786,
    "maximum": 55047980,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


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
    m.eval(S["import!"](SELF, S.library(S.lib_datastructures)))

    m += equation(S.bfs_loop(V.Q, V.N0)).to(
        S["if"](V.Q.eq(S["empty-queue"]()), V.N0, S.empty())
    )
    m += equation(S.bfs_loop(V.Q, V.N0)).to(
        S["let*"](
            (
                (V.Q1, S.once(S.dequeue(V.S, V.Q))),
                (
                    V.Ln,
                    S.collapse(
                        S["let*"](
                            (
                                (V.Snew, S.move(V.S, V._)),
                                (
                                    V.receipt,
                                    S["add-unique-or-fail"](DUPLICATES, V.Snew),
                                ),
                            ),
                            V.Snew,
                        )
                    ),
                ),
                (V.Q2, S.foldl(S.enqueue, V.Ln, V.Q1)),
                (V.N1, V.N0 + 1),
            ),
            S.bfs_loop(V.Q2, V.N1),
        )
    )
    m += equation(S.bfs_all(V.Start)).to(
        S["let*"](
            (
                (V.receipt, S["add-unique-item-or-empty"](V.Start)),
                (V.Q1, S.enqueue(V.Start, S["empty-queue"]())),
            ),
            S.bfs_loop(V.Q1, 0),
        )
    )

    start = (BLANK, 1, 2, 3, 4, 5, 6, 7, 8)
    assert m.one(S.let(V.x, S.bfs_all(start), V.x)) == 181441
