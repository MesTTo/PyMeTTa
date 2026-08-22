"""examples/libraries/test_memo_same_name_multi_arity.metta in Python: two arities, cached apart.

`mix` answers at one and at two arguments, and each arity carries its own
cache: memoizing one leaves the other alone, which is what `is-memoized`
reports here five times. Both equations come through `@rules`, for the reason
test_memo_per_arity gives.

`is-memoized` answers a boolean, so the claims are `is True` and `is False`
rather than comparisons against the symbols the example prints.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 134736 to 127720, -7016 (-5.21%), by the idiomatic
#: rewrite: nine `test` wrappers left the engine for `assert`, and the two
#: arities arrive through one `@rules` write. Measured min-of-three with the
#: MORK backend linked into this worktree, which the earlier figure may not
#: have been. Prior: 134736 was the last figure for the generator twin that
#: yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 127720


def twin(m):
    """Cache one arity of a name, then the other, and watch both report."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @rules
    def mix(x, y):
        yield equation(S.mix(x)).to(x + 1)
        yield equation(S.mix(x, y)).to(x + y)

    m.add(*mix)
    m.eval(S.memoize(S.mix, 1))

    memoized = m.fn("is-memoized")
    assert memoized(S.mix, 1) is True
    assert memoized(S.mix, 2) is False

    mixed = m.fn("mix")
    assert mixed(5) == 6
    assert mixed(5) == 6

    assert mixed(3, 4) == 7
    assert mixed(3, 4) == 7

    m.eval(S.memoize(S.mix, 2))
    assert memoized(S.mix, 2) is True
    assert mixed(8, 9) == 17
    assert mixed(8, 9) == 17
