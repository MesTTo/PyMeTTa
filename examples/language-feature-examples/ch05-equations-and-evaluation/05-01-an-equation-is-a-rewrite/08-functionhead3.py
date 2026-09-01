"""Purpose: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/08-functionhead3.metta in Python: one constraint per argument.

`in` keeps a value only when it is a member of a list, and `myplus` chains one
constraint per argument, so the relation runs in BOTH directions: give it two
numbers and it filters, give it variables and it enumerates what is reachable.
The last form runs the whole relation backwards through a guard.

Both definitions are decorated Python functions, and both need the descent
ladder's bottom rung, each for its own reason. `in` is a Python KEYWORD, so no
Python function can carry that name: `name="in"` gives the equation the name
the example uses, and the decorated `is_in` object carries that exact MeTTa
head when another compiled body calls it. `is-member` is
an engine function whose spelling is hyphenated, and `fn.is_member` is its
mention door, rung 4's map applied at the factory.

The variables `myplus` chains over are holes rather than parameters, which
`V.x` and `V.y` say inside the body, and `S.let` names the relational `let`
Python's assignment does not reach.

A call answers what the relation reduces to, whether or not its arguments
carry variables, so running `myplus` backwards is the same Python line as
running it forwards; the bindings those variables took are the parallel row
face on the same view. `collapse` dissolves either way, because the view
already IS the list of answers. Only the last claim evaluates a term instead
of calling, because a `let`-as-guard has to wrap the call.
"""

from metta import TRUE, S, V, fn


def twin(m):
    """Constrain both arguments and the result, then run it every way."""

    @m.define(name="in")
    def is_in(x, items):
        # (= (in $x $L) (let True (is-member $x $L) $x))
        return S.let(True, fn.is_member(x, items), x)  # noqa: FBT003  -- True is the ATOM the membership check answers, matched against, not a flag  # rung: let as a guard

    @m.define
    def myplus(a, b):
        # (= (myplus $A $B)
        #    (let $A (in $X (1 2 3))
        #      (let $B (in $Y (2 3))
        #        (in (+ $X $Y) (3 4 5)))))
        return S.let(  # rung: solve(pattern, subject) has no expression-position form inside a compiled body
            a,
            is_in(V.x, (1, 2, 3)),
            S.let(  # rung: solve(pattern, subject) has no expression-position form inside a compiled body
                b, is_in(V.y, (2, 3)), is_in(fn.add(V.x, V.y), (3, 4, 5))
            ),
        )

    # fine:
    assert myplus(1, 3) == [4]
    # output out of range:
    assert myplus(3, 3) == []
    # input out of range:
    assert myplus(3, 4) == []
    # what can be reached when adding $X to 3:
    assert myplus(V.x, 3) == [4, 5]
    # what can be reached when adding $X to $Y:
    assert myplus(V.x, V.y) == [3, 4, 4, 5, 5]
    # with which $x added to 2 can we reach values above 3?
    guard = S.gt(S.myplus(V.x, 2), 3)
    assert m.eval(S.let(TRUE, guard, V.x)) == [2, 3]  # rung: let as a guard


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 16050 to 16107, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 16107 to 16115, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 16115 to 16086, on the release tree:
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
#: RE-PINNED 2026-08-25, 16086 to 16091, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 16091 to 17742 (+1651), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 17742 to 17762 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 17762 to 16263 (-1499), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 16263 to 8450 (-7813), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 8450 to 8429 (-21), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 8429 to 8468 (+39), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 8468
