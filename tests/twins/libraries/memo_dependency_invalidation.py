"""examples/libraries/memo_dependency_invalidation.metta in Python: cache, then hit.

Two claims over one memoized definition. `double` is compiled from Python and
`memoize` is lib_memo's declaration, which stays named.

The same divergence memo_stats records applies: a memoized function called
from Python does not reach the dispatch hook, so the second call recomputes
rather than hitting. Both claims hold either way.
"""

from metta import S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1


def twin(m):
    """Double five twice."""
    m.fn["import!"](m, S.library(S["lib_memo"]))

    @m.define
    def double(x):
        return x + x

    m.eval(S.memoize(S.double))

    assert double(5) == [10]
    assert double(5) == [10]
