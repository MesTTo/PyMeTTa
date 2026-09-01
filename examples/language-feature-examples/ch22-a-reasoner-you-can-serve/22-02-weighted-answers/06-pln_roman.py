"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/06-pln_roman.metta in Python: one bounded PLN proof search.

Four sentences say how strongly A inherits B, A inherits C, B inherits D and C
inherits D, and the query asks what PLN makes of A inheriting D. The answer is
a truth value and the four premises it came from.

`STV` is a `@m.rules` bundle: its four clauses fix a SYMBOL in the head, and a
bundle is the door for equations whose heads are structures rather than
parameter lists. `kb` is one equation whose body is DATA, so it goes through
the write door as the atom it is, and `_sentence` names the shape the four
rows share.

The bounded search is intentionally larger than the evaluator's default fuel,
so the example states its own budget. `max-stack-depth` is branch-local
reduction fuel and has no keyword on `limits()`, which scopes time, inferences
and SWI's stack BYTES, so the pragma is written as the term it is (friction,
P14.14). `with-pragma!` is banged, so the bound namespace performs it on the
line that writes it.
"""

from metta import S, equation, lib

#: How strongly each concept holds on its own, in the example's own order.
STRENGTHS = ((S.A, 0.5), (S.B, 0.25), (S.C, 0.25), (S.D, 0.5))

#: The four premises: a link, its truth value, and its one-item evidence stamp.
PREMISES = ((S.A, S.B, 0.25, 1), (S.A, S.C, 0.25, 2),
            (S.B, S.D, 0.5, 3), (S.C, S.D, 0.5, 4))


def _sentence(left, right, strength, identifier):
    """Build one PLN sentence with its truth value and one-item evidence stamp."""
    return S.Sentence(
        (S.Inheritance(left, right), S.stv(strength, 0.9)),
        (identifier,),
    )


def twin(m):
    """Load PLN, state the Roman-diamond knowledge base, and ask for A to D."""
    # !(import! &self (library lib_pln))
    m += lib.pln

    @m.rules
    def strengths():
        """(= (STV A) (stv 0.5 0.9)), and three more with a symbol in the head."""
        for concept, strength in STRENGTHS:
            yield equation(S.STV(concept)).to(S.stv(strength, 0.9))

    # (= (kb) ((Sentence ((Inheritance A B) (stv 0.25 0.9)) (1)) ...))
    m += equation(S.kb()).to(tuple(_sentence(*premise) for premise in PREMISES))

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (PLN.Query (kb) (Inheritance A D)))
    #        ((stv 0.5 0.9473684210526316) (1 2 3 4)))
    raised_stack = ((S.max_stack_depth, 100_000_000),)
    answer = m.fn.with_pragma(
        raised_stack,
        S["PLN.Query"](S.kb(), S.Inheritance(S.A, S.D)),
    ).one()
    assert answer[0] == S.stv(0.5, 0.9473684210526316)
    assert tuple(answer[1]) == (1, 2, 3, 4)


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 3285491, maximum 3285661
#: over 28 observations under `full-lane/218/workers=32`, so the re-pin owes
#: it an envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 30629305 to 30629327, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 30629327 to 30628674, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 30628674 to 30628694, on the release tree:
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
#: RE-PINNED 2026-08-25, 30628694 to 30628539, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 30628539 to 30642331 (+13792), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 30642331 to 30641911 (-420), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 30641911 to 30641747 (-164), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 30641747 to 30640083 (-1664), by the
#: specializer argument-walk fix this file's own chain named as the
#: follow-up. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 30640083 to 2305005 (-28335078), one corpus pricing
#: pass on the merged tree for the 2026-08-27..09-01 engine span
#: (8e75816d..f0744f86), whose four mechanisms are decomposed per lane in
#: benchmarks/baseline.json and ai-parametricity-audit.md passes 10-16: the
#: seam-offer routing and its one-wrap fold (net +8 inferences per evaluation),
#: the strict-scope removal leaving the eval path, the doubling cursor chunk
#: (~3 engine-side inferences per answer replacing per-answer crossings; drains
#: halve on CPU), and the aligned-path work; thirteen twins additionally carry
#: the idiom sweep's local deltas tabulated in the twin-idioms notes, none
#: above 347 [measured 2026-09-01: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 2305005 to 2305044 (+39), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 2305044 to 2304878 (-166), the subtract-atom primitive
#: and Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 2304878 to 2304929 (+51), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 2304929
