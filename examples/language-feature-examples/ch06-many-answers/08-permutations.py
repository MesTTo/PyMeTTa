"""Purpose: examples/ch06-many-answers/08-permutations.metta in Python: 9! by joining inequalities.

Three kinds of knowledge, each written the way Python already writes it.

The 56 inequality FACTS are every ordered pair of distinct positions, so they
are a nested `for` and a tuple: MeTTa's `(1 != 2)` is Python's `(1, NE, 2)`, and
anything that yields tuples is a fact stream.

The nine `E` facts move one hole through the nine slots of a row, so the hole's
position is the loop variable and the row is built by slicing the eight
placeholders around it.

The 29-conjunct join is `space.match(...)`, whose varargs ARE the conjunction,
and the answer is a row per solution, so the example's
`(length (collapse (match ...)))` is `len()` over the view the door already
answers, counted through the engine rather than pulled into Python. The
conjuncts keep the original's triangular layout, which is this file's
documentation of the constraint graph.
"""

from metta import S, V

#: The inequality head, the hole, and the eight placeholder variables every
#: fact and the query share.
#:
#: The example's names are `$_1` and `___`, both of which carry a genuine
#: underscore: the factory attribute door maps every underscore to a hyphen,
#: so `V._1` would be `$-1` and these take the bracket, which is what rung 5
#: is for. `!=` has an operator word, so the head is `S.ne`.
NE = S.ne
HOLE = S["___"]
SLOT = (V["_1"], V["_2"], V["_3"], V["_4"], V["_5"], V["_6"], V["_7"], V["_8"])


def ne(left, right):
    """`($_left != $_right)`, one conjunct of the constraint graph."""
    return (SLOT[left - 1], NE, SLOT[right - 1])


def twin(m):
    """State 65 facts, then join them into every permutation of nine."""
    # Every ordered pair of distinct positions, the original's four rows of
    # fourteen.
    # (1 != 2) (1 != 3) ... (8 != 7)
    m += [
        (left, NE, right)
        for left in range(1, 9)
        for right in range(1, 9)
        if left != right
    ]

    # One hole, moved through the nine slots of a row.
    # (E $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8 1 (___ $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8))
    # ... and eight more, the hole one place further along each time
    m += [
        S.E(*SLOT, slot, (*SLOT[: slot - 1], HOLE, *SLOT[slot - 1:]))
        for slot in range(1, 10)
    ]

    # The triangular constraint graph: each new position differs from every
    # earlier one, and the ninth slot is where the hole may sit.
    # !(test (length (collapse (match &self (, ($_1 != $_2) ... ) (state1 $state))))
    #        362880)
    conjuncts = (
        ne(1, 2),
        ne(2, 3), ne(3, 1),
        ne(3, 4), ne(4, 2), ne(4, 1),
        ne(4, 5), ne(5, 3), ne(5, 2), ne(5, 1),
        ne(5, 6), ne(6, 4), ne(6, 3), ne(6, 2), ne(6, 1),
        ne(6, 7), ne(7, 5), ne(7, 4), ne(7, 3), ne(7, 2), ne(7, 1),
        ne(7, 8), ne(8, 6), ne(8, 5), ne(8, 4), ne(8, 3), ne(8, 2), ne(8, 1),
        S.E(*SLOT, V.x, V.state),
    )
    assert len(m.match(*conjuncts)) == 362880


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 50760321 to 50760325, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 50760325 to 50760323, on the release tree:
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
#: RE-PINNED 2026-08-26, 50760323 to 27172201 (-23588122): c7468b27 routed the
#: algebra carriers' counting through the algebra tower and this twin's
#: enumeration got 1.87x cheaper; the improvement was never re-pinned
#: when it landed [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 27172201 to 23885278 (-3286923), the compiled-language
#: batch: try/raise on the error algebra, dict-space literals with lib_dict
#: auto-import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 23885278 to 23886193 (+915), generic Python operators
#: now dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-06, 23886193 to 23886199 (+6), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-08, 23886199 to 23886354 (+155), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 23886354 to 23885402 (-952), the module boundary
#: merged with trunk's later packages (refactor/engine-and-libraries-as-modules
#: at b64291369): every space now resolves through one more chain link, prelude
#: -> metta_engine -> user, the engine's measured export list is imported into
#: the host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 23886199 to 23885246 (-953), The typed host door
#: catalog is published before user code. Its declarations change catalog
#: lookup indexes; generated public names bind directly to their existing
#: bodies [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 23885246 to 23885402 (+156), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-08, 23885402 to 23885792 (+390), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
BUDGET = 23885792
