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

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 128946 to 125604, -3342 (-2.59%), by the idiomatic
#: rewrite: three `test` wrappers left the engine for `assert`; `sq` is now
#: compiled by `@m.define` where the source wrote the equation. Measured min-
#: of-three with the MORK backend linked into this worktree, which the
#: earlier figure may not have been. Prior: 128946 was the last figure for
#: the generator twin that yielded `m.eval(S.test(...))` once per runnable
#: form.
BUDGET = 125604


def twin(m):
    """Square nine three times over a memoized definition."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @m.define
    def sq(x):
        return x * x

    m.eval(S.memoize(S.sq))

    assert sq(9) == [81]
    assert sq(9) == [81]
    assert sq(9) == [81]
