"""examples/libraries/tabling_statistics.metta in Python: what the incremental machinery DID.

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

DEFECT, and it decides how the counters are read. Each of the six reads ought
to be `m.fn.table_stats(S.reach(V.x, V.y))`, the call door. Every LAZY door,
the function namespace and `m.answers` alike, answers all five counters as
zero where `m.eval` answers `(tables 1) (answers 1) (complete-call 1)` for the
same subgoal, inside a `m.stats()` scope and outside one: a lazy pull runs on
the held cursor's own SWI engine and SWI's tabling statistics are per-engine
[measured again 2026-08-24; commit=1e264c186c531e69acde5ad03ff6a79210626df4]. So the counters come back through
`eval`, the term door.

A second thing does have to be forced: a call is LAZY, so `reach(S.a, V.y)` on
its own performs no engine work and the counters below it would all read zero
for that reason too. The example's own `(collapse (reach a $y))` is what forces
it, and `list(...)` is that collapse.

`reach` is written by `@m.define` and tabled through `lib.tabling`. `@m.cache`
uses the distinct exact-bag memo substrate, whose `cache_info()` reports memo
entries and answer occurrences rather than SWI table counters.
"""

from metta import S, V, lib, match

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
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
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
BUDGET = 60177

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
    subgoal = S.table_stats(S.reach(V.x, V.y))

    # Nothing has happened yet: one call, one answer, no invalidation.
    assert list(reach(S.a, V.y)) == [S.b]
    [counted] = m.eval(subgoal)
    assert list(counted) == UNTOUCHED

    # A write under a key this subgoal does not read leaves the table alone.
    # Not "leaves the answers alone", which a rebuild would too: the table is
    # never invalidated at all.
    m += S.edge(S.b, S.d)
    [counted] = m.eval(subgoal)
    assert list(counted) == UNTOUCHED

    # Nor does an atom with a different head in the same space.
    m += S.unrelated(S.x, S.y)
    [counted] = m.eval(subgoal)
    assert list(counted) == UNTOUCHED

    # A write under a key it DOES read invalidates, and only that.
    m += S.edge(S.a, S.c)
    [counted] = m.eval(subgoal)
    assert list(counted) == [
        S.tables(1), S.answers(1), S.complete_call(1),
        S.invalidated(1), S.reevaluated(0),
    ]

    # Re-evaluation is on demand, so it takes a call. reevaluated LOWER than
    # invalidated would be SWI deciding a dependency changed without changing
    # this table's answers, which is the incremental win rather than a rebuild.
    assert sorted(reach(S.a, V.y)) == [S.b, S.c]
    [counted] = m.eval(subgoal)
    assert list(counted) == [
        S.tables(1), S.answers(2), S.complete_call(3),
        S.invalidated(1), S.reevaluated(1),
    ]
