"""The Python twin of examples/spaces/state.metta: the state cell is a value.

`(new-state V)` answers a cell, `get-state` reads it, and `change-state!` answers
the CELL it wrote, so a write composes with a read in one expression. The type
says what the cell HOLDS.

`bind!` is Python's own name binding, which is what the token was for: the cell
comes back from the engine as an ordinary value and lives in a Python variable
from there, so every later term names the object rather than a symbol. The
binding form answers the unit, and the six assertions after it are what read the
cell back. The residue records this as friction (P14.10): `bind!` is local to the
file-reading program, so the twin holds the cell instead of a name for it.
"""

from petta import S, expr, val

#: The answer group the binding form contributes: `bind!` answers the unit,
#: which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 3971 across the P14 twin-style rewrite: the six terms are
#: the same terms spelled with named symbols and the mechanically transliterated
#: hyphen-to-underscore locals (§9d rule 2), and the cell is still fetched with
#: one m.eval and then passed by identity. Measured 3971 before and after.
#: Prior: ADDED 2026-08-22 at 3971 by the wave-3 spaces baseline.
BUDGET = 3971


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    new_state, get_state = S["new-state"], S["get-state"]
    change_state, get_type = S["change-state!"], S["get-type"]

    # !(bind! state (new-state rest))
    state = m.eval(new_state(S.rest))[0]
    yield WROTE

    # !(test (get-state state) rest)
    yield m.eval(S.test(get_state(state), S.rest))

    # change-state! answers the cell, so the write and the read compose.
    # !(test (get-state (change-state! state active)) active)
    yield m.eval(S.test(get_state(change_state(state, S.active)), S.active))

    # !(test (get-state state) active)
    yield m.eval(S.test(get_state(state), S.active))

    # The type says what the cell HOLDS.
    # !(test (get-type (new-state 5)) (StateMonad Number))
    yield m.eval(S.test(get_type(new_state(5)), S.StateMonad(S.Number)))

    # !(test (get-type (new-state "hi")) (StateMonad String))
    yield m.eval(
        S.test(get_type(new_state(val("hi"))), S.StateMonad(S.String))
    )

    # A cell needs no name at all: built, written and read in place.
    # !(test (get-state (change-state! (new-state 1) 2)) 2)
    yield m.eval(S.test(get_state(change_state(new_state(1), 2)), 2))
