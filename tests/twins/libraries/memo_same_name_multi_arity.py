"""examples/libraries/memo_same_name_multi_arity.metta in Python: two arities, cached apart.

`mix` answers at one and at two arguments, and each arity carries its own
cache: memoizing one leaves the other alone, which is what `is-memoized`
reports here five times. The two clauses are STACKED decorations of one MeTTa
name, dispatched by arity, for the reason memo_per_arity gives, and each arity
is called by its own Python name because a decorated definition answers a
callable.

`is-memoized` answers a boolean, so the claims compare against `[True]` and
`[False]` rather than against the symbols the example prints.
"""

from metta import S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Cache one arity of a name, then the other, and watch both report."""
    m.fn["import!"](m, S.library(S["lib_memo"]))

    @m.define
    def mix(x):
        # (= (mix $x) (+ $x 1))
        return x + 1

    @m.define(name="mix")
    def mix_2(x, y):
        # (= (mix $x $y) (+ $x $y))
        return x + y

    m.eval(S.memoize(S.mix, 1))

    memoized = m.fn.is_memoized
    assert memoized(S.mix, 1) == [True]
    assert memoized(S.mix, 2) == [False]

    assert mix(5) == [6]
    assert mix(5) == [6]

    assert mix_2(3, 4) == [7]
    assert mix_2(3, 4) == [7]

    m.eval(S.memoize(S.mix, 2))
    assert memoized(S.mix, 2) == [True]
    assert mix_2(8, 9) == [17]
    assert mix_2(8, 9) == [17]
