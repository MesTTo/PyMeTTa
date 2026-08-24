"""Purpose: examples/control/superpose_nested.metta in Python: a superposition flattens.

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

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


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
