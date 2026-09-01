"""Purpose: examples/ch06-many-answers/01-superpose_nested.metta in Python: a superposition flattens.

Four collapses of the same three answers, differing only in how deeply the
superposition is nested, and all four give the answers back flat: nesting a
superposition inside a superposition adds no structure, and mixing nested and
bare alternatives adds none either.

Inside a compiled body `superpose(a, b, c)` is the form itself, one expression
holding the alternatives, so the four lines below are the four lines of the
original. `collapse` is the gathering, because the dissolution table's `list()`
does not lower inside a compiled body, which supercollapse records; it is a
name the subset reads as MeTTa and Python's own linter does not, so each line
carries the suppression the residue entry against P14.4 would delete.

The six tags are `S.a` through `S.z`, the lowercase symbols reached through
the factory, which a compiled body reads as the atoms they build.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, superpose


def twin(m):
    """Collapse the same three answers out of four different nestings."""
    # The top rung imports the gathering name, so Python's own linter sees it:
    #     from metta import collapse
    # The package exports neither `collapse` nor `empty`, so each call carries
    # an F821 suppression while a compiled body reads the free name as MeTTa.
    # `list()` is the dissolution table's spelling for `collapse` and does not
    # lower inside a body at all. Residue: P14.4.
    @m.define
    def progme():
        # (= (progme)
        #    ((collapse (superpose ((superpose (a b c)) (superpose (x y z)))))
        #     (collapse (superpose (a b c)))
        #     (collapse (superpose ((superpose (a b c)))))
        #     (collapse (superpose ((superpose (a b c)) x y z )))))
        return (
            collapse(superpose(superpose(S.a, S.b, S.c), superpose(S.x, S.y, S.z))),  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)
            collapse(superpose(S.a, S.b, S.c)),  # noqa: F821  -- the same name
            collapse(superpose(superpose(S.a, S.b, S.c))),  # noqa: F821  -- the same name, nested once more
            collapse(superpose(superpose(S.a, S.b, S.c), S.x, S.y, S.z)),  # noqa: F821  -- nested and bare alternatives side by side
        )

    # Calling a symbol builds the expression headed by it, which is how a
    # fact is written too: `(a b c)` is `S.a(S.b, S.c)`.
    letters = S.a(S.b, S.c)
    both = S.a(S.b, S.c, S.x, S.y, S.z)

    # !(test (progme) ((a b c x y z) (a b c) (a b c) (a b c x y z)))
    assert progme() == [Expression((both, letters, letters, both))]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 10880 to 10899, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 10899 to 10912, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 10912 to 10844, on the release tree:
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
#: RE-PINNED 2026-08-25, 10844 to 10854, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 10854 to 10877 (+23), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 10877 to 3815 (-7062), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 3815 to 3808 (-7), the subtract-atom primitive and the
#: Counter grain for -=: a new engine head shifts every twin's load structure,
#: and the removal doors changed meaning where a twin spells one [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 3808
