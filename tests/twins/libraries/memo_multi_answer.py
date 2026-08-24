"""examples/libraries/memo_multi_answer.metta in Python: caching a function that answers twice.

Two equations share one head, so they are two ALTERNATIVES rather than a
redefinition, and `yield` is the door that says so: each independent yield in a
compiled body stores one equation, which is exactly the pair of atoms the
example writes.

The answers are compared as a sorted multiset rather than in clause order.
`memoize` recompiles by removing each equation and adding it back, which
reverses the order the clauses answer in, and answer order is unspecified while
multiplicity is not, so the set is what the claim can be about.

Sorting takes a key here where the other twins in this folder need none. Atoms
carry the engine's standard order, but one of these two answers is the number
7, which the answer view decodes to a Python int, and comparing an int with an
Expression REFUSES in both directions by the same rule that makes `V.x < 2`
raise. `str` is the ordering that spans both kinds.
"""

from metta import S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1

#: Both answers for `(choose 7)`, in the order `sorted(key=str)` puts them.
BOTH = [S.Pair(7, 7), 7]


def twin(m):
    """Two answers for one call, before and after the cache."""
    m.fn["import!"](m, S.library(S["lib_memo"]))

    @m.define
    def choose(x):
        # (= (choose $x) $x), then (= (choose $x) (Pair $x $x))
        yield x
        yield S.Pair(x, x)

    m.eval(S.memoize(S.choose))

    assert sorted(choose(7), key=str) == BOTH
    assert sorted(choose(7), key=str) == BOTH
