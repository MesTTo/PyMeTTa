"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/09-nars_tuffy.metta in Python: the Tuffy smokers knowledge base.

Ten NARS sentences say who smokes, who is friends with whom, that friends of
smokers smoke, and that smokers get cancer. The claim asks NARS what it makes
of Edward being cancerous, and gets back a truth value and the five premises it
came from.

The knowledge base is ONE equation whose body is a ten-element expression, so
it is written as data: a Python tuple of ten `sentence(...)` calls. NARS spells
four things with punctuation, so each gets a named Python function and the ten
rows then read as the logic they are: `-->` is inheritance, `==>` implication,
`[] p` the property `p`, and U+00D7 the product of two terms. That last head is
written as the escape `\N{MULTIPLICATION SIGN}` and called `multiplication-sign`
in prose, because a bare one is a confusable ruff refuses.

`kb` is ONE equation whose body is DATA, so it goes through the write door as
the atom it is. The punctuation heads are not what keeps it there: measured
2026-08-24, `S["-->"](a, S["[]"](b))` inside a compiled body stores
`(--> $a ([] $b))`. What a compiled body cannot do is CALL the seven host
helpers that make the ten rows readable, because a body is pure atoms, so
compiling `kb` would mean inlining every bracket again. The import takes the
space HANDLE, because a space crosses a term position as itself.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

from metta import Expression, S, V, equation, lib


def inheritance(subject, predicate):
    """`(--> subject predicate)`, NARS inheritance."""
    return S["-->"](subject, predicate)


def implication(premise, conclusion):
    """`(==> premise conclusion)`, NARS implication."""
    return S["==>"](premise, conclusion)


def product(left, right):
    """`(multiplication-sign left right)`, the NARS product of two terms.

    The head is the REAL U+00D7, and it matches the rules in
    `lib/lib_nars/lib_nars.metta` because the engine reads its sources as UTF-8
    whatever the locale, which `twin_coverage.py`'s `_environment` pins to
    `LC_ALL=C` [measured 2026-08-23 under `LC_ALL=C`: 0 U+FFFD replacement
    characters and 12 real U+00D7 heads in the imported library, where the
    locale-dependent reader gave 123 replacements over the 51 `|-` clauses;
    commit=3459d4f6fce103269ff5cdd575edec4bb9e4be95].
    """
    return S["\N{MULTIPLICATION SIGN}"](left, right)


def prop(name):
    """`([] name)`, the NARS property `name`."""
    return S["[]"](name)


def sentence(statement, strength, ident):
    """`(Sentence (statement (stv strength 0.9)) (ident))`, one row of the KB.

    Every row of this example carries the same 0.9 confidence, so only the
    strength varies.
    """
    return S.Sentence((statement, S.stv(strength, 0.9)), (ident,))


def friends(left, right):
    """`(--> (multiplication-sign left right) friend)`, the friendship relation."""
    return inheritance(product(left, right), S.friend)


def smokes(who):
    """`(--> who ([] smokes))`."""
    return inheritance(who, prop(S.smokes))


def twin(m):
    """State ten sentences, then ask NARS about one of their consequences."""
    # The library's file name is `lib_nars.metta`, and the factory attribute
    # door maps every underscore to a hyphen, so the name takes the bracket.
    # !(import! &self (library lib_nars))
    m += lib.nars

    # The knowledge base, as the ten rows it is. `$1` and `$2` in the first two
    # rows are the rules' variables; everything below them is ground.
    # (= (kb)
    #    ((Sentence ((==> (--> (multiplication-sign $1 $2) friend)
    #                     (==> (--> $1 ([] smokes))
    #                          (--> $2 ([] smokes))))
    #                (stv 0.4 0.9)) (1))
    #     (Sentence ((==> (--> $1 ([] smokes))
    #                     (--> $1 ([] cancerous)))
    #                (stv 0.6 0.9)) (2))
    #     (Sentence ((--> (multiplication-sign Anna Bob) friend) (stv 1.0 0.9)) (3))
    #     (Sentence ((--> (multiplication-sign Anna Edward) friend) (stv 1.0 0.9)) (4))
    #     (Sentence ((--> (multiplication-sign Anna Frank) friend) (stv 1.0 0.9)) (5))
    #     (Sentence ((--> (multiplication-sign Edward Frank) friend) (stv 1.0 0.9)) (6))
    #     (Sentence ((--> (multiplication-sign Gary Helen) friend) (stv 1.0 0.9)) (7))
    #     (Sentence ((--> (multiplication-sign Gary Frank) friend) (stv 0.0 0.9)) (8))
    #     (Sentence ((--> Anna ([] smokes)) (stv 1.0 0.9)) (9))
    #     (Sentence ((--> Edward ([] smokes)) (stv 1.0 0.9)) (10))))
    m += equation(S.kb()).to(
        (
            sentence(
                implication(
                    friends(V["1"], V["2"]),
                    implication(smokes(V["1"]), smokes(V["2"])),
                ),
                0.4,
                1,
            ),
            sentence(
                implication(
                    smokes(V["1"]), inheritance(V["1"], prop(S.cancerous))
                ),
                0.6,
                2,
            ),
            sentence(friends(S.Anna, S.Bob), 1.0, 3),
            sentence(friends(S.Anna, S.Edward), 1.0, 4),
            sentence(friends(S.Anna, S.Frank), 1.0, 5),
            sentence(friends(S.Edward, S.Frank), 1.0, 6),
            sentence(friends(S.Gary, S.Helen), 1.0, 7),
            sentence(friends(S.Gary, S.Frank), 0.0, 8),
            sentence(smokes(S.Anna), 1.0, 9),
            sentence(smokes(S.Edward), 1.0, 10),
        )
    )

    # Edward smokes, so Edward is cancerous, and the answer names the five
    # sentences the derivation used.
    # !(test (NARS.Query (kb) (--> Edward ([] cancerous)))
    #        ((stv 0.6 0.48941156079382964) (2 5 6 9 10)))
    assert m.fn["NARS.Query"](
        S.kb(), inheritance(S.Edward, prop(S.cancerous))
    ) == [Expression((S.stv(0.6, 0.48941156079382964), Expression((2, 5, 6, 9, 10))))]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 586166175 to 586166213, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 586166213 to 586165716, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 586165716 to 586165692, on the release tree:
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
#: RE-PINNED 2026-08-25, 586165692 to 586165578, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 586165578 to 586175343 (+9765), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 586175343 to 586174992 (-351), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 586174992 to 586174869 (-123), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 586174869 to 586173138 (-1731), by the
#: specializer argument-walk fix this file's own chain named as the
#: follow-up. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 586173138 to 4735420 (-581437718), one corpus pricing
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
#: RE-PINNED 2026-09-01, 4735420 to 4735304 (-116), the subtract-atom primitive
#: and Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 4735304 to 4735313 (+9), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 4735313 to 4737638 (+2325), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
#: RE-PINNED 2026-09-02, 4737638 to 4737853 (+215), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-02, 4737853 to 4737934 (+81), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4737934
