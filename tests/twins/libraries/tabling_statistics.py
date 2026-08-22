"""The Python twin of examples/libraries/tabling_statistics.metta.

What the incremental machinery actually did, rather than what it is meant to do:
a write under a key the subgoal reads invalidates its table, a write under any
other key does not, and re-evaluation waits for the next call.

`reach` is written by `@m.define`, whose compiled `match(...)` names the space
as a literal and the pattern structurally. The counter tuples are Python tuples,
which is what a MeTTa expression of pairs already is.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 104258 to 105819, +1561 (+1.50%), by the P14
#: twin-style rewrite: reach's equation is now compiled from Python syntax by
#: @m.define instead of added as an already-built atom. Prior: ADDED
#: 2026-08-22 at 104258 by the wave-3 libraries baseline, which recorded no
#: cause.
BUDGET = 105819

def stats(tables, answers, complete, invalidated, reevaluated):
    """The five counters in the order `table-stats` answers them.

    Written once because the same shape is asserted five times below and
    only the numbers move.
    """
    return (
        (S.tables, tables),
        (S.answers, answers),
        (S["complete-call"], complete),
        (S.invalidated, invalidated),
        (S.reevaluated, reevaluated),
    )


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_tabling))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_tabling)))

    # !(add-atom &self (edge a b))
    yield m.eval(S["add-atom"](S["&self"], S.edge(S.a, S.b)))

    @m.define
    def reach(x, y):
        # (= (reach $x $y) (match &self (edge $x $y) $y))
        return match("&self", edge(x, y), y)  # noqa: F821  -- match reads its pattern as syntax: `edge` is the relation symbol and `x`, `y` are the parameters

    # !(tabled (reach $x $y))
    yield m.eval(S.tabled(S.reach(V.x, V.y)))

    # Nothing has happened yet: one call, one answer, no invalidation.
    # !(collapse (reach a $y))
    yield m.eval(S.collapse(S.reach(S.a, V.y)))
    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 0) (reevaluated 0)))
    yield m.eval(S.test(S["table-stats"](S.reach(V.x, V.y)), stats(1, 1, 1, 0, 0)))

    # A write under a key this subgoal does not read leaves the table alone.
    # !(add-atom &self (edge b d))
    yield m.eval(S["add-atom"](S["&self"], S.edge(S.b, S.d)))
    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 0) (reevaluated 0)))
    yield m.eval(S.test(S["table-stats"](S.reach(V.x, V.y)), stats(1, 1, 1, 0, 0)))

    # Nor does an atom with a different head in the same space.
    # !(add-atom &self (unrelated x y))
    yield m.eval(S["add-atom"](S["&self"], S.unrelated(S.x, S.y)))
    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 0) (reevaluated 0)))
    yield m.eval(S.test(S["table-stats"](S.reach(V.x, V.y)), stats(1, 1, 1, 0, 0)))

    # A write under a key it DOES read invalidates.
    # !(add-atom &self (edge a c))
    yield m.eval(S["add-atom"](S["&self"], S.edge(S.a, S.c)))
    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 1) (complete-call 1) (invalidated 1) (reevaluated 0)))
    yield m.eval(S.test(S["table-stats"](S.reach(V.x, V.y)), stats(1, 1, 1, 1, 0)))

    # Re-evaluation is on demand, so it takes a call.
    # !(test (sort-atom (collapse (reach a $y))) (b c))
    yield m.eval(
        S.test(S["sort-atom"](S.collapse(S.reach(S.a, V.y))), (S.b, S.c))
    )
    # !(test (table-stats (reach $x $y))
    #        ((tables 1) (answers 2) (complete-call 3) (invalidated 1) (reevaluated 1)))
    yield m.eval(S.test(S["table-stats"](S.reach(V.x, V.y)), stats(1, 2, 3, 1, 1)))
