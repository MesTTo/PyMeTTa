"""The Python twin of examples/functions/dispatch_policies.metta: a dispatch override.

`(only-a A)` answers `hit`; `(only-a B)` matches no clause, and the catalogued
default leaves such a call UNREDUCED, so it answers itself. Adding
`(dispatch-policy only-a NoMatchEnum NoMatchFail)` to `&petta` overrides that
for this one function, so the call fails instead and collapses to `()`;
removing the override restores the default on the same call.

The override is an ordinary atom in an ordinary space, so setting it is
`add-atom` and clearing it is `remove-atom`: the library steers from inside
MeTTa rather than through a Python knob.

The equation is written at the container door, ONE RUNG BELOW the decorator,
because its head fixes a SYMBOL: `(only-a A)` matches the atom `A`. A stacked
`@m.define` clause fixes a head position with a literal default, and a literal
is a bool, int, float or str, never a symbol, so this head has no decorator
spelling. The residue table records that against P14.4.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 4594 across the rewrite into the authority's idiom:
#: the equation became `equation(...).to(...)`, every `expr(S["test"], ...)`
#: became `S.test(...)`, and the override atom is now named once and reused
#: instead of built twice. All three are Python-side spellings of the same
#: atoms, so the five runnable forms cost what they cost before. Prior:
#: ADDED 2026-08-22 at 4594 by 7f15dc1's wave-3 baseline.
BUDGET = 4594


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    #: The override, written once and used three times: set, then cleared.
    policy = S["dispatch-policy"](S["only-a"], S.NoMatchEnum, S.NoMatchFail)

    # (= (only-a A) hit)
    # rung: below the function shape: the head fixes the SYMBOL A, and a stacked
    #   clause's literal default is a bool, int, float or str (residue, P14.4)
    m += equation(S["only-a"](S.A)).to(S.hit)

    # !(test (only-a B) (only-a B))
    yield m.eval(S.test(S["only-a"](S.B), S["only-a"](S.B)))

    # !(add-atom &petta (dispatch-policy only-a NoMatchEnum NoMatchFail))
    yield m.eval(S["add-atom"](S["&petta"], policy))

    # !(test (collapse (only-a B)) ())
    yield m.eval(S.test(S.collapse(S["only-a"](S.B)), ()))

    # !(remove-atom &petta (dispatch-policy only-a NoMatchEnum NoMatchFail))
    yield m.eval(S["remove-atom"](S["&petta"], policy))

    # !(test (only-a B) (only-a B))
    yield m.eval(S.test(S["only-a"](S.B), S["only-a"](S.B)))
