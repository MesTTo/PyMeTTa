"""Purpose: examples/ch09-types/10-recursive_types2.metta in Python: Peano numbers and a test.

`Nat` is `Z` or `(S n)` for a `Nat`, and `Greater` walks two of them down in
step until one runs out. `Nat` itself is a Python class, so the three arrows
are written from Python types through the one conversion table.

The three clauses select on the SHAPE of their arguments, `(S $x)` against `Z`,
which is what `@m.rules` is for: it lands bare coexisting equations, derives no
guard, and its parameters ARE the equations' variables. A compiled parameter
list reaches none of it, because a head pattern there is a literal default, a
constant IN a position rather than a structure around one.

The constructor pair is declared rather than written as a class for one reason
beyond the head shapes: a Python class declares ITSELF as what its constructor
returns, where `(: S (-> Nat Nat))` declares the ADT the constructor belongs to
(friction, P14.10). The constructor here is also spelled `S`, which is already
the name of the symbol factory, so it is written `S.S`.
"""

from metta import FALSE, TRUE, S, arrow, equation, typed


class Nat:
    """The MeTTa type `Nat`, so the three arrows can be built from Python types."""


def twin(m):
    """Build two Peano numbers and compare them."""
    succ = S.S

    # (: Z Nat) (: S (-> Nat Nat)) (: Greater (-> Nat Nat Bool))
    m += typed(S.Z, Nat)
    m += typed(succ, arrow(Nat, Nat))
    m += typed(S.Greater, arrow(Nat, Nat, bool))

    @m.rules
    def order(smaller, larger):
        """The example's three clauses, over two shared rule variables."""
        # (= (Greater (S $x) Z) True)
        yield equation(S.Greater(succ(smaller), S.Z)).to(TRUE)
        # (= (Greater Z $x) False)
        yield equation(S.Greater(S.Z, smaller)).to(FALSE)
        # (= (Greater (S $x) (S $y)) (Greater $x $y))
        yield equation(S.Greater(succ(smaller), succ(larger))).to(
            S.Greater(smaller, larger)
        )

    one, two = succ(S.Z), succ(succ(S.Z))
    # !(test (Greater (S Z) (S Z)) false)
    assert m.fn.Greater(one, one) == [False]
    # !(test (Greater (S (S Z)) (S Z)) true)
    assert m.fn.Greater(two, one) == [True]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11637 to 11673, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 11673 to 11612, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 11612 to 11614, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 11614 to 13321 (+1707), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 13321 to 13273 (-48), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 13273 to 13257 (-16), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 13257 to 11742 (-1515), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 11742 to 8598 (-3144), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 8598 to 8590 (-8), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 8590
