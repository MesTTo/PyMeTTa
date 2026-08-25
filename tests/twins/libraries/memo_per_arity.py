"""examples/libraries/memo_per_arity.metta in Python: memoizing one arity of a name.

`add` carries two arities, and `memoize add 2` caches only the two-argument
one. The two clauses are STACKED decorations of one MeTTa name, which the
define door dispatches by arity; the second Python name states the MeTTa name
exactly, because its own underscore map would reach a different head.

Both arities are CALLED by their Python names. A decorated definition answers
a callable, so `add(3, 4)` is the call the example writes and no namespace sits
between the two.

The memoize argument is the function this file just defined. Mentioning a
`Defined` in term position carries that definition's head symbol, so the
declaration reads `S.memoize(add, 2)` without re-spelling its name.

`x + y + z` in the compiled body is Python's own left-associating addition, so
it builds `(+ (+ $x $y) $z)` without a word about it.
"""

from metta import S, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 32996 to 33129, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 33129 to 33150, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 33150 to 33094, on the release tree:
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
BUDGET = 33094


def twin(m):
    """Two arities of one name, one of them cached."""
    m += lib.memo

    @m.define
    def add(x, y):
        # (= (add $x $y) (+ $x $y))
        return x + y

    @m.define(name="add")
    def add_3(x, y, z):
        # (= (add $x $y $z) (+ (+ $x $y) $z))
        return x + y + z

    m.eval(S.memoize(add, 2))

    assert add(3, 4) == [7]
    assert add(3, 4) == [7]

    # The three-argument arity is untouched by the declaration above.
    assert add_3(1, 2, 3) == [6]

    assert add(5, 6) == [11]
    assert add(5, 6) == [11]
