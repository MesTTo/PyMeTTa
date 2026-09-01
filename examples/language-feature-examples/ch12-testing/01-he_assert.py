"""Purpose: examples/ch12-testing/01-he_assert.metta in Python: the assert family itself.

Python's `assert` is what MeTTa's assert family dissolves into, which is why
this one file cannot dissolve it: the twelve functions here ARE the subject, so
each claim is a Python assert ABOUT one of them. That is what the `RUNG`
declaration below records.

Three distinctions the file draws, and they are the reason it exists.
`assertEqual` compares evaluated results, so both sides are built as terms
rather than computed in Python, and each takes the operator's WORD, `S.add` for
`+` and `S.sub` for `-`. The `ToResult` forms take the expected results as a
TUPLE and do not evaluate it, so a single result is written `(3)` and not `3`.
The `Alpha` forms compare modulo variable renaming, and the `Msg` variants add
a failure message and otherwise behave as their bases.

`adder` is an ordinary compiled definition. Its body is a one-element
expression holding a variable the head does not bind, which a body says with
Python's own one-tuple; the engine freshens the name, which is why the claim
about it is an ALPHA one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, V, lib


def twin(m):
    """Ask each member of the assert family whether it holds."""
    m += lib.he

    assert m.fn.assertEqual(S.add(1, 2), S.sub(6, 3)) == [True]

    # Comparing modulo variable renaming carries variables by definition, and
    # the call answers the True this family reports all the same.
    alpha_equal = m.fn.assertAlphaEqual
    assert alpha_equal(S.h(V.x, V.y), S.h(V.a, V.b)) == [True]
    assert alpha_equal(S.quote(V.x + V.y), S.quote(V.a + V.b)) == [True]

    # The ToResult forms take the expected results as a tuple, not a bare
    # value, and do not evaluate it. A single result is therefore (3), not 3.
    to_result = m.fn.assertEqualToResult
    assert to_result(S.add(1, 2), (3,)) == [True]
    assert to_result(S.superpose((1, 2)), (1, 2)) == [True]

    @m.define
    def adder():
        # (= (adder) ($x))
        return (V.x,)

    assert m.fn.assertAlphaEqualToResult(
        S.adder(), (Expression((V.y,)),)
    ) == [True]

    # Every expected result must appear among those produced.
    includes = m.fn.assertIncludes
    assert includes(S.superpose((1, 2, 3)), (2,)) == [True]
    assert includes(S.superpose((1, 2, 3)), (2, 3)) == [True]

    # The Msg variants take a failure message and otherwise behave as their bases.
    assert m.fn.assertEqualMsg(S.add(1, 2), S.sub(6, 3), G("sums differ")) == [True]
    assert m.fn.assertAlphaEqualMsg(
        S.h(V.x, V.y), S.h(V.a, V.b), G("not alpha equal")
    ) == [True]
    assert m.fn.assertEqualToResultMsg(
        S.add(1, 2), (3,), G("not the expected result")
    ) == [True]
    assert m.fn.assertAlphaEqualToResultMsg(
        S.adder(), (Expression((V.y,)),), G("not alpha equal")
    ) == [True]


#: Why this twin sits below the top rung: every claim here is about a member of
#: the assert family, so naming them is the file's subject rather than MeTTa
#: written in Python punctuation.
RUNG = "the assert family is this file's subject, so each claim names one of its twelve members"

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 20919 to 20974, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 20974 to 20985, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 20985 to 20919, on the release tree:
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
#: RE-PINNED 2026-08-25, 20919 to 20929, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 20929 to 19924 (-1005), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 19924 to 19944 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 19944 to 19628 (-316), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 19628 to 19565 (-63), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 19565 to 19653 (+88), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 19653 to 19889 (+236), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
#: RE-PINNED 2026-09-02, 19889 to 19934 (+45), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-02, 19934 to 19951 (+17), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 19951
