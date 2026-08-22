"""The Python twin of examples/spaces/spacefunction.metta: removing a definition.

Two identical equations under different names, one of them removed. The removed
one leaves its compiled answer with it, so `(f 3 4)` becomes its own answer while
`(g 3 4)` still reduces to 7. The same happens for a plain fact.

`@m.define` writes the equations and `-=` removes one, which is the reflectivity
invariant in Python dress: a Python-authored definition is an ordinary atom, so
the operator that removes an atom removes it. Each write form answers the unit;
the four assertions after them are what prove which definitions survived.
"""

from petta import S, V, equation, expr

#: The answer group a write form contributes. `add-atom` and `remove-atom` both
#: answer the unit, which is what Python's own None means here (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5262 to 5426, +164 (+3.1%), by the P14 twin-style
#: rewrite, whose two causes nearly cancel and were split by re-measuring this
#: file with only the decorator change reverted: 3,604, twice.
#: Five of the eight forms are writes, and moving them to the container door is
#: worth -1658, about 332 a form against translating and reducing an
#: (add-atom ...) or (remove-atom ...) call. The two equations moved to
#: @m.define, worth +1822, which is the decorator door's DEFINITION-TIME price:
#: ~1,436 one-time for the first decorated function in a process plus ~193 per
#: equation, none of it paid per call.
#: Prior: ADDED 2026-08-22 at 5262 by the wave-3 spaces baseline.
BUDGET = 5426


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    here = S[m.space_name]

    # !(add-atom &self (= (f $x $y) (+ $x $y)))
    @m.define
    def f(x, y):
        return x + y

    yield WROTE

    # !(add-atom &self (= (g $x $y) (+ $x $y)))
    @m.define
    def g(x, y):
        return x + y

    yield WROTE

    # The equation is an atom, so the operator that removes an atom removes it.
    # !(remove-atom &self (= (f $x $y) (+ $x $y)))
    m -= equation(S.f(V.x, V.y)).to(V.x + V.y)
    yield WROTE

    # !(test (f 3 4) (f 3 4))
    yield m.eval(S.test(S.f(3, 4), S.f(3, 4)))

    # !(test (g 3 4) 7)
    yield m.eval(S.test(S.g(3, 4), 7))

    # !(add-atom &self (my test))
    m += (S.my, S.test)
    yield WROTE

    # !(remove-atom &self (my test))
    m -= (S.my, S.test)
    yield WROTE

    # !(test (collapse (match &self (my test) (my test))) ())
    yield m.eval(
        S.test(S.collapse(S.match(here, (S.my, S.test), (S.my, S.test))), ())
    )
