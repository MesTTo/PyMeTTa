"""The Python twin of examples/types/parametric_types.metta: an arrow argument.

`apply` takes a FUNCTION and its argument, so its own type has an arrow inside
it: `(-> (-> $tx $ty) $tx $ty)`. That declaration is written here as a Python
annotation, which is the door P14.9 names, and it is the case that shows the
projection is structural rather than a lookup table: `Callable[[TX], TY]`
becomes `(-> $tx $ty)` and a `TypeVar` becomes a MeTTa variable, so the whole
parametric signature falls out of the signature a Python reader would write
anyway.

The body is a Python tuple, `(f, x)`, which is the expression `($f $x)`:
applying a function held in a variable is building the expression whose head is
that variable.

The two type variables are minted `TypeVar(name="TX")` rather than
`TypeVar("TX")`. Both are the same object; the keyword is what says the string
is a NAME, which is the one distinction this lane makes about a string in a
twin, and `name=` is how it is marked at any call.
"""

from collections.abc import Callable
from typing import TypeVar

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5694 to 5543, -151, by P14.9's declaration-order
#: correction: @define now adds the annotation-derived parametric signature
#: before storing `apply`'s equation, so clause compilation sees its type.
#: Three fresh processes measured 5543, 5543, 5543. Prior: RE-PINNED
#: 2026-08-22 at 5694 by P14.8's m.eval fuel-scope alignment.
BUDGET = 5543

TX = TypeVar(name="TX")
TY = TypeVar(name="TY")


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def apply(f: Callable[[TX], TY], x: TX) -> TY:
        # (: apply (-> (-> $tx $ty) $tx $ty))
        # (= (apply $f $x) ($f $x))
        return (f, x)

    # !(apply not False) answers (True)
    yield m.eval(S.apply(S["not"], FALSE))
    # !(get-type (apply not False)) answers (Bool)
    yield m.eval(S["get-type"](S.apply(S["not"], FALSE)))
    # !(test (let (get-type apply) (-> (-> Bool Bool) Bool $result) $result) Bool)
    yield m.eval(
        S.test(
            S["let"](
                S["get-type"](S.apply),
                S["->"](
                    S["->"](S.Bool, S.Bool), S.Bool, V.result
                ),
                V.result,
            ),
            S.Bool,
        )
    )
