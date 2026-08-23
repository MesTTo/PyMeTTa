"""examples/libraries/memo_spaces.metta in Python: a cache belongs to a space.

Each space compiles its own equations into its own module, so two spaces
defining the same name hold two functions, and each one caches on its own.
Sixteen claims watch that: the two answers stay apart, memoizing one leaves the
other's report false, and changing one space's equation moves only that space's
answer.

`evalc`'s Python image is the space handle itself, which is what makes this
file read: `metric.fn.shipping_cost(3)` evaluates IN &metric because the handle
carries the space, and the same call on `m` evaluates in &self. No form here
has to name a space at all.

The replacement equation goes to the container door. A second `@m.define` for a
name the space already answers is a redefinition rather than an alternative and
is refused, which the residue table records; the write and read doors take the
old equation away and put the new one in without ceremony.
"""

import petta
from petta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Two spaces, one function name, two caches, and one equation change."""
    m.eval(S["import!"](m, S.library(S["lib_memo"])))

    metric = petta.space("&metric")
    metric += equation(S["shipping-cost"](V.w)).to(V.w * 9)

    @m.define(name="shipping-cost")
    def shipping_cost(w):
        return w * 2

    here, there = m.fn.shipping_cost, metric.fn.shipping_cost
    memoized, memoized_there = m.fn.is_memoized, metric.fn.is_memoized

    assert here(3) == [6]
    assert there(3) == [27]
    assert memoized(S["shipping-cost"]) == [False]
    assert memoized_there(S["shipping-cost"]) == [False]

    # Memoizing here caches this space's function and leaves the other alone.
    m.eval(S.memoize(S["shipping-cost"]))

    assert memoized(S["shipping-cost"]) == [True]
    assert memoized_there(S["shipping-cost"]) == [False]

    # Both answers stand, and stand again on the call that hits the cache.
    assert here(3) == [6]
    assert here(3) == [6]
    assert there(3) == [27]
    assert there(3) == [27]

    # Memoizing the other space's function adds a second cache, not a shared one.
    metric.eval(S.memoize(S["shipping-cost"]))

    assert memoized_there(S["shipping-cost"]) == [True]
    assert there(3) == [27]
    assert there(3) == [27]
    assert here(3) == [6]

    # Changing one space's equation invalidates that space's cache and answers
    # the new value, while the other space keeps answering its own.
    m -= equation(S["shipping-cost"](V.w)).to(V.w * 2)
    m += equation(S["shipping-cost"](V.w)).to(V.w * 3)

    assert here(3) == [9]
    assert there(3) == [27]
