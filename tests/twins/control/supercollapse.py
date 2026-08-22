"""Purpose: examples/control/supercollapse.metta in Python: appending through answer sets.

`TupleConcat` takes two expressions apart into answers and gathers the answers
back into one expression, which is how a program written entirely in answer
sets appends. `range` then builds 1..9 out of nothing but that.

Taking an expression apart into answers is `yield from` and nothing else, so
`fanout` is the superposition of the two superpositions and the collapse
around it is what makes the result one expression again. The collapse is
spelled `collapse(...)` rather than `list(...)`: the dissolution table says
`list()` is `collapse`, and a compiled body refuses `list` outright, which is
filed as residue against P14.4. `collapse` is bound from `m.fn` so the name a
compiled body reads as MeTTa is a name Python can see too.

`range` is `count_from` on the Python side because `range` is a Python BUILTIN
that a compiled body lowers to `py-range` before it looks for the definition's
own name; `name="range"` puts the MeTTa name on the equation and the recursion
resolves to it. `()` is the empty tuple, which is the empty expression, so the
base case needs no spelling of its own.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S

#: The equation's own name, so a compiled body and a Python reader see the
#: same spelling. A compiled body resolves a free name EXACTLY, so
#: `tuple_concat` would reach nothing.
TupleConcat = S.TupleConcat

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 7810 to 8116, +306 (+3.9%), by the twin contract
#: change: `TupleConcat` ENTERED the engine as two compiled definitions, a
#: `yield from` pair and the collapse around it, where it was a container-
#: door equation, so two fixed registrations arrive; the `test` wrapper LEFT
#: for `assert`. Measured min-of-3 over fresh processes with the MORK backend
#: linked in, which the artefact-free worktree omits and which moves a
#: compiled twin by about 10 inferences per definition; against the example's
#: 9648 the ratio is 0.8412. Prior: 7810, the transliterated twin this
#: replaces.
BUDGET = 8116


def twin(m):
    """Append two expressions, then count to nine with nothing else."""
    collapse = m.fn("collapse")

    @m.define
    def fanout(first, second):
        # (superpose ((superpose $Ev1) (superpose $Ev2)))
        yield from first
        yield from second

    @m.define(name="TupleConcat")
    def concat(first, second):
        # (= (TupleConcat $Ev1 $Ev2) (collapse (superpose ((superpose $Ev1) (superpose $Ev2)))))
        return collapse(fanout(first, second))

    @m.define(name="range")
    def count_from(k, n):
        # (= (range $K $N) (if (< $K $N) (TupleConcat ($K) (range (+ $K 1) $N)) ()))
        return TupleConcat((k,), count_from(k + 1, n)) if k < n else ()

    # !(test (range 1 10) (1 2 3 4 5 6 7 8 9))
    assert count_from(1, 10) == [Expression((1, 2, 3, 4, 5, 6, 7, 8, 9))]
