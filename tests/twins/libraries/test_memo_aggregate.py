"""examples/libraries/test_memo_aggregate.metta in Python: the one claim Python cannot make.

`(config-memoize (aggregate sum))` folds a ground call's answers into one
cached value, so `(choices 5)` answers 18 rather than 5, 6 and 7. The folding
happens INSIDE the cache path, and a memoized function called from Python never
reaches lib_memo's dispatch hook, so from here the call answers all three. The
claim is a declined residue entry with its reproduction, not a silent gap.

What this twin does state is the half that does hold: the mode is accepted and
readable, and setting it back to `none` restores the default for whatever runs
next in the same process, which is why the example ends the way it does.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 130374 to 127849, -2525 (-1.94%), by the idiomatic
#: rewrite: the one `test` wrapper left with the claim it wrapped, which is
#: now declined because the fold happens inside a cache the Python call door
#: does not reach; what replaces it is two reads of the memoize
#: configuration. Measured min-of-three with the MORK backend linked into
#: this worktree, which the earlier figure may not have been. Prior: 130374
#: was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 127849


def twin(m):
    """Ask for a summing cache, build the function, and read the mode back."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    config = m.fn("config-memoize")
    config(S.aggregate(S.sum))

    @rules
    def choices(x):
        yield equation(S.choices(x)).to(x)
        yield equation(S.choices(x)).to(x + 1)
        yield equation(S.choices(x)).to(x + 2)

    m.add(*choices)
    m.eval(S.memoize(S.choices))

    assert S.aggregate(S.sum) in m.fn("get-memoize-config")()

    # Restore the default mode: the counters and the configuration are
    # process-global, so a later run in the same process would inherit this one.
    config(S.aggregate(S.none))
    assert S.aggregate(S.none) in m.fn("get-memoize-config")()
