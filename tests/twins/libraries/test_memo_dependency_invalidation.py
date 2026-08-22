"""examples/libraries/test_memo_dependency_invalidation.metta in Python: cache, then hit.

Two claims over one memoized definition. `double` is compiled from Python and
`memoize` is lib_memo's declaration, which stays named.

The same divergence test_memo_stats records applies: a memoized function called
from Python does not reach the dispatch hook, so the second call recomputes
rather than hitting. Both claims hold either way.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 128629 to 125532, -3097 (-2.41%), by the idiomatic
#: rewrite: two `test` wrappers left the engine for `assert`; the import is
#: almost the whole cost of every lib_memo file, which is why the ratio moves
#: so little. Measured min-of-three with the MORK backend linked into this
#: worktree, which the earlier figure may not have been. Prior: 128629 was
#: the last figure for the generator twin that yielded `m.eval(S.test(...))`
#: once per runnable form.
BUDGET = 125532


def twin(m):
    """Double five twice."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @m.define
    def double(x):
        return x + x

    m.eval(S.memoize(S.double))

    assert double(5) == [10]
    assert double(5) == [10]
