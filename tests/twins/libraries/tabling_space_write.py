"""examples/libraries/tabling_space_write.metta in Python: a table over a space stays fresh.

The engine declares the storage predicates a tabled function reads incremental,
so SWI invalidates and re-evaluates the table on the next call by itself. Six
claims watch that happen across an add, a remove, and a conjunction that reads
two patterns.

`reach` and `bypattern` are ordinary compiled definitions. Inside a body the
expression-position `match(space, pattern, template)` is read as syntax and
emits the instruction, so `match(m, S.edge(x, y), y)` stores exactly the
example's `(match &self (edge $x $y) $y)`, and `match(m, p, p)` passes its
pattern straight through as a PARAMETER. The `@m.cache` door would declare the
table in the same act, and does in tabling_fib; it cannot here, because caching
refuses the two-argument form that lowers to `(context-space)` and this file's
readers name their space.

`twohop` stays at the container door, which is the residue entry this file
carries. A conjunction pattern `(, p q)` has no compiled spelling: the receiver
door takes a conjunction as varargs, `space.match(p, q)`, while the compiled
`match()` takes only a pattern and a template, with the space optional.

Both readers are projected the same way. `reach` and `bypattern` have Python
names and their claims read `reach(S.a, V.y).y == [S.b]`, the projection the
answers family rules; `twohop` has none, so it is called through the space's
own function namespace and `.z` is that same projection. A call keeps its
caller-variable columns inside a `space.stats()` scope, which is the scope
every twin runs in, so the two doors agree.

The refusal at the end comes back through `eval`, because its `$p` is an
argument the answer does not depend on.

The last claim is compared with `alpha_eq` rather than against printed text. The
engine names the unresolved variable freshly, so the example's `$_0` is `$_558`
here and would be a third name tomorrow; alpha equality is the relation the law
already defines for exactly this, and it belongs to the atom. The refusal's
own head keeps the bracket: `petta_tabling_unresolved_read` really has
underscores, and the attribute door maps every underscore to a hyphen.
"""

from metta import S, V, equation, lib, match

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 63295 to 63445, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 63445 to 63694, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 63694 to 63351, on the release tree:
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
BUDGET = 63351


def twin(m):
    """Table two readers of a space, then write to the space under them."""
    m += lib.tabling

    m += S.edge(S.a, S.b)
    m += S.edge(S.b, S.c)

    @m.define
    def reach(x, y):
        # (= (reach $x $y) (match &self (edge $x $y) $y))
        return match(m, S.edge(x, y), y)

    m += equation(S.twohop(V.x, V.z)).to(S.match(m, S[","](S.edge(V.x, V.y), S.edge(V.y, V.z)), V.z))  # rung: the conjunction `,` has no compiled match() spelling, which is why this equation is built rather than compiled

    m.eval(S.tabled(S.reach(V.x, V.y)))
    m.eval(S.tabled(S.twohop(V.x, V.z)))

    twohop = m.fn.twohop
    assert reach(S.a, V.y).y == [S.b]
    assert twohop(S.a, V.z).z == [S.c]

    # Adding an atom the table read. Sorted for the same reason as
    # tabling_equation_change: a tabled function answers from its trie, not in
    # clause order, so only the answer SET is stable.
    m += S.edge(S.a, S.c)
    assert sorted(reach(S.a, V.y).y) == [S.b, S.c]

    # Removing one.
    m -= S.edge(S.a, S.b)
    assert reach(S.a, V.y).y == [S.c]

    # A conjunction reads each of its patterns, so it tracks them all.
    m += S.edge(S.c, S.d)
    assert twohop(S.b, V.z).z == [S.d]

    # A read the engine cannot resolve to one space predicate is refused rather
    # than tabled without the guarantee.
    @m.define
    def bypattern(p):
        # (= (bypattern $p) (match &self $p $p))
        return match(m, p, p)

    [refused] = m.eval(S.catch(S.tabled(S.bypattern(V.p))))
    assert refused.alpha_eq(S.Error(S["petta_tabling_unresolved_read"](S.match, V.p), S.none))
