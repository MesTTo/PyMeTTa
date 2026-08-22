"""The Python twin of examples/libraries/memo_spaces.metta.

Memoization belongs to a space, not to a function name: two spaces defining
`shipping-cost` hold two functions, and each caches on its own.

Both of this space's equations are written by `@m.define`. The second one
re-decorates the same head, which is what redefinition means on the Python
side: the decorator takes the earlier equation out and puts the new one in,
which is exactly what the source spells as `remove-atom` followed by a fresh
equation, so the removal stays the visible runnable form it is in the original.
The redefinition has to REUSE the Python function name, which is why the second
decoration carries a `noqa: F811`: the clause table is keyed by the MeTTa name
and the twin dispatcher by the Python one, so a fresh Python name would address
an empty dispatcher and raise IndexError. The residue table records that
against P14.4.

The other space's equation is data written through `add-atom`, so it is built
with `equation(...).to(...)` and handed to the form.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 142268 to 144534, +2266 (+1.59%), by the P14
#: twin-style rewrite: both of this space's equations are now compiled from
#: Python syntax by @m.define instead of added as already-built atoms, and
#: the second decoration also RETIRES the first clause through the definition
#: machinery rather than only adding an atom. Two compiles plus one
#: retirement cost 2,266 inferences over the two atom adds they replace.
#: Prior: ADDED 2026-08-22 at 142268 by the wave-3 libraries baseline, which
#: recorded no cause.
BUDGET = 144534


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # !(bind! &metric (new-space))
    yield m.eval(S["bind!"](S["&metric"], S["new-space"]()))

    # !(add-atom &metric (= (shipping-cost $w) (* $w 9)))
    yield m.eval(
        S["add-atom"](S["&metric"], equation(S["shipping-cost"](V.w)).to(V.w * 9))
    )

    @m.define(name="shipping-cost")
    def shipping_cost(w):
        # (= (shipping-cost $w) (* $w 2))
        return w * 2

    # !(test (shipping-cost 3) 6)
    yield m.eval(S.test(S["shipping-cost"](3), 6))
    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(S.test(S.evalc(S["shipping-cost"](3), S["&metric"]), 27))
    # !(test (is-memoized shipping-cost) false)
    yield m.eval(S.test(S["is-memoized"](S["shipping-cost"]), FALSE))
    # !(test (evalc (is-memoized shipping-cost) &metric) false)
    yield m.eval(
        S.test(S.evalc(S["is-memoized"](S["shipping-cost"]), S["&metric"]), FALSE)
    )

    # Memoizing here caches this space's function and leaves the other alone.
    # !(memoize shipping-cost)
    yield m.eval(S.memoize(S["shipping-cost"]))

    # !(test (is-memoized shipping-cost) true)
    yield m.eval(S.test(S["is-memoized"](S["shipping-cost"]), TRUE))
    # !(test (evalc (is-memoized shipping-cost) &metric) false)
    yield m.eval(
        S.test(S.evalc(S["is-memoized"](S["shipping-cost"]), S["&metric"]), FALSE)
    )

    # Both answers stand, and stand again on the call that hits the cache.
    # !(test (shipping-cost 3) 6)
    yield m.eval(S.test(S["shipping-cost"](3), 6))
    # !(test (shipping-cost 3) 6)
    yield m.eval(S.test(S["shipping-cost"](3), 6))
    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(S.test(S.evalc(S["shipping-cost"](3), S["&metric"]), 27))
    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(S.test(S.evalc(S["shipping-cost"](3), S["&metric"]), 27))

    # Memoizing the other space's function adds a second cache, not a shared one.
    # !(evalc (memoize shipping-cost) &metric)
    yield m.eval(S.evalc(S.memoize(S["shipping-cost"]), S["&metric"]))

    # !(test (evalc (is-memoized shipping-cost) &metric) true)
    yield m.eval(
        S.test(S.evalc(S["is-memoized"](S["shipping-cost"]), S["&metric"]), TRUE)
    )
    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(S.test(S.evalc(S["shipping-cost"](3), S["&metric"]), 27))
    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(S.test(S.evalc(S["shipping-cost"](3), S["&metric"]), 27))
    # !(test (shipping-cost 3) 6)
    yield m.eval(S.test(S["shipping-cost"](3), 6))

    # Changing one space's equation invalidates that space's cache and answers
    # the new value, while the other space keeps answering its own.
    # !(remove-atom &self (= (shipping-cost $w) (* $w 2)))
    yield m.eval(
        S["remove-atom"](S["&self"], equation(S["shipping-cost"](V.w)).to(V.w * 2))
    )

    @m.define(name="shipping-cost")
    def shipping_cost(w):  # noqa: F811  -- re-decorating the same name IS redefinition: the decorator takes the old equation out and puts the new one in
        # (= (shipping-cost $w) (* $w 3))
        return w * 3

    # !(test (shipping-cost 3) 9)
    yield m.eval(S.test(S["shipping-cost"](3), 9))
    # !(test (evalc (shipping-cost 3) &metric) 27)
    yield m.eval(S.test(S.evalc(S["shipping-cost"](3), S["&metric"]), 27))
