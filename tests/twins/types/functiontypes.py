"""The Python twin of examples/types/functiontypes.metta: declared signatures.

Three declared functions, and what each declaration does to the arguments and
the result. `wu1` takes its second argument as `Atom`, so `(+ 4 2)` reaches the
body unrun; `wu2` is `Number` throughout and adds; `wu3` answers a plain
expression on one branch and a number on the other, which `%Undefined%` allows.

`wu1` and `wu2` state their types as Python ANNOTATIONS, the door P14.9 names:
the decorator reads the signature and writes `(: name (-> ...))` into the
space, so the type is written once and the engine checks it. `int` projects to
`Number`, `Any` to `%Undefined%`, and `Atom`, the library's own base class, to
the `Atom` metatype.

`wu3` is written at the container door because its second branch answers
`(a list not a number)`, four lowercase SYMBOLS: a compiled body resolves a
lowercase free name as a function and reads a capitalised one as a
constructor, which wave one recorded against P14.4 for `time_and_pragmas`.
"""

from typing import Any

from petta import Atom, S, V, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: two drops. `wu3`'s second branch answers `(a list not a number)`, four lowercase
#: SYMBOLS a compiled body has no spelling for. And the `(+ 2 4)` arguments have two GROUND operands
#: each, where Python's `+` computes the sum instead of building the term `wu1` receives unrun.
RUNG = (
    "container door for wu3's four lowercase symbols, plus ground operands in the (+ 2 4) arguments"
)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10035 to 9738, -297, by P14.9's declaration-order
#: correction: @define now adds each annotation-derived `(: name type)` before
#: storing its equation, so type-directed clause compilation sees `wu1` and
#: `wu2` as declared. Three fresh processes measured 9738, 9738, 9738. Prior:
#: RE-PINNED 2026-08-22 at 10035 by P14.8's m.eval fuel-scope alignment.
BUDGET = 9738

#: (a list not a number), the answer that is data rather than arithmetic.
NOT_A_NUMBER = (S.a, S.list, S["not"], S.a, S.number)


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def wu1(a: int, b: Atom) -> Any:
        # (: wu1 (-> Number Atom %Undefined%))
        # (= (wu1 $a $b) (42 $a $b))
        return (42, a, b)

    @m.define
    def wu2(a: int, b: int) -> int:
        # (: wu2 (-> Number Number Number))
        # (= (wu2 $a $b) (+ $a $b))
        return a + b

    # (: wu3 (-> Number Number %Undefined%))
    m += S[":"](S.wu3, S["->"](S.Number, S.Number, S["%Undefined%"]))
    # (= (wu3 $a $b) (if (< $a 10) (+ $a $b) (a list not a number)))
    m += equation(S.wu3(V.a, V.b)).to(S["if"](V.a < 10, V.a + V.b, NOT_A_NUMBER))

    # quote retains its wrapper in LeaTTa; noeval is the payload-preserving
    # form this expected syntax requires.
    # !(test (wu1 (+ 2 4) (+ 4 2)) (noeval (42 6 (+ 4 2))))
    yield m.eval(
        S.test(
            S.wu1(S["+"](2, 4), S["+"](4, 2)),
            S.noeval((42, 6, S["+"](4, 2))),
        )
    )

    # !(test (wu2 (+ 2 4) (+ 4 2)) 12)
    yield m.eval(S.test(S.wu2(S["+"](2, 4), S["+"](4, 2)), 12))

    # !(test (wu3 42 0) (a list not a number))
    yield m.eval(S.test(S.wu3(42, 0), NOT_A_NUMBER))
    # !(test (wu3 2 0) 2)
    yield m.eval(S.test(S.wu3(2, 0), 2))
