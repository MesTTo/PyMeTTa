"""examples/ch18-performance/18-02-memoisation-and-tabling/11-tabling_space_write.metta in Python: a table over a space stays fresh.

The engine declares the storage predicates a tabled function reads incremental,
so SWI invalidates and re-evaluates the table on the next call by itself. Six
claims watch that happen across an add, a remove, and a conjunction that reads
two patterns.

`reach` and `bypattern` are ordinary compiled definitions. Inside a body the
expression-position `match(space, pattern, template)` is read as syntax and
emits the instruction, so `match(m, S.edge(x, y), y)` stores exactly the
example's `(match &self (edge $x $y) $y)`, and `match(m, p, p)` passes its
pattern straight through as a PARAMETER. SWI tabling stays an explicit
`lib.tabling` declaration because `@m.cache` has the distinct exact-bag memo
law.

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
own head keeps the bracket: `metta_tabling_unresolved_read` really has
underscores, and the attribute door maps every underscore to a hyphen.
"""

from metta import S, V, equation, lib, match


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
    assert refused.alpha_eq(S.Error(S["metta_tabling_unresolved_read"](S.match, V.p), S.none))


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
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
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
#: RE-PINNED 2026-08-25, 63351 to 63372, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 63372 to 59111 (-4261), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: The parallel async-scheduler branch's own history of this pin,
#: kept for the record; the merged value follows below:
#: RE-PINNED 2026-08-26, 63372 to 63560, on the completed async-scheduler
#: tree. The six incremental-table claims and their answers are unchanged;
#: the movement is the compiled QLF and predicate-index layout after adding
#: scheduler, callback, and lifecycle clauses. Three fresh serial processes
#: agreed at the new cost
#: [measured: 63560 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch18-performance/18-02-memoisation-and-tabling/11-tabling_space_write.metta; fixture=p14-audit-async with
#: engine/reader.so; commit=39092863ae34184a9f955f185ff57c1ff177ec40].
#: RE-PINNED 2026-08-26, 59111 to 59176 (+65), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 59176 to 70224 (+11048), at the
#: tabling-seam merge: declarations now table `as shared` (checked
#: readers `as (incremental, shared)`) so a live Answers cursor, the
#: source runner, and a later statistics call enter one answer trie
#: instead of a cursor-engine-private one, and calls route through
#: the declared dispatch ownership seam. The shared scope is what
#: SWI charges for cross-engine visibility; a private-when-unwatched
#: refinement is recorded as follow-up [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=tabling-seam merged tree with engine/reader.so; commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 70224 to 68759 (-1465), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 68759
