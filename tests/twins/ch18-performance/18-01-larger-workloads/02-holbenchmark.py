"""Purpose: examples/ch18-performance/18-01-larger-workloads/02-holbenchmark.metta in Python: four million-step kernels.

A map over a million-long cons list, a fold over a nested one, a hundred
thousand applications of one function, and a polynomial sum. All four are
higher-order: the function being applied arrives as an argument and is called
through a variable.

Applying a parameter is Python's own call syntax now, `f(x)` lowering to
`($f $x)`, so `apply-many` and `poly` are ordinary functions under the
decorator, and so are the two list builders `range` and `deep-nest`, whose
empty-expression base case is Python's `()`.

`map-flat` and `fold-nested` stay at the container door for a blocker the
subset still has: each is two clauses that destructure in the HEAD, `()` and
`(cons $x $xs)`, and a compiled head pattern may only be a LITERAL default, so
a structural default is refused with "a default here is a head pattern, so it
must be a literal" [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT: two
`@m.define`s whose parameters carry the patterns, the way the equations do.
Residue P14.4.

The recursive list builders name every value before passing it to `cons`.
Rules-bundle bodies build the stored `let` terms; compiled bodies use plain
assignment, which lowers to `let*`.
[source: examples/ch18-performance/18-01-larger-workloads/02-holbenchmark.metta:1; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]

Each claim states its own branch allowance above the evaluator's 100000
default, which is a term because `m.limits` bounds inferences and time and not
stack depth (residue, P14.14). It is load-bearing for the compiled kernels
twice over: a compiled `if` wraps its condition in `py-truthy` and `==` lowers
to `py-eq`, so every level of these million-step recursions spends reductions
the original does not.
"""

from metta import S, V, equation, fn, if_

#: `(+ 1)`, the partially applied increment all four kernels are driven with. A
#: one-argument application has no operator spelling, so it is the tuple MeTTa
#: writes it as.
INC = S.add(1)

#: The branch allowance these million-step kernels state above the evaluator's
#: 100000 default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S.max_stack_depth(100_000_000),)


def twin(m):
    """Four higher-order kernels, each run to a million steps."""
    # A map that flattens as it goes, over a cons list built by counting down.
    m += equation(S.map_flat(V.f, ())).to(())  # rung: a compiled head pattern may only be a literal default
    m += equation(S.map_flat(V.f, S.cons(V.x, V.xs))).to(  # rung: as above
        S.let(  # rung: this rules body has no Python statement position for the required binding
            V.head,
            (V.f, V.x),
            S.let(  # rung: the recursive value must be named before cons receives its Expression-typed tail
                V.rest,
                S.map_flat(V.f, V.xs),
                S.cons(V.head, V.rest),
            ),
        )
    )

    # The define door applies rung 4's underscore map like every other door,
    # so a hyphenated MeTTa name needs nothing said twice. This one still
    # takes `name=`: `range` is a Python builtin, so the def carries rung 2's
    # trailing underscore, which the map would turn into a trailing hyphen.
    # `def range` would consume the gate's zero A-family headroom and report
    # `P0.13 suppression burn-down increased (observed, maximum): {'N': (37,
    # 35), 'A': (9, 8)}`; it would also redirect recursion to `py-range`.
    @m.define(name="range")
    def range_(n):
        if n == 0:
            return ()
        rest = range_(n - 1)
        return S.cons(n, rest)

    assert m.fn.with_pragma(DEEP, S.length(S.map_flat(INC, S.range(1_000_000)))) == [1_000_000]

    # A fold that recurses into nested expressions rather than over them.
    m += equation(S.fold_nested(V.f, V.init, ())).to(V.init)  # rung: as above
    m += equation(S.fold_nested(V.f, V.init, S.cons(V.x, V.xs))).to(  # rung: as above
        if_(S.is_expr(V.x),  # rung: the stored body of an equation the decorator cannot compile
            S.fold_nested(V.f, S.fold_nested(V.f, V.init, V.x), V.xs),
            S.fold_nested(V.f, (V.f, V.init, V.x), V.xs)))

    @m.define
    def deep_nest(n):
        if n == 0:
            return ()
        row = fn.range(50)
        rest = deep_nest(n - 1)
        return S.cons(row, rest)

    assert m.fn.with_pragma(
        DEEP, S.fold_nested(S.add, 0, S.deep_nest(20_000))
    ).one() == 25_500_000

    # A hundred thousand applications of one function to one value.
    @m.define
    def apply_many(f, n, x):
        if n == 0:
            return x
        return apply_many(f, n - 1, f(x))

    assert m.fn.with_pragma(DEEP, S.apply_many(INC, 100_000, 0)) == [100_000]

    # And a polynomial sum, which applies the parameter inside an addition.
    @m.define
    def poly(f, n):
        if n == 0:
            return 0
        return f(n) + poly(f, n - 1)

    assert m.fn.with_pragma(DEEP, S.poly(INC, 1_000_000)) == [500_001_500_000]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 189781420 to 189781298, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 189781298 to 189781263, on the release tree:
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
#: RE-PINNED 2026-08-25, 189781263 to 189781236, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 189781236 to 189786652 (+5416), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 189786652 to 189787371 (+719), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 189787371 to 189787307 (-64), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 189787307 to 189785398 (-1909), by the
#: specializer argument-walk fix this file's own chain named as the
#: follow-up. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 189785398
