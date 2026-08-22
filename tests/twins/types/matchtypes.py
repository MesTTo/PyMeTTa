"""The Python twin of examples/types/matchtypes.metta: comparing two types.

A type is an ordinary atom, so comparing two of them is `==` and nothing more.
`match-types` is that comparison wrapped in an `if`, and `match-type-or` layers
one on top: answer True when the two types agree, and the value itself when
they do not.

Both equations are written at the container door, and `match-types` has a second
reason wave one did not record: it is already an engine builtin, so
`@m.define(name="match-types")` refuses with "'match-types' is already a
function this space answers" before the body is even read. `match-type-or`'s
body then CALLS it, and a compiled body resolves a free name EXACTLY, so a
hyphenated function cannot be reached from one (wave one recorded that against
P14.4 for `fibsmart`). Writing one of the pair at each door would say the two
equations differ in kind, and they do not.

The two strings the first two forms answer are DATA, `val(...)`-marked: they
are what the program computes, not what it is written in.
"""

from petta import S, V, equation, val

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `match-types` is already an engine builtin, so the decorator refuses to stack a clause
#: onto it, and `match-type-or`'s body then names it hyphenated, which a compiled body cannot
#: resolve.
RUNG = "container door: match-types is an engine builtin the decorator refuses to stack onto"

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 7016 to 7492, +476, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 7016 by 47554fc's control/types twin baseline.
BUDGET = 7492

MATCHED, MISSED = val("Matched!"), val("Didn't match")


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (match-types $A $B $Then $Else) (if (== $A $B) $Then $Else))
    m += equation(S["match-types"](V.a, V.b, V.then, V.els)).to(S["if"](V.a.eq(V.b), V.then, V.els))

    # !(match-types Atom Atom "Matched!" "Didn't match") answers ("Matched!")
    yield m.eval(S["match-types"](S.Atom, S.Atom, MATCHED, MISSED))
    # !(match-types Atom Number "Matched!" "Didn't match")
    # answers ("Didn't match")
    yield m.eval(S["match-types"](S.Atom, S.Number, MATCHED, MISSED))

    # (= (match-type-or $value $type1 $type2) (match-types $type1 $type2 True $value))
    m += equation(S["match-type-or"](V.value, V.first, V.second)).to(
        S["match-types"](V.first, V.second, TRUE, V.value)
    )

    # !(test (match-type-or True Number Number) True)
    yield m.eval(S.test(S["match-type-or"](TRUE, S.Number, S.Number), TRUE))
    # !(test (match-type-or False Number Number) True)
    yield m.eval(S.test(S["match-type-or"](FALSE, S.Number, S.Number), TRUE))
    # !(test (match-type-or True Number Bool) True)
    yield m.eval(S.test(S["match-type-or"](TRUE, S.Number, S.Bool), TRUE))
    # !(test (match-type-or False Number Bool) False)
    yield m.eval(S.test(S["match-type-or"](FALSE, S.Number, S.Bool), FALSE))
