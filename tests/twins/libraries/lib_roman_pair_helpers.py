"""examples/libraries/lib_roman_pair_helpers.metta in Python: pairs, from lib_roman.

`first` and `second` apply a function to one side of a pair and leave the other
alone; `flip` swaps the sides. All three are the example's subject, so the twin
names them through the function namespace, where a typo raises on the line that
writes it. What is Python's is the function they are given: `(= (inc $x) (+ $x
1))` is an ordinary compiled definition here.

A pair comes back as one expression, so the claim compares the whole answer
sequence; where the pair's head is a symbol the term is built by calling it.
"""

from petta import Expression, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Import lib_roman, define inc, then move it over each side of a pair."""
    m.eval(S["import!"](m, S.library(S["lib_roman"])))

    @m.define
    def inc(x):
        return x + 1

    assert m.fn.first(S.inc, (1, 9)) == [Expression((2, 9))]
    assert m.fn.second(S.inc, (1, 9)) == [Expression((1, 10))]
    assert m.fn.flip((S.left, S.right)) == [S.right(S.left)]
