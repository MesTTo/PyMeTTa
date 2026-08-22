"""examples/libraries/lib_roman_pair_helpers.metta in Python: pairs, from lib_roman.

`first` and `second` apply a function to one side of a pair and leave the other
alone; `flip` swaps the sides. All three are the example's subject, so the twin
names them. What is Python's is the function they are given: `(= (inc $x) (+ $x
1))` is an ordinary compiled definition here.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 154076 to 153411, -665 (-0.43%), by the idiomatic
#: rewrite: three `test` wrappers left the engine for `assert`, and `inc` is
#: now compiled by `@m.define` where the source built it as an atom. Measured
#: min-of-three with the MORK backend linked into this worktree, which the
#: earlier figure may not have been. Prior: 154076 was the last figure for
#: the generator twin that yielded `m.eval(S.test(...))` once per runnable
#: form.
BUDGET = 153411


def twin(m):
    """Import lib_roman, define inc, then move it over each side of a pair."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_roman)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @m.define
    def inc(x):
        return x + 1

    first, second, flip = m.fn("first"), m.fn("second"), m.fn("flip")
    assert list(first(S.inc, (1, 9))) == [2, 9]
    assert list(second(S.inc, (1, 9))) == [1, 10]
    assert list(flip((S.left, S.right))) == [S.right, S.left]
