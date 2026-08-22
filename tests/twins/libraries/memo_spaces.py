"""examples/libraries/memo_spaces.metta in Python: a cache belongs to a space.

Each space compiles its own equations into its own module, so two spaces
defining the same name hold two functions, and each one caches on its own.
Sixteen claims watch that: the two answers stay apart, memoizing one leaves the
other's report false, and changing one space's equation moves only that space's
answer.

`evalc`'s Python image is the space handle itself, which is what makes this
file read: `metric.fn("shipping-cost")(3)` evaluates IN &metric because the
handle carries the space, and the same call on `m` evaluates in &self. No form
here has to name a space at all.

The replacement equation goes to the container door. A second `@m.define` for a
name the space already answers is a redefinition rather than an alternative and
is refused, which the residue table records; the write and read doors take the
old equation away and put the new one in without ceremony.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 144534 to 131884, -12650 (-8.75%), by the idiomatic
#: rewrite: sixteen `test` wrappers left the engine for `assert`, and the
#: `evalc` forms left for the two space handles, which carry their space
#: instead of naming it once per call. Measured min-of-three with the MORK
#: backend linked into this worktree, which the earlier figure may not have
#: been. Prior: 144534 was the last figure for the generator twin that
#: yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 131884


def twin(m):
    """Two spaces, one function name, two caches, and one equation change."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    metric = m.space("&metric")
    metric += equation(S["shipping-cost"](V.w)).to(V.w * 9)

    @m.define(name="shipping-cost")
    def shipping_cost(w):
        return w * 2

    here, there = m.fn("shipping-cost"), metric.fn("shipping-cost")
    memoized, memoized_there = m.fn("is-memoized"), metric.fn("is-memoized")

    assert here(3) == 6
    assert there(3) == 27
    assert memoized(S["shipping-cost"]) is False
    assert memoized_there(S["shipping-cost"]) is False

    # Memoizing here caches this space's function and leaves the other alone.
    m.eval(S.memoize(S["shipping-cost"]))

    assert memoized(S["shipping-cost"]) is True
    assert memoized_there(S["shipping-cost"]) is False

    # Both answers stand, and stand again on the call that hits the cache.
    assert here(3) == 6
    assert here(3) == 6
    assert there(3) == 27
    assert there(3) == 27

    # Memoizing the other space's function adds a second cache, not a shared one.
    metric.eval(S.memoize(S["shipping-cost"]))

    assert memoized_there(S["shipping-cost"]) is True
    assert there(3) == 27
    assert there(3) == 27
    assert here(3) == 6

    # Changing one space's equation invalidates that space's cache and answers
    # the new value, while the other space keeps answering its own.
    m -= equation(S["shipping-cost"](V.w)).to(V.w * 2)
    m += equation(S["shipping-cost"](V.w)).to(V.w * 3)

    assert here(3) == 9
    assert there(3) == 27
