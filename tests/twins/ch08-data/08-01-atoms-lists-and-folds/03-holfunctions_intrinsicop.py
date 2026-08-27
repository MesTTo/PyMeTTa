"""examples/ch08-data/08-01-atoms-lists-and-folds/03-holfunctions_intrinsicop.metta in Python: a builtin, half applied.

`mymap` is written out rather than borrowed: an empty expression answers an
empty expression and a cons cell rebuilds itself around the applied function.
Both clauses select on the SHAPE of the second argument, which is Python's
`match` statement lowering to MeTTa's own case tower.

The recursive clause names the applied head and mapped tail before rebuilding
the cons cell. Plain assignments in a compiled body are the Python spelling of
the example's nested `let` sequence.
[source: examples/ch08-data/08-01-atoms-lists-and-folds/03-holfunctions_intrinsicop.metta:9; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]

The claim is that a builtin and a defined function behave the same when either
is handed to `mymap` half applied. `(== 1)` is equality with one argument, and
`eq` is a function whose whole body is that same equality written as Python's
own operator, so the two calls differ in nothing but which of them the engine
had to compile. Applying a half-applied head is the one place a tuple beats a
call, because the head is a value here rather than a name.

The two half applications sit either side of the operator word table. `fn.eq`
is `==`, the builtin, because the word table maps every operator to its
`operator`-module name at the attribute door; the DEFINED function is the
symbol literally spelled `eq`, so it takes the bracket, which is the exact
door by the same ruling. Naming both on one line is what makes the claim
readable.
"""

from metta import Expression, S, fn


def twin(m):
    """Map a half-applied builtin and its defined twin over one list."""

    @m.define
    def mymap(f, items):                    # (= (mymap $f ()) ())
        match items:                        # (= (mymap $f (cons $x $xs))
            case ():                        #    (cons ($f $x) (mymap $f $xs)))
                return ()
            case (S.cons, x, rest):
                head = f(x)
                tail = mymap(f, rest)
                return S.cons(head, tail)

    @m.define
    def eq(a, b):                           # (= (eq $a $b) (== $a $b))
        return a == b

    numbers = Expression((1, 2, 3))
    defined = S["eq"](1)  # rung: the word table owns S.eq, which is ==, so the symbol named eq takes rung 5's exact door
    assert mymap(fn.eq(1), numbers) == mymap(defined, numbers)   # [(True False False)]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 32377 to 32415, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 32415 to 32428, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 32428 to 32362, on the release tree:
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
#: RE-PINNED 2026-08-25, 32362 to 32372, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 32372 to 35315 (+2943), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 35315 to 35335 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 35335 to 33804 (-1531), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 33804
