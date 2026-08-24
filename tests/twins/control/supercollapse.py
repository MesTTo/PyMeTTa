"""Purpose: examples/control/supercollapse.metta in Python: appending through answer sets.

`TupleConcat` takes two expressions apart into answers and gathers the answers
back into one expression, which is how a program written entirely in answer
sets appends. `range` then builds 1..9 out of nothing but that.

Both operations are named where the subset reads them as MeTTa, and the
equation stored is the original's own. Two rungs are visible on the line.
`collapse` is written rather than `list()`, because the dissolution table says
`list()` is `collapse` and a compiled body refuses `list` outright; and taking
a BOUND expression apart is `fn.superpose(x)`, because the ruled
expression-position spelling `superpose(*x)` refuses with "Starred has no
MeTTa equivalent in the compiled subset" and `superpose(x)` is the other
operation, one alternative that happens to be `$x` [both measured 2026-08-24;
commit=WORKTREE]. Both are filed against P14.4.

Both heads are named rather than spelled, and each for a measured reason. A
def's own name IS its head, so `name=` is for heads Python cannot spell:
`range` is a BUILTIN a compiled body lowers to `py-range` before it looks for
the definition's own name, so `def range` compiles its own recursion to the
builtin and answers `[1, (2 3 4)]`; and `TupleConcat` is a CapWords FUNCTION
head, which `def TupleConcat` can spell only at the cost of an N-family
suppression this repository's gate has no budget for
[both measured 2026-08-24; commit=WORKTREE]. `()` is the empty tuple, which is
the empty expression, so the base case needs no spelling of its own.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, fn, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Append two expressions, then count to nine with nothing else."""
    @m.define(name="TupleConcat")
    def concat(first, second):
        # (= (TupleConcat $Ev1 $Ev2) (collapse (superpose ((superpose $Ev1) (superpose $Ev2)))))
        return collapse(superpose(fn.superpose(first), fn.superpose(second)))  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)

    @m.define(name="range")
    def count_from(k, n):
        # (= (range $K $N) (if (< $K $N) (TupleConcat ($K) (range (+ $K 1) $N)) ()))
        return concat((k,), count_from(k + 1, n)) if k < n else ()

    # !(test (range 1 10) (1 2 3 4 5 6 7 8 9))
    assert count_from(1, 10) == [Expression((1, 2, 3, 4, 5, 6, 7, 8, 9))]
