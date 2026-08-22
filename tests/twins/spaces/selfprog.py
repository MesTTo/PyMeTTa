"""The Python twin of examples/spaces/selfprog.metta: a program editing itself.

An equation is an ordinary atom, so a program removes one and adds another while
it runs, and `repr` shows the answer changing under it: first `(function1)`
unreduced, then `(OK)`.

Both edits go through the container protocol, which is what makes the point:
`m -= equation(...).to(...)` is `(remove-atom &self (= ...))` and `m +=` is the
add, the same operators that move any other knowledge. Each write form answers
the unit, and the assertion after it is what proves the edit landed.
"""

from petta import S, equation, expr, val

#: The answer group a write form contributes. `remove-atom` and `add-atom` both
#: answer the unit, which is what Python's own None means here (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3282 to 4332, +1050 (+32.0%), by the P14 twin-style
#: rewrite, whose two causes pull opposite ways and were split by re-measuring
#: this file with only the decorator change reverted: 2,669, twice.
#: The two edit forms moved to the container door, `m -= equation(...)` and
#: `m += equation(...)`, worth -613 against evaluating (remove-atom ...) and
#: (add-atom ...) terms. The opening equation moved to @m.define, worth +1663,
#: which is the DEFINITION-TIME price of the decorator door: measured in
#: isolation it is ~1,436 of one-time machinery the first decorated function in
#: a process reaches plus ~193 per equation, and none of it is paid per call.
#: Prior: ADDED 2026-08-22 at 3282 by the wave-3 spaces baseline.
BUDGET = 4332


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def function1():
        # (= (function1) OK)
        return OK  # noqa: F821  -- a capitalised free name in a compiled body is a data CONSTRUCTOR, and MeTTa data has no Python value to bind

    # !(remove-atom &self (= (function1) OK))
    m -= equation(S.function1()).to(S.OK)
    yield WROTE

    # With no equation left, the call is its own answer.
    # !(test (repr (function1)) "(function1)")
    yield m.eval(S.test(S.repr(S.function1()), val("(function1)")))

    # !(add-atom &self (= (function1) (OK)))
    m += equation(S.function1()).to(S.OK())
    yield WROTE

    # !(test (repr (function1)) "(OK)")
    yield m.eval(S.test(S.repr(S.function1()), val("(OK)")))
