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

`reach` is written by `@m.define` and tabled by hand rather than by `@m.cache`,
whose `cache_info()` is this counter set under Python's own name, for the reason
tabling_space_write gives: the lane reads a string inside a `define`-decorated
body as an equation's literal and does not yet know that `cache` compiles a body
too, and the compiled `match(...)` has to name its space.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 105819 to 99288, -6531 (-6.17%), by the idiomatic
#: rewrite: six `test` wrappers and two `collapse`s left the engine, and
#: reading the counters is now a list comparison in Python rather than a term
#: compared by `test`. Measured min-of-three with the MORK backend linked
#: into this worktree, which the earlier figure may not have been. Prior:
#: 105819 was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 99288

#: One call, one answer, nothing invalidated: what the first three claims all
#: expect, because the two writes between them are writes the subgoal never read.
UNTOUCHED = [
    S.tables(1), S.answers(1), S["complete-call"](1),
    S.invalidated(0), S.reevaluated(0),
]


def twin(m):
    """Call a tabled reader once, then write around it and watch its counters."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_tabling)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += S.edge(S.a, S.b)

    @m.define
    def reach(x, y):
        return match("&self", edge(x, y), y)  # noqa: F821  -- match reads its pattern as syntax: `edge` is the relation symbol and `x`, `y` are the parameters

    m.eval(S.tabled(S.reach(V.x, V.y)))
    counters = m.fn("table-stats")

    # Nothing has happened yet: one call, one answer, no invalidation.
    reach(S.a, V.y)
    assert list(counters(S.reach(V.x, V.y))) == UNTOUCHED

    # A write under a key this subgoal does not read leaves the table alone.
    # Not "leaves the answers alone", which a rebuild would too: the table is
    # never invalidated at all.
    m += S.edge(S.b, S.d)
    assert list(counters(S.reach(V.x, V.y))) == UNTOUCHED

    # Nor does an atom with a different head in the same space.
    m += S.unrelated(S.x, S.y)
    assert list(counters(S.reach(V.x, V.y))) == UNTOUCHED

    # A write under a key it DOES read invalidates, and only that.
    m += S.edge(S.a, S.c)
    assert list(counters(S.reach(V.x, V.y))) == [
        S.tables(1), S.answers(1), S["complete-call"](1),
        S.invalidated(1), S.reevaluated(0),
    ]

    # Re-evaluation is on demand, so it takes a call. reevaluated LOWER than
    # invalidated would be SWI deciding a dependency changed without changing
    # this table's answers, which is the incremental win rather than a rebuild.
    assert sorted(reach(S.a, V.y), key=str) == [S.b, S.c]
    assert list(counters(S.reach(V.x, V.y))) == [
        S.tables(1), S.answers(2), S["complete-call"](3),
        S.invalidated(1), S.reevaluated(1),
    ]
