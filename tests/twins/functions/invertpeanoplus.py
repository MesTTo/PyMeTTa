"""The Python twin of examples/functions/invertpeanoplus.metta: Peano addition, run every way.

Two equations define `plus` forwards. `let` then runs them backwards: fix the
sum and one operand and the other comes out bound; fix only the sum and every
pair that reaches it is enumerated; wrap that in `once` and only the first pair
answers.

The definition takes the `@rules` shape of the definitional decorator because both heads
are PATTERNS rather than parameters: `(plus Z $y)` fixes a symbol and
`(plus (S $x) $y)` fixes a whole subterm. A stacked `@m.define` clause fixes a
head position with a literal DEFAULT, and a literal is a bool, int, float or
str, so neither head has a function-shape spelling. The residue table records
that against P14.4. In the equational shape both heads are what they are,
`S.plus(S.Z, y)` and `S.plus(S.S(x), y)`.

The numerals are built by a Python function, since `(S (S (S (S Z))))` is just
`S` applied four times, and writing that out four times in three different
forms is what made the original hard to read.
"""

from petta import S, V, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 12762 to 12781, +19 (+0.15%), and the whole of it is
#: the BATCH door rather than the rewrite: `@rules` builds the identical two
#: equation atoms, and `m.add(a, b)` costs 19 more than `m += a` twice, the
#: fixed cost of the many-wire call. Building the numerals in Python changes
#: nothing the engine sees: `peano(4)` is the same atom the nested calls
#: built, so the five runnable forms cost what they cost before. The lane's
#: parity reads 0.64 of the original. Prior: ADDED 2026-08-22 at 12762 by
#: 7f15dc1's wave-3 baseline.
BUDGET = 12781


def peano(n):
    """The Peano numeral for n: `(S (S ... Z))`, n successors deep."""
    return S.Z if n == 0 else S.S(peano(n - 1))


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @rules
    def plus(x, y):
        # (= (plus Z $y) $y)
        yield equation(S.plus(S.Z, y)).to(y)
        # (= (plus (S $x) $y) (S (plus $x $y)))
        yield equation(S.plus(S.S(x), y)).to(S.S(S.plus(x, y)))

    m.add(*plus)

    # forward: (2+1=3)
    # !(test (plus (S (S Z)) (S Z)) (S (S (S Z))))
    yield m.eval(S.test(S.plus(peano(2), peano(1)), peano(3)))

    # half-inverted (searching for $A): ($A+1=4) -> $A=3
    # !(test (let (plus $A (S Z)) (S (S (S (S Z)))) $A) (S (S (S Z))))
    yield m.eval(
        S.test(S.let(S.plus(V.A, peano(1)), peano(4), V.A), peano(3))
    )

    # half-inverted (searching for $B): (1+$B=4) -> $B=3
    # !(test (let (plus (S Z) $B) (S (S (S (S Z)))) $B) (S (S (S Z))))
    yield m.eval(
        S.test(S.let(S.plus(peano(1), V.B), peano(4), V.B), peano(3))
    )

    # inverted: every input pair that reaches 4.
    # !(test (collapse (let (plus $A $B) (S (S (S (S Z)))) ($A $B)))
    #        ((Z (S (S (S (S Z)))))
    #         ((S Z) (S (S (S Z))))
    #         ((S (S Z)) (S (S Z)))
    #         ((S (S (S Z))) (S Z))
    #         ((S (S (S (S Z)))) Z)))
    yield m.eval(
        S.test(
            S.collapse(S.let(S.plus(V.A, V.B), peano(4), (V.A, V.B))),
            tuple((peano(a), peano(4 - a)) for a in range(5)),
        )
    )

    # inverted, first solution only: ($A,$B)=(0,4)
    # !(test (once (let (plus $A $B) (S (S (S (S Z)))) ($A $B)))
    #        (Z (S (S (S (S Z))))))
    yield m.eval(
        S.test(
            S.once(S.let(S.plus(V.A, V.B), peano(4), (V.A, V.B))),
            (peano(0), peano(4)),
        )
    )
