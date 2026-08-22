"""The Python twin of examples/functions/invertfunction.metta: functions run backwards.

`let` unifies its pattern with what its second argument PRODUCES, so
destructuring a list with `cons` and destructuring it with an ordinary user
function are the same act: the call runs backwards and its variables come out
bound. The last form does it through arithmetic, where `#+` is the constraint
path, so `(g $X $Y 35)` solves `$X + 35 = 42`.

`f` is an ordinary Python function: `append((x,), y)` is `(append ($X) $Y)`,
where the one-element Python tuple is the one-element expression.

`g` takes the `@rules` shape of the definitional decorator, because its body names
`#+`, which no Python identifier spells; in the equational shape it is the
ordinary subscripted symbol the subscript form exists for.
"""

from petta import S, V, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6229 to 8043, +1814 (+29.12%), and ALL of it is one
#: definition: `f` costs 940 as an equation atom and 2754 through
#: `@m.define`, +1814. It is the FIRST decorated definition in this process,
#: so it carries the one-time setup as well as its own compile (2244 against
#: the atom door's 600 for one equation the first time, 793 against 600
#: after). `g` costs 1272 either way and the three runnable forms cost 1363
#: and 1553 unchanged, because both doors land the same two equations. The
#: lane's parity reads 0.74 of the original. Prior: ADDED 2026-08-22 at 6229
#: by 7f15dc1's wave-3 baseline.
BUDGET = 8043


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    append = m.fn("append")

    @m.define
    def f(x, y):
        # (= (f $X $Y) (append ($X) $Y))
        return append((x,), y)

    @rules
    def constrained(x, y, z):
        # (= (g $X $Y $Z) (append ((#+ $X $Z)) $Y))
        yield equation(S.g(x, y, z)).to(S.append(((S["#+"], x, z),), y))

    m.add(*constrained)

    # List destructuring:
    # !(test (let (cons $Head $Tail) (1 2 3 4 5 6) ($Head $Tail)) (1 (2 3 4 5 6)))
    yield m.eval(
        S.test(
            S.let(S.cons(V.Head, V.Tail), (1, 2, 3, 4, 5, 6), (V.Head, V.Tail)),
            (1, (2, 3, 4, 5, 6)),
        )
    )

    # But instead it works for any relational functions:
    # !(test (let (f $Head $Tail) (1 2 3 4 5 6) ($Head $Tail)) (1 (2 3 4 5 6)))
    yield m.eval(
        S.test(
            S.let(S.f(V.Head, V.Tail), (1, 2, 3, 4, 5, 6), (V.Head, V.Tail)),
            (1, (2, 3, 4, 5, 6)),
        )
    )

    # More complex case:
    # !(test (let (g $X $Y 35) (42 2 3) ($X $Y 40)) (7 (2 3) 40))
    yield m.eval(
        S.test(
            S.let(S.g(V.X, V.Y, 35), (42, 2, 3), (V.X, V.Y, 40)),
            (7, (2, 3), 40),
        )
    )
