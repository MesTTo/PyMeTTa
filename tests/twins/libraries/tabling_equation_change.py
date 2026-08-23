"""examples/libraries/tabling_equation_change.metta in Python: a table goes stale, and knows.

A table answers from the equations compiled when it was built, so changing an
equation makes it stale. The engine's own change funnel drops the tables and the
next call rebuilds them, which is what the four claims here watch.

`pick` is written at the container door twice, and both reasons are recorded in
the residue table: its body is the bare lowercase symbol `one`, which a compiled
body resolves as a function rather than as data, and the second equation is a
stacked ALTERNATIVE, where a second `@m.define` under the same name replaces the
first. The write door takes both without ceremony, and the read door takes them
away again.

The third claim is sorted, because a TABLED function does not answer in clause
order: answers come out of the answer trie, and SWI says so plainly, "Tabling
effectively inverts the execution order for this case". Which order you get
depends on the trie's layout, so it moves when anything unrelated moves. The
answer SET is what tabling preserves; that is what this asserts.
"""

from petta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Table one equation, add a second, remove the first, watch the answers move."""
    m.eval(S["import!"](m, S.library(S["lib_tabling"])))

    m += equation(S.pick(V.x)).to(S.one)
    m.eval(S.tabled(S.pick(V.x)))

    pick = m.fn.pick
    assert pick(S.a) == [S.one]
    assert pick(S.a) == [S.one]

    # A second equation for the same function. Without invalidation the table
    # would keep answering [one].
    m += equation(S.pick(V.x)).to(S.two)
    assert sorted(pick(S.a), key=str) == [S.one, S.two]

    # Removing one again.
    m -= equation(S.pick(V.x)).to(S.one)
    assert pick(S.a) == [S.two]
