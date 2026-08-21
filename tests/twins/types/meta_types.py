"""The Python twin of examples/types/meta_types.metta: the four metatypes.

Every atom is one of four kinds, and `get-metatype` says which: `Expression`,
`Grounded`, `Variable`, `Symbol`. The Python surface has one builder per kind
and they line up exactly, which is what this file is: `expr(...)` builds an
Expression, `val(...)` a Grounded, `V.x` a Variable and `S.a` a Symbol.

A grounded number written as a bare `1` in an argument list encodes to the
same `Gnd(1)`, so `S["get-metatype"](1)` is the Grounded case without any
marking.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1936


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    metatype = S["get-metatype"]

    # !(test (get-metatype (foo 1 2)) Expression)
    yield m.eval(S.test(metatype(S.foo(1, 2)), S.Expression))
    # !(test (get-metatype (a b)) Expression)
    yield m.eval(S.test(metatype(expr(S.a, S.b)), S.Expression))
    # !(test (get-metatype 1) Grounded)
    yield m.eval(S.test(metatype(1), S.Grounded))
    # !(test (get-metatype +) Grounded)
    yield m.eval(S.test(metatype(S["+"]), S.Grounded))
    # !(test (get-metatype $x) Variable)
    yield m.eval(S.test(metatype(V.x), S.Variable))
    # !(test (get-metatype a) Symbol)
    yield m.eval(S.test(metatype(S.a), S.Symbol))
