"""examples/ch08-data/08-01-atoms-lists-and-folds/02-holfunctions.metta in Python: the higher-order forms.

`map-atom`, `filter-atom` and `foldl-atom` walk an expression with a TEMPLATE
or with a named function, and the file is that contrast written six times.
Python draws the same line and the compiler emits the same instructions on
either side of it: an inline expression is a comprehension or a lambda, and a
named function is that name written in the same place.

So the `a` half reads as ordinary Python with the work inline, the `b` half
reads as ordinary Python with the work named, and the engine sees the two
instruction shapes the original wrote by hand. `functools.reduce` is the fold
in both halves, taking a lambda in one and a function in the other; the
comprehension is the map and the filter, calling the named function where the
`b` half names one.

The last form folds expressions rather than numbers, with `append` reached at
the function namespace, where rung 4's map turns the underscore back into the
hyphen the engine holds. The original writes it as a bare runnable over one
literal, so the twin names it and passes the parts in. Every definition here is
nullary or takes plain names, so no stacking question arises anywhere in the
file.
"""

import functools

from metta import Expression, fn


def twin(m):
    """Fold, map and filter, first with the work inline and then with it named."""

    @m.define
    def foldfun(a, b):  # (= (foldfun $a $b) (+ $a $b))
        return fn.add(a, b)

    @m.define
    def mapfun(a):  # (= (mapfun $a) (+ $a 1))
        return fn.add(a, 1)

    @m.define
    def filterfun(x):  # (= (filterfun $x) (> $x 3))
        return fn.gt(x, 3)

    @m.define
    def f1a():  # (= (f1a) (foldl-atom (1 2 3 4) 0
        return functools.reduce(
            lambda acc, x: fn.add(acc, x), (1, 2, 3, 4), 0
        )  # $acc $x (+ $acc $x)))

    @m.define
    def f2a():  # (= (f2a) (map-atom (1 2 3) $x (+ $x 1)))
        return [fn.add(x, 1) for x in (1, 2, 3)]

    @m.define
    def f3a():  # (= (f3a) (filter-atom (1 2 3 4 5) $x (> $x 3)))
        return [x for x in (1, 2, 3, 4, 5) if fn.gt(x, 3)]

    @m.define
    def f1b():  # (= (f1b) (foldl-atom (1 2 3 4) 0 foldfun))
        return functools.reduce(foldfun, (1, 2, 3, 4), 0)

    @m.define
    def f2b():  # (= (f2b) (map-atom (1 2 3) mapfun))
        return [mapfun(x) for x in (1, 2, 3)]

    @m.define
    def f3b():  # (= (f3b) (filter-atom (1 2 3 4 5) filterfun))
        return [x for x in (1, 2, 3, 4, 5) if filterfun(x)]

    @m.define
    def foldfun2(a, b):  # (= (foldfun2 $a $b) (append $a $b))
        return fn.append(a, b)

    @m.define
    def joined(parts):  # the bare runnable, named:
        # (foldl-atom ((1 2) (3 4) (5 6)) () $acc $x (append $acc $x))
        return functools.reduce(lambda acc, x: fn.append(acc, x), parts, ())

    assert f1a() == [10]  # [10]
    assert f2a() == [Expression((2, 3, 4))]  # [(2 3 4)]
    assert f3a() == [Expression((4, 5))]  # [(4 5)]

    assert f1b() == [10]  # [10]
    assert f2b() == [Expression((2, 3, 4))]  # [(2 3 4)]
    assert f3b() == [Expression((4, 5))]  # [(4 5)]

    parts = Expression((Expression((1, 2)), Expression((3, 4)), Expression((5, 6))))
    assert joined(parts) == [Expression((1, 2, 3, 4, 5, 6))]  # [(1 2 3 4 5 6)]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 55190 to 55325, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 55325 to 54952, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 54952 to 54896, on the release tree:
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
#: RE-PINNED 2026-08-25, 54896 to 54810, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 54810 to 57062 (+2252), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 57062 to 56794 (-268), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 56794 to 56602 (-192), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 56602 to 55354 (-1248), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 55354 to 28628 (-26726), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 28628 to 28483 (-145), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 28483 to 29392 (+909), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 29392
