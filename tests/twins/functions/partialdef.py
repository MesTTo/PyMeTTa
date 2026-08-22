"""The Python twin of examples/functions/partialdef.metta: a definition answering a partial application.

`(mp)` answers `(+)`, which takes both its arguments later, so `(mp 1 1)` is 2.
`..` composes two partial applications, and `(plus1times2)` answers that
composition, so `(plus1times2 1)` is `(1 + 1) * 2`.

`..` is a decorated Python function under `name=".."`, because `..` is not a
Python identifier while its BODY is ordinary Python: `f1(f2(arg))` applies two
parameters in turn, which is the variable-head application the subset already
reads.

The other two definitions take the `@rules` shape of the definitional decorator,
because their bodies are partial applications of OPERATORS: `(+)` and `(* 2)`
and `(+ 1)` cannot be written with Python's `+` and `*`, which need both
operands to be operators at all. A tuple IS an expression, so `(S["+"],)` is
`(+)` and `(S["*"], 2)` is `(* 2)`. `plus1times2` also calls `..`, which no
Python identifier spells.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3935 to 5503, +1568 (+39.85%), and ALL of it is one
#: definition: `..` costs 702 as an equation atom and 2270 through
#: `@m.define`, +1568. It is the FIRST decorated definition in this process,
#: so it carries the one-time setup as well as its own compile (a decorated
#: definition costs 2244 against the atom door's 600 for one equation the
#: first time and 793 against 600 every time after). The first runnable form
#: costs 1335 either way and the second is unchanged too, because both doors
#: land the same three equations. The lane's parity reads 0.83 of the
#: original. Prior: ADDED 2026-08-22 at 3935 by 7f15dc1's wave-3 baseline.
BUDGET = 5503


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (mp) (+))
    # rung: below the function shape: the body is `(+)`, a zero-argument application of
    #   an operator head, which no Python spelling reaches (residue, P14.4)
    m += equation(S.mp()).to((S["+"],))

    # !(test (mp 1 1) 2)
    yield m.eval(S.test(S.mp(1, 1), 2))

    @m.define(name="..")
    def compose(f1, f2, arg):
        # (= (.. $f1 $f2 $arg) ($f1 ($f2 $arg)))
        return f1(f2(arg))

    # (= (plus1times2) (.. (* 2) (+ 1)))
    # rung: below the function shape: the body calls `..`, which no Python identifier
    #   spells, and holds two operator partials (residue, P14.4)
    m += equation(S.plus1times2()).to(S[".."]((S["*"], 2), (S["+"], 1)))

    # !(test (plus1times2 1) 4)
    yield m.eval(S.test(S.plus1times2(1), 4))
