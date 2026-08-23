"""examples/libraries/test_memo_multi_answer.metta in Python: caching a function that answers twice.

Two equations share one head, so they are two ALTERNATIVES rather than a
redefinition, and `@rules` is the door that says that: the generator's
parameter IS the equations' variable, and the bundle lands through the ordinary
write door.

The answers are compared as a sorted multiset rather than in clause order.
`memoize` recompiles by removing each equation and adding it back, which
reverses the order the clauses answer in, and answer order is unspecified while
multiplicity is not, so the set is what the claim can be about.
"""

from petta import S, equation, rules

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
    m.eval(S["import!"](m, S.library(S["lib_memo"])))

    @rules
    def choose(x):
        yield equation(S.choose(x)).to(x)
        yield equation(S.choose(x)).to(S.Pair(x, x))

    m += choose
    m.eval(S.memoize(S.choose))

    answers = m.fn.choose
    assert sorted(answers(7), key=str) == BOTH
    assert sorted(answers(7), key=str) == BOTH
