"""examples/libraries/test_memo_multi_answer.metta in Python: caching a function that answers twice.

Two equations share one head, so they are two ALTERNATIVES rather than a
redefinition, and `@rules` is the door that says that: the generator's
parameter IS the equations' variable, and both land through one write.

The answers are compared as a sorted multiset rather than in clause order.
`memoize` recompiles by removing each equation and adding it back, which
reverses the order the clauses answer in, and answer order is unspecified while
multiplicity is not, so the set is what the claim can be about.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 129174 to 124847, -4327 (-3.35%), by the idiomatic
#: rewrite: two `test` wrappers and the tuple comparison left the engine for
#: `assert` over a sorted multiset; the two alternatives now arrive through
#: one `@rules` write. Measured min-of-three with the MORK backend linked
#: into this worktree, which the earlier figure may not have been. Prior:
#: 129174 was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 124847

#: Both answers for `(choose 7)`, in the order `sorted(key=str)` puts them.
BOTH = [S.Pair(7, 7), 7]


def twin(m):
    """Two answers for one call, before and after the cache."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @rules
    def choose(x):
        yield equation(S.choose(x)).to(x)
        yield equation(S.choose(x)).to(S.Pair(x, x))

    m.add(*choose)
    m.eval(S.memoize(S.choose))

    answers = m.fn("choose")
    assert sorted(answers.all(7), key=str) == BOTH
    assert sorted(answers.all(7), key=str) == BOTH
