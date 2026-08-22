"""The Python twin of examples/spaces/spaces_succeedspredicate.metta: a Prolog goal as a test.

`succeedsPredicate` runs `(<space> <functor> <args>...)` as a goal and answers a
boolean, so an absent fact is False and a present one binds the variables the
goal carried.

`import!` stays a term because it is a directive with no Python door yet
(residue, P14.13); the fact between the two assertions is a plain tuple.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 19938 across the P14 twin-style rewrite: the fact now
#: enters as a tuple and both assertions are built from named symbols, storing
#: and evaluating exactly what the expr() spellings did. Measured 19938 before
#: and after, so this file's cost is the lib_spaces import rather than its own
#: three forms. Prior: ADDED 2026-08-22 at 19938 by the wave-3 spaces baseline.
BUDGET = 19938


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    here = S[m.space_name]

    # !(import! &self (library lib_spaces))
    yield m.eval(S["import!"](here, S.library(S.lib_spaces)))

    # Nothing is stored yet, so the goal fails.
    # !(test (succeedsPredicate (&self friend tim tom)) False)
    yield m.eval(
        S.test(
            S.succeedsPredicate((here, S.friend, S.tim, S.tom)),
            val(value=False),
        )
    )

    # (friend a b)
    m += (S.friend, S.a, S.b)

    # Now it succeeds, and the goal's variables come back bound.
    # !(test (if (succeedsPredicate (&self friend $a $b)) ($a $b) NotFound) (a b))
    yield m.eval(
        S.test(
            S["if"](
                S.succeedsPredicate((here, S.friend, V.a, V.b)),
                (V.a, V.b),
                S.NotFound,
            ),
            (S.a, S.b),
        )
    )
