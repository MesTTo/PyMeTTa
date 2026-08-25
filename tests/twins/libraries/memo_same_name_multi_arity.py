"""examples/libraries/memo_same_name_multi_arity.metta in Python: two arities, cached apart.

`mix` answers at one and at two arguments, and each arity carries its own
cache: memoizing one leaves the other alone, which is what `is-memoized`
reports here five times. The two clauses are STACKED decorations of one MeTTa
name, dispatched by arity, for the reason memo_per_arity gives, and each arity
is called by its own Python name because a decorated definition answers a
callable.

`is-memoized` answers a boolean, so the claims compare against `[True]` and
`[False]` rather than against the symbols the example prints.
"""

from metta import S, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 37140 to 37368, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 37368 to 37389, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 37389 to 37343, on the release tree:
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
#: RE-PINNED 2026-08-25, 37343 to 37353, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 37353


def twin(m):
    """Cache one arity of a name, then the other, and watch both report."""
    m += lib.memo

    @m.define
    def mix(x):
        # (= (mix $x) (+ $x 1))
        return x + 1

    @m.define(name="mix")
    def mix_2(x, y):
        # (= (mix $x $y) (+ $x $y))
        return x + y

    m.eval(S.memoize(mix, 1))

    memoized = m.fn.is_memoized
    assert memoized(S.mix, 1) == [True]
    assert memoized(S.mix, 2) == [False]

    assert mix(5) == [6]
    assert mix(5) == [6]

    assert mix_2(3, 4) == [7]
    assert mix_2(3, 4) == [7]

    m.eval(S.memoize(mix_2, 2))
    assert memoized(S.mix, 2) == [True]
    assert mix_2(8, 9) == [17]
    assert mix_2(8, 9) == [17]
