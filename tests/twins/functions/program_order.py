"""The Python twin of examples/functions/program_order.metta: source order counts.

The call comes before its equation and stays unreduced; the same call after the
equation reduces. A Python twin reads the same way for the same reason, because
statements run in order: the first `m.eval` happens before the `m +=` below it.

The equation is written at the container door, ONE RUNG BELOW the decorator,
because its head fixes a SYMBOL: `(p121-example-respond me)` matches the atom
`me` and nothing else. A stacked `@m.define` clause fixes a head position with
a literal DEFAULT (`def g(n=1)` writes `(= (g 1) 1)`), and a literal is a
bool, int, float or str, never a symbol, so this head has no decorator
spelling. The residue table records that against P14.4, which owns the
subset's growth.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 1223 across the rewrite into the authority's idiom:
#: `expr(S["="], expr(S["p121-example-respond"], S["me"]), S["hello"])`
#: became `equation(S["p121-example-respond"](S.me)).to(S.hello)`. Both
#: build the same atom in Python before the engine sees anything, so the two
#: runnable forms cost what they cost before. Prior: ADDED 2026-08-22 at
#: 1223 by 7f15dc1's wave-3 baseline.
BUDGET = 1223


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(p121-example-respond me)
    yield m.eval(S["p121-example-respond"](S.me))

    # (= (p121-example-respond me) hello)
    m += equation(S["p121-example-respond"](S.me)).to(S.hello)

    # !(test (p121-example-respond me) hello)
    yield m.eval(S.test(S["p121-example-respond"](S.me), S.hello))
