"""Purpose: examples/ch18-performance/18-01-larger-workloads/01-scale.metta in Python: a million atoms, five index shapes.

`addK` bulk-loads a million `(r K (mod K 10))` atoms, and five query shapes then
ask the same store different questions: everything, a bound first argument, a
bound second, both bound, and a variable in HEAD position. The driver runs all
five and reports the counts, which is the claim.

The driver is an ordinary Python function under the decorator: it calls its six
siblings by name through the mention door and builds the report it answers.

Two families stay at the container door, each for a blocker rather than a
preference.

The five queries are `(collapse (match ...))`, and a compiled body has no
spelling for `collapse` at all: `list(...)` and `fn.collapse` are both refused,
and a comprehension over a match lowers to `map-atom`, a different operation,
`(map-atom (match ...) (|-> ($x) $x))`, answering once per solution where
collapse answers once [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT:
`list(space[pattern])` inside a body. Residue P14.4.

`addK` compiles and then cannot run. A compiled `if` wraps its condition in
`py-truthy` and `==` lowers to `py-eq`, so every level of this million-deep
recursion spends reductions the original does not, and the evaluator's default
100,000 stack bound is reached at K=100,000: the compiled `addK` answers
`(Error 75002 StackOverflow)` where the term door completes a million
[measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. `m.limits` bounds inferences and time
and not stack depth, so there is no scope to raise it in and the example states
no pragma to copy. PERFECT: a compiled `if` that leaves an engine-Bool
condition alone, or a stack-depth mode block. Residue P14.4 and P14.14.
"""

from metta import S, V, equation, fn, if_

#: What a million atoms answer to the five shapes, in the driver's own order.
REPORT = S["all:"](1_000_000, S["first:"], 1, S["second:"], 100_000,
                   S["rel:"], 1, S["both:"], 1)


def twin(m):
    """Load a million atoms, then ask five differently-shaped questions."""
    m += equation(S.addK(V.k)).to(
        if_(S.eq(V.k, 0),  # rung: the compiled body answers StackOverflow at this depth
                S.done,
                S["let*"](((V.k10, V.k % 10),  # rung: as above
                           (V.written, S.add_atom(m, S.r(V.k, V.k10)))),  # rung: as above
                          S.addK(V.k - 1))))

    # Five shapes over one store: nothing bound, first bound, second bound,
    # both bound, and the relation itself a variable.
    m += equation(S.q_all()).to(S.collapse(S.match(m, S.r(V.x, V.y), S.r(V.x, V.y))))  # rung: a compiled body has no spelling for collapse
    m += equation(S.q_first(V.a)).to(S.collapse(S.match(m, S.r(V.a, V.y), S.r(V.a, V.y))))  # rung: as above
    m += equation(S.q_second(V.b)).to(S.collapse(S.match(m, S.r(V.x, V.b), S.r(V.x, V.b))))  # rung: as above
    m += equation(S.q_both(V.a, V.b)).to(S.collapse(S.match(m, S.r(V.a, V.b), S.r(V.a, V.b))))  # rung: as above
    m += equation(S.q_rel(V.r)).to(S.collapse(S.match(m, (V.r, 643, 3), (V.r, 643, 3))))  # rung: as above

    @m.define
    def indexing_demo(k):
        _loaded = fn.addK(k)
        everything = fn.q_all()
        first = fn.q_first(7)
        second = fn.q_second(3)
        rel = fn.q_rel(S.r)
        both = fn.q_both(42, 2)
        return S["all:"](fn.length(everything), S["first:"], fn.length(first),
                         S["second:"], fn.length(second), S["rel:"], fn.length(rel),
                         S["both:"], fn.length(both))

    assert indexing_demo(1_000_000) == [REPORT]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 26335504 to 26335523, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 26335523 to 26335529, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 26335529 to 26335496, on the release tree:
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
#: RE-PINNED 2026-08-25, 26335496 to 26335501, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 26335501 to 26335533 (+32), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 26335533 to 26335555 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 26335555 to 23218681 (-3116874), the compiled-language
#: batch: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 23218681 to 23218650 (-31), the subtract-atom
#: primitive and Counter's grain for -=: a new engine head shifts every twin's
#: load structure, the removal doors changed meaning where a twin spells one,
#: and the quad twin stopped being a different program [measured 2026-09-01:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 23218650 to 23218632 (-18), generic Python operators
#: now dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 23218632 to 23218842 (+210), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
#: RE-PINNED 2026-09-02, 23218842 to 23218870 (+28), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-02, 23218870 to 23218884 (+14), P43 protects both
#: generated policy-check fallbacks from space-local capture [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 23218884
