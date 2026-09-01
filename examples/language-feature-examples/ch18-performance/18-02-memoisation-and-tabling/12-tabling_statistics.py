"""examples/ch18-performance/18-02-memoisation-and-tabling/12-tabling_statistics.metta in Python: what the incremental machinery DID.

A write to a space a tabled function reads invalidates its table, and the next
call re-evaluates it. Until these counters existed the guarantee was testable
only by its EFFECT, a fresh answer, which a table rebuilt from scratch produces
just as well. Six claims read the counters instead.

The finding worth keeping is the middle one: a write under a key this subgoal
does not read does not invalidate the table at all, and neither does an atom
with a different head in the same space. That is finer than the manual's own
summary, which says invalidation "is done at the level of tables. Notably
asserting a clause invalidates all affected tables" and closes with "Future
versions may implement a more fine grained approach". Reading the counters
BEFORE the next call is what shows it, because they are cumulative.

Each counter read uses `m.fn.table_stats(S.reach(V.x, V.y))`, the live call
door. A lazy pull runs on the held cursor's own SWI engine, so lib_tabling
declares shared SWI tables: the cursor, the source runner and the next cursor
all enter one answer trie and see one set of statistics. A private table here
answered the right values while disappearing with its cursor, leaving every
counter at zero at the next door.

A second thing does have to be forced: a call is LAZY, so `reach(S.a, V.y)` on
its own performs no engine work and the counters below it would all read zero
for that reason too. The example's own `(collapse (reach a $y))` is what forces
it, and `list(...)` is that collapse.

`reach` is written by `@m.define` and tabled through `lib.tabling`.
`lib_memo`'s `memoize-exact` uses the distinct exact-bag memo substrate, whose
`get-memoize-stats` reports memo entries and answer occurrences rather than SWI
table counters. That substrate is mode-directed tabling, which cannot be
declared `as shared` the way lib_tabling's tables above are: SWI then returns a
clause reference where `get_calls/3` expects a trie. So the two libraries differ
here on purpose, and the exact memo a lazy cursor fills stays that cursor's own
[measured 2026-08-31].
"""

from metta import S, V, lib, match

#: One call, one answer, nothing invalidated: what the first three claims all
#: expect, because the two writes between them are writes the subgoal never read.
UNTOUCHED = [
    S.tables(1), S.answers(1), S.complete_call(1),
    S.invalidated(0), S.reevaluated(0),
]


def twin(m):
    """Call a tabled reader once, then write around it and watch its counters."""
    m += lib.tabling

    m += S.edge(S.a, S.b)

    @m.define
    def reach(x, y):
        # (= (reach $x $y) (match &self (edge $x $y) $y))
        return match(m, S.edge(x, y), y)

    m.eval(S.tabled(S.reach(V.x, V.y)))
    call = S.reach(V.x, V.y)

    def stats():
        [counted] = m.fn.table_stats(call)
        return list(counted)

    # Nothing has happened yet: one call, one answer, no invalidation.
    # Iterating the view explicitly avoids list()'s separate cardinality hint:
    # this is one live call, and complete-call therefore reads one.
    assert list(iter(reach(S.a, V.y))) == [S.b]
    assert stats() == UNTOUCHED

    # A write under a key this subgoal does not read leaves the table alone.
    # Not "leaves the answers alone", which a rebuild would too: the table is
    # never invalidated at all.
    m += S.edge(S.b, S.d)
    assert stats() == UNTOUCHED

    # Nor does an atom with a different head in the same space.
    m += S.unrelated(S.x, S.y)
    assert stats() == UNTOUCHED

    # A write under a key it DOES read invalidates, and only that.
    m += S.edge(S.a, S.c)
    assert stats() == [
        S.tables(1), S.answers(1), S.complete_call(1),
        S.invalidated(1), S.reevaluated(0),
    ]

    # Re-evaluation is on demand, so it takes a call. reevaluated LOWER than
    # invalidated would be SWI deciding a dependency changed without changing
    # this table's answers, which is the incremental win rather than a rebuild.
    # The shared table has completed one original call and one re-evaluation.
    assert sorted(reach(S.a, V.y)) == [S.b, S.c]
    assert stats() == [
        S.tables(1), S.answers(2), S.complete_call(2),
        S.invalidated(1), S.reevaluated(1),
    ]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 59955 to 60158, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 60158 to 60187, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 60187 to 60162, on the release tree:
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
#: RE-PINNED 2026-08-25, 60162 to 60177, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 60177 to 67893 (+7716), at the
#: tabling-seam merge: declarations now table `as shared` (checked
#: readers `as (incremental, shared)`) so a live Answers cursor, the
#: source runner, and a later statistics call enter one answer trie
#: instead of a cursor-engine-private one, and calls route through
#: the declared dispatch ownership seam. The shared scope is what
#: SWI charges for cross-engine visibility; a private-when-unwatched
#: refinement is recorded as follow-up [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=tabling-seam merged tree with engine/reader.so; commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 67893 to 66441 (-1452), by the specializer
#: argument-walk fix.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 66441 to 71833 (+5392), one corpus pricing pass on the
#: merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 71833 to 71779 (-54), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 71779 to 71818 (+39), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 71818
