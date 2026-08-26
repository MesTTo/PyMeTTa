"""Purpose: examples/types/functiontypes.metta in Python: what a signature does.

Four functions over one shape of body, and the declared signature decides what
reaches it and what comes back. `wu1` takes its second argument as `Atom`, so
that argument arrives unrun, then its `%Undefined%` result re-enters evaluation.
`wu1b` changes only the result to `Atom`, so its answer stays as produced.
`wu2` is `Number` throughout and adds; `wu3` answers a plain expression on one
branch and a number on the other, which `%Undefined%` allows.
[source: examples/types/functiontypes.metta:15; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]

All four say their types as ANNOTATIONS, which is the whole declaration: `int`
is Number, `Atom` is the Atom metatype, and `Any` is `%Undefined%`, all through
the one conversion table, so each arrow is written once and the engine checks
it. Inside the compiled bodies Python's own syntax is the MeTTa: `if a < 10`
is the guard, `a + b` builds `(+ $a $b)`, and wu3's other branch builds the
five-symbol expression `(a list not a number)` by calling its head, which is
what building a term by its head means whether or not anything defines that
head. Nothing here defines `a`, and the expression is data.

Note what the twin does NOT need: the example wraps its expected answers in
`noeval` because MeTTa's `test` evaluates them. Python's `==` evaluates
nothing, so the expected term is written as itself. It is written through
`Expression` rather than as a bare tuple because comparison is the one door a
tuple does not cross as an expression (P14.28).
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

from typing import Any

from metta import Atom, Expression, S

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 16662 to 18152, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 18152 to 18165, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 18165 to 18095, on the release tree:
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
#: RE-PINNED 2026-08-25, 18095 to 18105, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 18105 to 19809 (+1704), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 19809 to 19829 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 19829 to 18350 (-1479), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 18350
def twin(m):
    """Declare four signatures, then watch each one shape its call."""

    @m.define
    def wu1(a: int, b: Atom) -> Any:
        """(: wu1 (-> Number Atom %Undefined%)), (= (wu1 $a $b) (42 $a $b))."""
        return (42, a, b)

    @m.define
    def wu1b(a: int, b: Atom) -> Atom:
        """(: wu1b (-> Number Atom Atom)), preserving the produced expression."""
        return (42, a, b)

    @m.define
    def wu2(a: int, b: int) -> int:
        """(: wu2 (-> Number Number Number)), (= (wu2 $a $b) (+ $a $b))."""
        return a + b

    @m.define
    def wu3(a: int, b: int) -> Any:
        """(: wu3 (-> Number Number %Undefined%)), guarded on (< $a 10)."""
        if a < 10:
            return a + b
        return S.a(S.list, S["not"], S.a, S.number)

    # The Atom-typed argument arrives unevaluated, but wu1's %Undefined% result
    # re-enters evaluation and reduces the held sum in the produced expression.
    # !(test (wu1 (+ 2 4) (+ 4 2)) (42 6 6))
    assert wu1(S.add(2, 4), S.add(4, 2)) == [Expression((42, 6, 6))]
    # An Atom result answers as produced, retaining the held argument.
    # !(test (wu1b (+ 2 4) (+ 4 2)) (noeval (42 6 (+ 4 2))))
    assert wu1b(S.add(2, 4), S.add(4, 2)) == [
        Expression((42, 6, S.add(4, 2)))
    ]
    # !(test (wu2 (+ 2 4) (+ 4 2)) 12)
    assert wu2(S.add(2, 4), S.add(4, 2)) == [12]

    # %Undefined% output: either branch is acceptable to the checker.
    # !(test (wu3 42 0) (a list not a number))
    assert wu3(42, 0) == [S.a(S.list, S["not"], S.a, S.number)]
    # !(test (wu3 2 0) 2)
    assert wu3(2, 0) == [2]
