"""Purpose: examples/control/supercollapse.metta in Python: appending through answer sets.

`TupleConcat` takes two expressions apart into answers and gathers the answers
back into one expression, which is how a program written entirely in answer
sets appends. `range` then builds 1..9 out of nothing but that.

Taking an expression apart into answers is `yield from` and nothing else, so
`fanout` is the superposition of the two superpositions and the collapse
around it is what makes the result one expression again. The collapse is
spelled `collapse(...)` rather than `list(...)`: the dissolution table says
`list()` is `collapse`, and a compiled body refuses `list` outright, which is
filed as residue against P14.4.

`range` is `count_from` on the Python side because `range` is a Python BUILTIN
that a compiled body lowers to `py-range` before it looks for the definition's
own name; `name="range"` puts the MeTTa name on the equation and the recursion
resolves to it. `()` is the empty tuple, which is the empty expression, so the
base case needs no spelling of its own.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Append two expressions, then count to nine with nothing else."""
    # `fanout` exists only because `superpose` cannot fan a BOUND expression
    # in expression position. The top rung is one definition:
    #
    #     @m.define(name="TupleConcat")
    #     def concat(first, second):
    #         return collapse(superpose(superpose(first), superpose(second)))
    #
    # which stores `(collapse (superpose ((superpose ($Ev1)) ...)))` and
    # answers `((1 2) (3 4))` where the example answers `(1 2 3 4)`: the
    # lowering wraps the argument list, so `superpose(x)` is a superposition
    # over ONE alternative rather than of `x`. `yield from` is the only
    # spelling that fans, and it is a statement. Residue: P14.4.
    @m.define
    def fanout(first, second):
        # (superpose ((superpose $Ev1) (superpose $Ev2)))
        yield from first
        yield from second

    @m.define(name="TupleConcat")
    def concat(first, second):
        # (= (TupleConcat $Ev1 $Ev2) (collapse (superpose ((superpose $Ev1) (superpose $Ev2)))))
        return collapse(fanout(first, second))  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa; the package exports it nowhere yet (residue, P14.4)

    @m.define(name="range")
    def count_from(k, n):
        # (= (range $K $N) (if (< $K $N) (TupleConcat ($K) (range (+ $K 1) $N)) ()))
        return S.TupleConcat((k,), count_from(k + 1, n)) if k < n else ()

    # !(test (range 1 10) (1 2 3 4 5 6 7 8 9))
    assert count_from(1, 10) == [Expression((1, 2, 3, 4, 5, 6, 7, 8, 9))]
