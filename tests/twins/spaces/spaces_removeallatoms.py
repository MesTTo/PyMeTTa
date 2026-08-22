"""The Python twin of examples/spaces/spaces_removeallatoms.metta: emptying a space.

`remove-all-atoms` takes everything with it, the imported library included, which
is why the next form finds `remove-all-atoms` itself undefined and answers the
call unreduced. `(f 42)` goes the same way, and `get-atoms` answers nothing.

The emptying form stays a TERM, and the reason is a measured divergence rather
than a missing door: `m.clear()` is Python's own spelling for emptying a
container and it empties the same space through the same funnel, but it answers
NOTHING, where `(remove-all-atoms &self)` answers one unit per removed atom,
eleven of them here. A twin written at the protocol door would answer `(())`
where the original answers `((() () ...))`, so the cardinality is the residue
entry (P14.10) and the term is what this form keeps.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 23683 to 25312, +1629 (+6.9%), by the P14 twin-style
#: rewrite, and the whole delta is one cause: `(= (f $x) 42)` moved from the
#: container door to @m.define, which is the decorator door's price for the
#: first decorated function in a process (2,244 against the container door's
#: 615, measured in isolation). Every other form is the same term spelled with
#: named symbols and tuples and measures identically; the lib_spaces import
#: still dominates the file. Prior: ADDED 2026-08-22 at 23683 by the wave-3
#: spaces baseline.
BUDGET = 25312


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    here = S[m.space_name]

    # !(import! &self (library lib_spaces))
    yield m.eval(S["import!"](here, S.library(S.lib_spaces)))

    # (friend tim tom)
    m += (S.friend, S.tim, S.tom)

    # (= (f $x) 42)
    @m.define
    def f(_x):
        return 42

    # One unit per atom removed, eleven of them.
    # !(remove-all-atoms &self)
    yield m.eval(S["remove-all-atoms"](here))

    # The library left with everything else, so its own function is undefined
    # now and the call is its own answer.
    # !(test (repr (remove-all-atoms &self)) "(remove-all-atoms &self)")
    yield m.eval(
        S.test(
            S.repr(S["remove-all-atoms"](here)),
            val("(remove-all-atoms &self)"),
        )
    )

    # !(test (repr (f 42)) "(f 42)")
    yield m.eval(S.test(S.repr(S.f(42)), val("(f 42)")))

    # !(test (collapse (get-atoms &self)) ())
    yield m.eval(S.test(S.collapse(S["get-atoms"](here)), ()))
