"""examples/libraries/test_memo_same_name_multi_arity.metta in Python: two arities, cached apart.

`mix` answers at one and at two arguments, and each arity carries its own
cache: memoizing one leaves the other alone, which is what `is-memoized`
reports here five times. Both equations come through `@rules`, for the reason
test_memo_per_arity gives.

`is-memoized` answers a boolean, so the claims compare against `[True]` and
`[False]` rather than against the symbols the example prints.
"""

from petta import S, equation, rules

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Cache one arity of a name, then the other, and watch both report."""
    m.eval(S["import!"](m, S.library(S["lib_memo"])))

    @rules
    def mix(x, y):
        yield equation(S.mix(x)).to(x + 1)
        yield equation(S.mix(x, y)).to(x + y)

    m += mix
    m.eval(S.memoize(S.mix, 1))

    memoized = m.fn.is_memoized
    assert memoized(S.mix, 1) == [True]
    assert memoized(S.mix, 2) == [False]

    mixed = m.fn.mix
    assert mixed(5) == [6]
    assert mixed(5) == [6]

    assert mixed(3, 4) == [7]
    assert mixed(3, 4) == [7]

    m.eval(S.memoize(S.mix, 2))
    assert memoized(S.mix, 2) == [True]
    assert mixed(8, 9) == [17]
    assert mixed(8, 9) == [17]
