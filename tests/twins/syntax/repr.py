"""The Python twin of examples/syntax/repr.metta: how an atom prints.

`repr` answers the engine's own swrite text for an atom, so this file is six
terms and their expected strings. Two spellings are worth naming.

A plain Python TUPLE builds an expression, so `(, B , C ,)` is written
`(S[","], S.B, S[","], S.C, S[","])`: five children under no head, which is
what that expression is. The subscript is there because `,` is not a Python
identifier, which is the only thing the subscript form is for.

`()` is the empty expression, and Python's own empty tuple encodes to it, so
`S.repr(())` needs no builder call at all.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 3394 across the rewrite into the authority's idiom:
#: every `expr(S["test"], ...)` became `S.test(...)`, `S["repr"]` became
#: `S.repr`, and the two nested expressions became tuples. NOTHING MOVED,
#: which is the point of those three changes: they are spellings of the same
#: atoms, built in Python before the engine sees anything, so the engine
#: does the identical work either way. Prior: ADDED 2026-08-22 at 3394 by
#: 7f15dc1's wave-3 baseline.
BUDGET = 3394


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (repr 42) "42")
    yield m.eval(S.test(S.repr(42), val("42")))
    # !(test (repr "42") "\"42\"")
    yield m.eval(S.test(S.repr(val("42")), val('"42"')))
    # !(test (repr (A (B C))) "(A (B C))")
    yield m.eval(S.test(S.repr(S.A(S.B(S.C))), val("(A (B C))")))
    # !(test (repr (A (, B , C ,))) "(A (, B , C ,))")
    yield m.eval(
        S.test(
            S.repr(S.A((S[","], S.B, S[","], S.C, S[","]))),
            val("(A (, B , C ,))"),
        )
    )
    # !(test (repr 2025_12_12) "2025_12_12")
    yield m.eval(S.test(S.repr(S["2025_12_12"]), val("2025_12_12")))
    # !(test (repr ()) "()")
    yield m.eval(S.test(S.repr(()), val("()")))
