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

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 77656 to 74824, -2832 (-3.65%), by the idiomatic
#: rewrite: four `test` wrappers, two `collapse`s and a `sort-atom` left the
#: engine for `assert`, `.all()` and `sorted`; the table and its two
#: invalidations still run there. Measured min-of-three with the MORK backend
#: linked into this worktree, which the earlier figure may not have been.
#: Prior: 77656 was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 74824


def twin(m):
    """Table one equation, add a second, remove the first, watch the answers move."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_tabling)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += equation(S.pick(V.x)).to(S.one)
    m.eval(S.tabled(S.pick(V.x)))

    pick = m.fn("pick")
    assert pick.all(S.a) == [S.one]
    assert pick.all(S.a) == [S.one]

    # A second equation for the same function. Without invalidation the table
    # would keep answering [one].
    m += equation(S.pick(V.x)).to(S.two)
    assert sorted(pick.all(S.a), key=str) == [S.one, S.two]

    # Removing one again.
    m -= equation(S.pick(V.x)).to(S.one)
    assert pick.all(S.a) == [S.two]
