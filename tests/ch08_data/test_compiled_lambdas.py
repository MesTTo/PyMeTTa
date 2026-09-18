"""Purpose: a compiled lambda is applicable where it stands and syntax where a function returns it.

Guarantees:
  - a lambda in argument or let position lowers to the bare `|->`, the form
    the engine's higher-order heads apply, so `fn.maplist(lambda a: ..., items)`
    compiles to the example's `(maplist (|-> ($a) ...) $items)` and a bound
    lambda applies to its argument [tested:
    test_a_compiled_lambda_is_applied_where_it_stands; commit=e59104aced3902c3ca0ba5fa87fc93bc5dceb38a]
  - a lambda a function returns is its quoted `|->` syntax, which a caller
    rebuilds through the contract the compiler published and applies from
    Python [tested: test_a_returned_lambda_is_its_syntax; commit=e59104aced3902c3ca0ba5fa87fc93bc5dceb38a]
  - a positional call of a bound callee is the plain application, so a
    parameter holding a defined function's symbol applies as `(f (f x))`
    [tested: test_a_compiled_lambda_is_applied_where_it_stands; commit=e59104aced3902c3ca0ba5fa87fc93bc5dceb38a]
"""

from collections.abc import Callable

from metta import Expression, MeTTa, S, convert, fn


def test_a_compiled_lambda_is_applied_where_it_stands():
    """`maplist` receives a closure, a let-bound lambda applies, a bound callee applies."""
    with MeTTa() as context:
        m = context.self

        @m.define
        def increment_all(items):
            return fn.maplist(lambda a: fn.add(1, a), items)

        @m.define
        def inc(n: int) -> int:
            return n + 1

        @m.define
        def apply_twice(f, x):
            g = lambda y: f(f(y))  # noqa: E731 -- the binding is the point: it stores a `|->`
            return g(x)

        assert increment_all((1, 2, 3)) == [Expression((2, 3, 4))]
        assert apply_twice(inc, 5) == [7]
        equations = [
            atom for atom in m.atoms()
            if isinstance(atom, Expression) and str(atom).startswith("(= (increment-all ")
        ]
        assert len(equations) == 1
        assert "(maplist (|-> " in str(equations[0])
        assert "noeval" not in str(equations[0])


def test_a_returned_lambda_is_its_syntax():
    """A function returning a lambda answers the `|->`, which the convert door rebuilds and applies."""
    with MeTTa() as context:
        m = context.self

        @m.define
        def make_adder(n: int) -> Callable[[int], int]:
            return lambda a: a + n

        answer = m.eval(S["make-adder"](3))
        assert len(answer) == 1
        assert isinstance(answer[0], Expression)
        assert answer[0].head == S["|->"]
        # A lambda from a plain function carries no lexical home in its
        # image, so the caller names the home it rebuilds in.
        adder = convert.build(answer[0], Callable[[int], int], space=m)
        assert adder(4) == 7
