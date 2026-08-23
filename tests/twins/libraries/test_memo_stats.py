"""examples/libraries/test_memo_stats.metta in Python: one miss, then two hits.

`sq` is an ordinary compiled definition and `memoize` is lib_memo's own
declaration, so it stays named: caching by dependency-aware invalidation is
what the library is for and Python has no word for it.

What this twin cannot show is the caching itself. A memoized function called
through `m.eval`, and therefore through every door over it, does not reach
lib_memo's dispatch hook: with the definition and the memoize both written by a
file, two calls from Python record no hit and no miss where two `!` forms in a
file record one of each. The claims here hold either way, because 81 is 81; the
divergence is in the residue table with its reproduction.
"""

from petta import S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Square nine three times over a memoized definition."""
    m.eval(S["import!"](m, S.library(S["lib_memo"])))

    @m.define
    def sq(x):
        return x * x

    m.eval(S.memoize(S.sq))

    assert sq(9) == [81]
    assert sq(9) == [81]
    assert sq(9) == [81]
