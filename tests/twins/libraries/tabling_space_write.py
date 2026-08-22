"""examples/libraries/tabling_space_write.metta in Python: a table over a space stays fresh.

The engine declares the storage predicates a tabled function reads incremental,
so SWI invalidates and re-evaluates the table on the next call by itself. Six
claims watch that happen across an add, a remove, and a conjunction that reads
two patterns.

`reach` is written by `@m.define`, whose compiled `match(...)` names its space
and reads its pattern as syntax, which is the source's own shape, and the table
is declared after it exactly as the example declares it. The `@m.cache` door
would say both in one act, and does in tabling_fib; it cannot here, because the
lane reads a string inside a `define`-decorated body as an equation's own
literal and does not yet know that `cache` compiles a body too.

`twohop` and `bypattern` stay at the container door, both already in the residue
table. A conjunction pattern `(, p q)` has no compiled spelling, because a
Python tuple of patterns builds `(p q)` and `,` is not a name Python can put in
head position; and `bypattern` takes its pattern as a PARAMETER, which the
compiled `match(...)` refuses because it reads its pattern as syntax. That
refusal is the last claim's subject, so it is asked for deliberately.

The last claim is compared with `alpha_eq` rather than against printed text. The
engine names the unresolved variable freshly, so the example's `$_0` is `$_558`
here and would be a third name tomorrow; alpha equality is the relation the law
already defines for exactly this.
"""

from petta import S, V, alpha_eq, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 86854 to 82560, -4294 (-4.94%), by the idiomatic
#: rewrite: six `test` wrappers, five `collapse`s, a `sort-atom` and a `repr`
#: left the engine for `assert`, `.all()`, `sorted` and `alpha_eq`; the two
#: tables and their invalidations still run there. Measured min-of-three with
#: the MORK backend linked into this worktree, which the earlier figure may
#: not have been. Prior: 86854 was the last figure for the generator twin
#: that yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 82560


def twin(m):
    """Table two readers of a space, then write to the space under them."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_tabling)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += S.edge(S.a, S.b)
    m += S.edge(S.b, S.c)

    @m.define
    def reach(x, y):
        return match("&self", edge(x, y), y)  # noqa: F821  -- match reads its pattern as syntax: `edge` is the relation symbol and `x`, `y` are the parameters

    m += equation(S.twohop(V.x, V.z)).to(S.match(S["&self"], S[","](S.edge(V.x, V.y), S.edge(V.y, V.z)), V.z))  # rung: an equation is DATA, so it carries its space by name; and the conjunction `,` has no Python head spelling, which is why this one is built rather than compiled

    m.eval(S.tabled(S.reach(V.x, V.y)))
    m.eval(S.tabled(S.twohop(V.x, V.z)))

    assert reach(S.a, V.y) == [S.b]
    assert m.fn("twohop").all(S.a, V.z) == [S.c]

    # Adding an atom the table read. Sorted for the same reason as
    # tabling_equation_change: a tabled function answers from its trie, not in
    # clause order, so only the answer SET is stable.
    m += S.edge(S.a, S.c)
    assert sorted(reach(S.a, V.y), key=str) == [S.b, S.c]

    # Removing one.
    m -= S.edge(S.a, S.b)
    assert reach(S.a, V.y) == [S.c]

    # A conjunction reads each of its patterns, so it tracks them all.
    m += S.edge(S.c, S.d)
    assert m.fn("twohop").all(S.b, V.z) == [S.d]

    # A read the engine cannot resolve to one space predicate is refused rather
    # than tabled without the guarantee.
    m += equation(S.bypattern(V.p)).to(S.match(S["&self"], V.p, V.p))  # rung: as above, and the pattern is a PARAMETER, which is the refusal this claim asks for
    [refused] = m.eval(S.catch(S.tabled(S.bypattern(V.p))))
    assert alpha_eq(refused, S.Error(S.petta_tabling_unresolved_read(S.match, V.p), S.none))
