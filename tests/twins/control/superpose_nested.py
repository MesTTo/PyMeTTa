"""Purpose: examples/control/superpose_nested.metta in Python: a superposition flattens.

Four collapses of the same three answers, differing only in how deeply the
superposition is nested, and all four give the answers back flat: nesting a
superposition inside a superposition adds no structure, and mixing nested and
bare alternatives adds none either.

Inside a compiled body `superpose(a, b, c)` is the form itself, one expression
holding the alternatives, so the four lines below are the four lines of the
original. `collapse` is bound from `m.fn` because the dissolution table's
`list()` does not lower inside a compiled body, which supercollapse records.

The six tags are capitalised. A compiled body reads a lowercase free name as a
function and a capitalised one as data, so `a` raises where `A` is data; the
spelling gap case2 records against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4872 to 5431, +559 (+11.5%), by the twin contract
#: change: `progme` ENTERED the engine as a compiled body whose four lines
#: are the original's four, and pays `@m.define`'s fixed registration; the
#: `test` wrapper LEFT for `assert`. Measured min-of-3 over fresh processes
#: with the MORK backend linked in, which the artefact-free worktree omits
#: and which moves a compiled twin by about 10 inferences per definition;
#: against the example's 9074 the ratio is 0.5985. Prior: 4872, the
#: transliterated twin this replaces.
BUDGET = 5431


def twin(m):
    """Collapse the same three answers out of four different nestings."""
    collapse, superpose = m.fn("collapse"), m.fn("superpose")

    @m.define
    def progme():
        # (= (progme)
        #    ((collapse (superpose ((superpose (a b c)) (superpose (x y z)))))
        #     (collapse (superpose (a b c)))
        #     (collapse (superpose ((superpose (a b c)))))
        #     (collapse (superpose ((superpose (a b c)) x y z )))))
        return (
            collapse(superpose(superpose(A, B, C), superpose(X, Y, Z))),  # noqa: F821  -- capitalised free names in a compiled body are MeTTa data, which has no Python value to bind
            collapse(superpose(A, B, C)),  # noqa: F821  -- the same three tags
            collapse(superpose(superpose(A, B, C))),  # noqa: F821  -- the same three tags, nested once more
            collapse(superpose(superpose(A, B, C), X, Y, Z)),  # noqa: F821  -- nested and bare alternatives side by side
        )

    # Calling a symbol builds the expression headed by it, which is how a
    # fact is written too: `(a b c)` is `S.A(S.B, S.C)`.
    letters = S.A(S.B, S.C)
    both = S.A(S.B, S.C, S.X, S.Y, S.Z)

    # !(test (progme) ((a b c x y z) (a b c) (a b c) (a b c x y z)))
    assert progme() == [Expression((both, letters, letters, both))]
