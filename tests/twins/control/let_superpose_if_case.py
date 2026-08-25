"""Purpose: examples/control/let_superpose_if_case.metta in Python: four forms at once.

One equation binds a superposition, tests each answer, dispatches the ones
that pass, and answers a default for the one that fails. Every layer has a
Python statement that means it, and the equation the four of them compile to
is the original's own: an assignment IS the `let`, `superpose(...)` in
expression position IS the superposition, the `if` is Python's `if`, and the
`case` over `(1 $y)` is Python's `match` statement, arms and fallback
included.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11801 to 11820, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 11820 to 11833, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 11833 to 11765, on the release tree:
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
BUDGET = 11765


def twin(m):
    """Fan out four numbers, filter them, and dispatch what survives."""
    @m.define
    def f(_x):
        # (= (f $x) 42): the head variable the body never reads
        return 42

    @m.define
    def progme():
        # (= (progme)
        #    (let $y (superpose (2 3 4 5))
        #            (if (> $y 2)
        #                (case (1 $y) (((1 3) (f 0)) ((1 4) (42 42)) ($else (42 42 42))))
        #                answertoeverything)))
        y = superpose(2, 3, 4, 5)
        if y > 2:
            match 1, y:
                case (1, 3):
                    return f(0)
                case (1, 4):
                    return 42, 42
                case _:
                    return 42, 42, 42
        return S.answertoeverything

    # !(test (collapse (progme)) (answertoeverything 42 (42 42) (42 42 42)))
    assert progme() == [S.answertoeverything, 42, Expression((42, 42)), Expression((42, 42, 42))]
