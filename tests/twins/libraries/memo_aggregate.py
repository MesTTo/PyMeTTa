"""examples/libraries/memo_aggregate.metta in Python: the one claim Python cannot make.

`(config-memoize (aggregate sum))` folds a ground call's answers into one
cached value, so `(choices 5)` answers 18 rather than 5, 6 and 7. The folding
happens INSIDE the cache path, and a memoized function called from Python never
reaches lib_memo's dispatch hook, so from here the call answers all three. The
claim is a declined residue entry with its reproduction, not a silent gap.

What this twin does state is the half that does hold: the mode is accepted and
readable, and setting it back to `none` restores the default for whatever runs
next in the same process, which is why the example ends the way it does.

A call through the function namespace is LAZY unless its resolved MeTTa name
ends in `!`, the effect marker, and `config-memoize` carries none: creating
the answer view performs no engine work, so `config(S.aggregate(S.sum))`
written for its EFFECT alone would silently do nothing and every later claim
would read the old mode. Both calls therefore state the `True` they answer,
which both pulls them and says what they answered.
"""

from petta import S, equation, rules

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Ask for a summing cache, build the function, and read the mode back."""
    m.fn["import!"](m, S.library(S["lib_memo"]))

    config = m.fn.config_memoize
    assert config(S.aggregate(S.sum)) == [True]

    @rules
    def choices(x):
        yield equation(S.choices(x)).to(x)
        yield equation(S.choices(x)).to(x + 1)
        yield equation(S.choices(x)).to(x + 2)

    m += choices
    m.eval(S.memoize(S.choices))

    read_config = m.fn.get_memoize_config
    [declared] = read_config()
    assert S.aggregate(S.sum) in declared

    # Restore the default mode: the counters and the configuration are
    # process-global, so a later run in the same process would inherit this one.
    assert config(S.aggregate(S.none)) == [True]
    [restored] = read_config()
    assert S.aggregate(S.none) in restored
