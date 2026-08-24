"""examples/libraries/tabling_equation_change.metta in Python: a table goes stale, and knows.

A table answers from the equations compiled when it was built, so changing an
equation makes it stale. The engine's own change funnel drops the tables and the
next call rebuilds them, which is what the four claims here watch.

The first clause is an ordinary compiled definition whose body is the lowercase
symbol `one`, which the `S` factory says inside a body as readily as outside
one. The SECOND clause cannot join it: a second decoration of the same head
replaces the first rather than stacking, so the alternative is written at the
container door, and the removal takes it away from there too. That is the
residue entry this file carries, and it is the shape the example needs, because
the program removes one of the two atoms later.

The third claim is sorted, because a TABLED function does not answer in clause
order: answers come out of the answer trie, and SWI says so plainly, "Tabling
effectively inverts the execution order for this case". Which order you get
depends on the trie's layout, so it moves when anything unrelated moves. The
answer SET is what tabling preserves; that is what this asserts. Sorting takes
no key, because atoms carry the engine's standard order of terms.
"""

from metta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1


def twin(m):
    """Table one equation, add a second, remove the first, watch the answers move."""
    m.fn["import!"](m, S.library(S["lib_tabling"]))

    @m.define
    def pick(x):  # noqa: ARG001  -- the head variable is the example's own, and its body ignores it
        # (= (pick $x) one)
        return S.one

    m.eval(S.tabled(S.pick(V.x)))

    assert pick(S.a) == [S.one]
    assert pick(S.a) == [S.one]

    # A second equation for the same function. Without invalidation the table
    # would keep answering [one].
    m += equation(S.pick(V.x)).to(S.two)
    assert sorted(pick(S.a)) == [S.one, S.two]

    # Removing one again.
    m -= equation(S.pick(V.x)).to(S.one)
    assert pick(S.a) == [S.two]
