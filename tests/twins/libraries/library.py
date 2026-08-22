"""examples/libraries/library.metta in Python: lib_roman's flat map.

One claim, and both halves of it are MeTTa's own: `map-flat` is the library
function under test and `(+ 1)` is a partial application, which Python spells
with `functools.partial` over host callables and not over an engine function.
So the twin names both and states the answer as an ordinary list comparison.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 151231 to 150953, -278 (-0.18%), by the idiomatic
#: rewrite: the one `test` wrapper left the engine for `assert`. The
#: lib_roman import is 99% of this file either way, which is why the ratio
#: barely moves. Measured min-of-three with the MORK backend linked into this
#: worktree, which the earlier figure may not have been. Prior: 151231 was
#: the last figure for the generator twin that yielded `m.eval(S.test(...))`
#: once per runnable form.
BUDGET = 150953


def twin(m):
    """Import lib_roman, then map (+ 1) over three numbers."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_roman)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    assert list(m.fn("map-flat")(S["+"](1), (1, 2, 3))) == [2, 3, 4]
