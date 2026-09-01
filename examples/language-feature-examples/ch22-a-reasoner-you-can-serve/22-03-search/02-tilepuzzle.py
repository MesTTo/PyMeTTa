"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-03-search/02-tilepuzzle.metta in Python: the eight-tile state graph.

Twenty-four move equations say where the blank may go from each of the nine
positions, and a breadth-first loop walks the reachable states, refusing a
duplicate, until the queue empties. The claim is the count it reaches, 181441.

The moves are one shape repeated, so a pair of loops writes them: the blank's
position and the direction are the loop variables, and the row is the eight
placeholders with the blank swapped into place. The example writes all
twenty-four out; here the shape is stated once and `@m.rules` lands the
twenty-four equations the loops supply, which is the door for a head that
destructures a nine-cell board.

The search is a `@m.rules` bundle and two compiled functions. `bfs_loop` must
stay the example's TWO coexisting clauses, and that is measured rather than
assumed: folding them into one `if`/`else` compiles, answers correctly for a
few thousand states, and then raises StackOverflow at 16,665 of the 181,441,
because the recursive call moves out of the let* chain's tail position into
`if`'s third argument (friction, P14.4). The example inlines a `let*` under the
`collapse`, and the twin NAMES that intermediate as `fresh-neighbour` instead,
which is a compiled function whose statements ARE that let*.

Three names carry a genuine underscore, `bfs_loop`, `bfs_all` and `$_1`. The
factory attribute door maps every underscore to a hyphen, so the variables take
the bracket and the two heads are given explicitly with `name=`: the implicit
name would install `bfs-loop`, a different head from the one the example makes
matchable.
"""

import metta
from metta import S, V, equation, if_, lib

#: The search head, whose MeTTa name carries a genuine underscore, so the
#: attribute door cannot say it: rung 4's map would make it `bfs-loop`.
BFS_LOOP = S["bfs_loop"]

#: The blank, and one variable per board position.
BLANK = S["___"]
SLOTS = (V["_1"], V["_2"], V["_3"], V["_4"], V["_5"],
         V["_6"], V["_7"], V["_8"], V["_9"])

#: Source order is up, left, right, down wherever the move is legal.
DIRECTIONS = ((S.U, -3), (S.L, -1), (S.R, 1), (S.D, 3))


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

    @m.rules
    def board():
        """Twenty-four move equations, the example's own shape written once.

        (= (move (___ $_2 $_3 $_4 $_5 $_6 $_7 $_8 $_9) R)
           ($_2 ___ $_3 $_4 $_5 $_6 $_7 $_8 $_9)), and twenty-three more.
        """
        yield from _moves()

    # !(import! &self (library lib_datastructures))
    m += lib.datastructures

    # The duplicate store is an ordinary space, and the Python variable IS its
    # binding, so it needs no name: the handle crosses a term position as
    # itself, which is what `add-unique-or-fail` receives.
    duplicates = metta.space()

    @m.define
    def fresh_neighbour(state):
        """One unseen state per legal move; the example inlines this let*."""
        moved = S.move(state, V._)
        _receipt = S.add_unique_or_fail(duplicates, moved)
        return moved

    @m.rules
    def search(queue, seen, state, rest, neighbours, grown):  # noqa: PLR0917  -- a bundle's parameters ARE its equations' variables, not a call signature
        """The two coexisting clauses: stop on an empty queue, or take one."""
        # `empty-queue` is a function, so the base case tests the queue against
        # what it produces rather than writing the call in the head, which
        # would be a pattern matched structurally.
        # (= (bfs_loop $Q $N0) (if (== $Q (empty-queue)) $N0 (empty)))
        yield equation(BFS_LOOP(queue, seen)).to(
            if_(S.eq(queue, S.empty_queue()), seen, S.empty())
        )
        # (= (bfs_loop $Q $N0)
        #    (let* (($Q1 (once (dequeue $S $Q)))
        #           ($Ln (collapse (let* (($Snew (move $S $_)) ...) $Snew)))
        #           ($Q2 (foldl enqueue $Ln $Q1))
        #           ($N1 (+ $N0 1)))
        #          (bfs_loop $Q2 $N1)))
        yield equation(BFS_LOOP(queue, seen)).to(
            S["let*"](  # rung: a stored let* whose bindings are queue calls, and whose TAIL is the recursion this search needs (P14.4)
                (
                    (rest, S.once(S.dequeue(state, queue))),
                    (neighbours, S.collapse(S.fresh_neighbour(state))),  # rung: `collapse` is list() (P14.4)
                    (grown, S.foldl(S.enqueue, neighbours, rest)),
                ),
                BFS_LOOP(grown, seen + 1),
            )
        )

    @m.define(name="bfs_all")
    def bfs_all(start):
        """Seed the duplicate store and the queue, then run the loop."""
        # (= (bfs_all $Start)
        #    (let* (($Pt (add-unique-item-or-empty $Start))
        #           ($Q1 (enqueue $Start (empty-queue))))
        #         (bfs_loop $Q1 0)))
        _receipt = S.add_unique_item_or_empty(start)
        queue = S.enqueue(start, S.empty_queue())
        return S["bfs_loop"](queue, 0)

    # !(test (let $x (bfs_all (___ 1 2 3 4 5 6 7 8)) $x) 181441)
    assert bfs_all((BLANK, 1, 2, 3, 4, 5, 6, 7, 8)) == [181441]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 55047786, maximum 55047980
#: over 28 observations under `full-lane/218/workers=32`, so the re-pin owes
#: it an envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 197554387 to 197554425, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 197554425 to 197554239, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 197554239 to 197554208, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 197554208 to 197554165, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 197554165 to 197556044 (+1879), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 197556044 to 197555920 (-124), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 197555920 to 197555874 (-46), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 197555874 to 197554482 (-1392), by the
#: specializer argument-walk fix this file's own chain named as the
#: follow-up. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 197554482 to 30041145 (-167513337), one corpus pricing
#: pass on the merged tree for the 2026-08-27..09-01 engine span
#: (8e75816d..f0744f86), whose four mechanisms are decomposed per lane in
#: benchmarks/baseline.json and ai-parametricity-audit.md passes 10-16: the
#: seam-offer routing and its one-wrap fold (net +8 inferences per evaluation),
#: the strict-scope removal leaving the eval path, the doubling cursor chunk
#: (~3 engine-side inferences per answer replacing per-answer crossings; drains
#: halve on CPU), and the aligned-path work; thirteen twins additionally carry
#: the idiom sweep's local deltas tabulated in the twin-idioms notes, none
#: above 347 [measured 2026-09-01: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 30041145 to 30041072 (-73), the subtract-atom
#: primitive and Counter's grain for -=: a new engine head shifts every twin's
#: load structure, the removal doors changed meaning where a twin spells one,
#: and the quad twin stopped being a different program [measured 2026-09-01:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 30041072
