"""examples/ch18-performance/18-02-memoisation-and-tabling/09-tabling_fib.metta in Python: tabled recursion, declared once.

The source example asks for SWI set tabling explicitly, so the twin does too.
`@m.cache` instead promises an exact answer bag and uses the engine memo store;
the two mechanisms agree on this exclusive Fibonacci definition but have
different multiplicity laws.
"""

from metta import S, V, lib


def twin(m):
    """Define fib, table it, and take the thirtieth in linear time."""
    m += lib.tabling

    @m.define
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    m.eval(S.tabled(S.fib(V.n)))
    assert fib(30) == [832040]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 91092 to 91148, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 91148 to 91180, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 91180 to 91114, on the release tree:
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
#: RE-PINNED 2026-08-25, 91114 to 91134, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 91134 to 90639, because this twin now
#: declares the example's SWI set table through `m += lib.tabling`
#: and `(tabled (fib $n))`; `@m.cache` moved to the distinct exact-
#: bag memo substrate and is no longer an equivalent spelling.
#: Measured through tools/twin_coverage.py --measure --rounds 3 on
#: this reader.so-bearing tree under the suite's two-sided +-4
#: allowance.
#: RE-PINNED 2026-08-26, 90639 to 86995, when get_native_atom gained
#: head-indexed clauses for open-tail bound-head patterns. The tabling
#: library's per-equation `'get-atoms'('&metta', [tabled|_])` existence
#: probe had walked the whole catalog, 23.7 inferences per row over this
#: load; the catalog's growth had silently pushed the twin to 99,336
#: before the fix, and the 90639 pin itself already carried the walk over
#: the smaller pre-visibility catalog, so the twin recovers past it. The
#: example drops 16.7%, 73800 to 61464 [measured: metta=61464 twin=86995;
#: command=python bindings/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch18-performance/18-02-memoisation-and-tabling/09-tabling_fib.metta; fixture=open-tail-index
#: tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 86995 to 86938 (-57), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: The parallel async-scheduler branch's own history of this pin,
#: kept for the record; the merged value follows below:
#: RE-PINNED 2026-08-26, 90639 to 90892, on the completed async-scheduler
#: tree. This twin still uses the example's SWI set table and returns 832040;
#: the movement is the compiled QLF and predicate-index layout after adding
#: the scheduler, context callback, and exact-memo lifecycle clauses. Three
#: fresh serial processes agreed at the new cost
#: [measured: 90892 inferences; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch18-performance/18-02-memoisation-and-tabling/09-tabling_fib.metta; fixture=p14-audit-async with
#: engine/reader.so; commit=39092863ae34184a9f955f185ff57c1ff177ec40].
#: RE-PINNED 2026-08-26, 86938 to 86978 (+40), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 86978 to 97711 (+10733), at the
#: tabling-seam merge: declarations now table `as shared` (checked
#: readers `as (incremental, shared)`) so a live Answers cursor, the
#: source runner, and a later statistics call enter one answer trie
#: instead of a cursor-engine-private one, and calls route through
#: the declared dispatch ownership seam. The shared scope is what
#: SWI charges for cross-engine visibility; a private-when-unwatched
#: refinement is recorded as follow-up [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=tabling-seam merged tree with engine/reader.so; commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 97711 to 96272 (-1439), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 96272
