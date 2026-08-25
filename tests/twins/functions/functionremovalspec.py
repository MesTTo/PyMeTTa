"""examples/functions/functionremovalspec.metta in Python: removal under specialization.

`f` applies its argument, so a call `(f g)` SPECIALIZES on `g`; removing one
of `f`'s two clauses must leave the specialized call working over the clause
that remains, and putting the clause back must bring its answer back.

Both definitions are decorated Python functions. `g` is a computation; `f`'s
two clauses are ALTERNATIVES that both answer, which a generator body says
directly, one stored equation per yield. Naming the equation the yield stored
is what lets `-=` and `+=` take it as the atom it is.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 19594 to 19651, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 19651 to 19662, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 19662 to 19598, on the release tree:
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
BUDGET = 19598


def twin(m):
    """Remove one clause of a specialized function, then put it back."""

    @m.define
    def g(x):
        # (= (g $x) (+ $x 1))
        return x + 1

    @m.define
    def f(g):
        # (= (f $g) ($g 1))
        yield (g, 1)
        # (= (f $g) ($g 2))
        yield (g, 2)

    one = equation(S.f(V.g)).to((V.g, 1))

    assert m.eval(S.f(S.g)) == [2, 3]

    m -= one
    # The specialized call still runs, over the one clause left.
    assert m.eval(S.f(S.g)) == [3]

    m += one
    assert m.eval(S.f(S.g)) == [3, 2]
