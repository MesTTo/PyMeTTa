"""examples/libraries/tabling_space_write.metta in Python: a table over a space stays fresh.

The engine declares the storage predicates a tabled function reads incremental,
so SWI invalidates and re-evaluates the table on the next call by itself. Six
claims watch that happen across an add, a remove, and a conjunction that reads
two patterns.

`reach` is written by `@m.define`, whose compiled `match(...)` names its space
and reads its pattern as syntax, which is the source's own shape, and the table
is declared after it exactly as the example declares it. The `@m.cache` door
would say both in one act, and does in tabling_fib; it cannot here, because the
compiled `match(...)` requires its space as a string constant while caching
refuses the two-argument form that lowers to `(context-space)`.

`twohop` and `bypattern` stay at the container door, both already in the residue
table. A conjunction pattern `(, p q)` has no compiled spelling, because a
Python tuple of patterns builds `(p q)` and `,` is not a name Python can put in
head position; and `bypattern` takes its pattern as a PARAMETER, which the
compiled `match(...)` refuses because it reads its pattern as syntax. That
refusal is the last claim's subject, so it is asked for deliberately.

DEFECT, and the two doors say it between them. `reach` has a Python name and
its claims ought to read `reach(S.a, V.y).y == [S.b]`, the projection the
answers family rules; `twohop` has none, so it is called through the space's
own function namespace and `.z` is that same projection. Only the second one
works: a Python-named call LOSES its caller-variable columns inside a
`space.stats()` scope, which is the scope every twin runs in, so `reach`'s
answers are compared directly and `twohop`'s are projected. Outside a stats
scope both project; that difference is the defect.

The refusal at the end comes back through `eval`, because its `$p` is an
argument the answer does not depend on and the answer view would report a
binding row for it.

The last claim is compared with `alpha_eq` rather than against printed text. The
engine names the unresolved variable freshly, so the example's `$_0` is `$_558`
here and would be a third name tomorrow; alpha equality is the relation the law
already defines for exactly this, and it belongs to the atom. The refusal's
own head keeps the bracket: `petta_tabling_unresolved_read` really has
underscores, and the attribute door maps every underscore to a hyphen.
"""

from petta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Table two readers of a space, then write to the space under them."""
    m.eval(S["import!"](m, S.library(S["lib_tabling"])))

    m += S.edge(S.a, S.b)
    m += S.edge(S.b, S.c)

    @m.define
    def reach(x, y):
        return match("&self", edge(x, y), y)  # noqa: F821  -- match reads its pattern as syntax: `edge` is the relation symbol and `x`, `y` are the parameters

    m += equation(S.twohop(V.x, V.z)).to(S.match(m, S[","](S.edge(V.x, V.y), S.edge(V.y, V.z)), V.z))  # rung: the conjunction `,` has no Python head spelling, which is why this equation is built rather than compiled

    m.eval(S.tabled(S.reach(V.x, V.y)))
    m.eval(S.tabled(S.twohop(V.x, V.z)))

    twohop = m.fn.twohop
    assert reach(S.a, V.y) == [S.b]
    assert twohop(S.a, V.z).z == [S.c]

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
    assert twohop(S.b, V.z).z == [S.d]

    # A read the engine cannot resolve to one space predicate is refused rather
    # than tabled without the guarantee.
    m += equation(S.bypattern(V.p)).to(S.match(m, V.p, V.p))  # rung: the pattern is a PARAMETER, which is the refusal this claim asks for
    [refused] = m.eval(S.catch(S.tabled(S.bypattern(V.p))))
    assert refused.alpha_eq(S.Error(S["petta_tabling_unresolved_read"](S.match, V.p), S.none))
