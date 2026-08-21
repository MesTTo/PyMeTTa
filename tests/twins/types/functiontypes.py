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

from petta import Atom, S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 9635

#: (a list not a number), the answer that is data rather than arithmetic.
NOT_A_NUMBER = expr(S.a, S["list"], S["not"], S.a, S.number)


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
    m += S[":"](
        S.wu3, S["->"](S.Number, S.Number, S["%Undefined%"])
    )
    # (= (wu3 $a $b) (if (< $a 10) (+ $a $b) (a list not a number)))
    m += S["="](
        S.wu3(V.a, V.b),
        S["if"](
            S["<"](V.a, 10), S["+"](V.a, V.b), NOT_A_NUMBER
        ),
    )

    # quote retains its wrapper in LeaTTa; noeval is the payload-preserving
    # form this expected syntax requires.
    # !(test (wu1 (+ 2 4) (+ 4 2)) (noeval (42 6 (+ 4 2))))
    yield m.eval(
        S.test(
            wu1(S["+"](2, 4), S["+"](4, 2)),
            S.noeval(expr(42, 6, S["+"](4, 2))),
        )
    )

    # !(test (wu2 (+ 2 4) (+ 4 2)) 12)
    yield m.eval(S.test(wu2(S["+"](2, 4), S["+"](4, 2)), 12))

    # !(test (wu3 42 0) (a list not a number))
    yield m.eval(S.test(S.wu3(42, 0), NOT_A_NUMBER))
    # !(test (wu3 2 0) 2)
    yield m.eval(S.test(S.wu3(2, 0), 2))
