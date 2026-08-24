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
[measured again 2026-08-24; commit=WORKTREE]. So the counters come back through
`eval`, the term door.

A second thing does have to be forced: a call is LAZY, so `reach(S.a, V.y)` on
its own performs no engine work and the counters below it would all read zero
for that reason too. The example's own `(collapse (reach a $y))` is what forces
it, and `list(...)` is that collapse.

`reach` is written by `@m.define` and tabled by hand rather than by `@m.cache`,
whose `cache_info()` is this counter set under Python's own name, for the
reason tabling_space_write gives: the compiled `match(...)` names its space,
and caching refuses the two-argument form that would let it stay silent.
"""

from metta import S, V, match

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1

#: One call, one answer, nothing invalidated: what the first three claims all
#: expect, because the two writes between them are writes the subgoal never read.
UNTOUCHED = [
    S.tables(1), S.answers(1), S.complete_call(1),
    S.invalidated(0), S.reevaluated(0),
]


def twin(m):
    """Call a tabled reader once, then write around it and watch its counters."""
    m.fn["import!"](m, S.library(S["lib_tabling"]))

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
