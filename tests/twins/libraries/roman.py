"""Purpose: examples/libraries/roman.metta in Python: lib_roman, walked end to end.

Every claim here is about a lib_roman function, so every one names it. Three
families: the higher-order maps and folds, the nine set operations whose names
are drawn from the shapes of their Venn diagrams, and the composition
combinators. Then the inverses: `let` unifying a CALL against a value so the
function runs BACKWARDS, where `(let (head $x) (1 2 3) $x)` answers 1 because
head, run in reverse, says what its argument's first element must be. `solve`
is the door for that shape, and its answer template takes the variables the
PATTERN introduces as well as the subject's, which is what this reading needs.

Six of the nine set operations carry VARIABLES in their arguments, and the
call answers the resulting term all the same. Two of those answers carry a
fresh variable, which is why they are compared with `alpha_eq` rather than
`==`: the engine renames variables and the claim is about the shape, not the
name.

An engine function may be named with an ampersand, and three of these are:
`&&&`, `&^&` and the Venn family's punctuation take the bracket, which is the
exact door for a name Python's grammar cannot spell. The arithmetic the maps
and folds are GIVEN takes the other door in the same ladder: `+` and `*` have
words, so `S.add(1)` is the partial application `(+ 1)` and `S.add` alone is
the operator mentioned by name.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 763487 to 763867, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 763867 to 763366, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 763366 to 763336, on the release tree:
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
#: RE-PINNED 2026-08-25, 763336 to 763218, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 763218 to 800064 (+36846): ~30 definitions each
#: paying 5c731b03's per-translated-equation specializer bookkeeping
#: (ai-brief-p14-specializer-translation-tax), plus 6917bef7's small
#: share and layout [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 800064


def twin(m):
    """Import lib_roman, then exercise its three families and its inverses."""
    m += lib.roman

    # Higher-order functions.
    assert m.fn.map_flat(S.add(1), (1, 2, 3)) == [Expression((2, 3, 4))]
    assert m.fn.map_nested(S.add(1), (1, (2, 3))) == [
        Expression((2, Expression((3, 4))))
    ]
    assert m.fn.fold_flat(S.add, 0, (1, 2, 3)) == [6]
    assert m.fn.foldr_flat(S.cons, (), (1, (2, 3), 4)) == [
        Expression((1, Expression((2, 3)), 4))
    ]
    assert m.fn.fold_nested(S.add, 0, (1, (2, 3))) == [6]

    # Set operations. The three families are intersection (/=\), difference
    # (\=) and union (\=/), each in a unifying, an equal and an alpha variant.
    #
    # Six of the nine carry a MeTTa variable in an argument, and the call
    # answers the resulting term all the same.
    assert m.fn["/=\\"]((1, 2, V.a), (2, 3, 4)) == [Expression((2, 2))]
    assert m.fn["/==\\"]((1, 2, 3), (2, 3, 4)) == [Expression((2, 3))]
    unified = m.fn["/=a\\"]((1, 2, V.a), (2, V.a, 4)).one()
    assert unified.alpha_eq(Expression((2, V.a)))

    assert m.fn["\\="]((1, 2, 3), (V.a, 3, 4)) == [Expression((2,))]
    assert m.fn["\\=="]((1, 2, 3), (2, 3, 4)) == [Expression((1,))]
    assert m.fn["\\=a"]((1, 2, V.a), (2, V.a, 4)) == [Expression((1,))]

    assert m.fn["\\=/"]((1, 2, 3), (V.a, 3, 4)) == [Expression((2, 1, 3, 4))]
    assert m.fn["\\==/"]((1, 2, 3), (2, 3, 4)) == [Expression((1, 2, 3, 4))]
    joined = m.fn["\\=a/"]((1, 2, V.a), (2, V.a, 4)).one()
    assert joined.alpha_eq(Expression((1, 2, V.a, 4)))

    # Composition.
    assert m.fn["."](S.add(1), S.mul(2), 1) == [3]
    assert m.fn[".:"](S.add(1), S.add, 2, 3) == [6]
    assert m.fn["&&&"](S.add(2), S.mul(2), 1) == [Expression((3, 2))]

    # A branch that answers nothing prunes, so the fan-out keeps one answer.
    @m.define
    def mfail(x):  # noqa: ARG001  -- the branch answers nothing whatever it is given, which is what makes it prune
        yield from ()

    assert list(m.fn["&^&"](S.add(1), S.mfail(), 1)) == [2]

    # Reverse function matching, which is `solve`: the PATTERN wins its
    # variables from what the subject produces, so the call runs backwards and
    # the bindings come back projected by name.
    taken = m.solve(S["@"](V.lst, S.cons(V.h, V.t)), (1, 2, 3))
    assert (taken.lst, taken.h, taken.t) == (Expression((1, 2, 3)), 1, Expression((2, 3)))
    assert m.solve(S.head(V.x), (1, 2, 3)).x == 1
    assert m.solve(S.tail(V.xs), (1, 2, 3)).xs == Expression((2, 3))
    assert m.solve(S.mylast(V.x), (1, 2, 3)).x == 3
    assert m.solve(S.init(V.xs), (1, 2, 3)).xs == Expression((1, 2))
    split = m.solve(S.rcons(V.xs, V.x), (1, 2, 3))
    assert (split.xs, split.x) == (Expression((1, 2)), 3)

    # prog1 answers its first form, progn its last; both run both.
    assert m.fn.prog1(S.add(1, 1), S.add(2, 2)) == [2]
    assert m.fn.progn(S.add(1, 1), S.add(2, 2)) == [4]
