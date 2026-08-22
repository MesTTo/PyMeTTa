"""The Python twin of examples/functions/curry.metta: too few arguments, and too many.

Calling a function with fewer arguments than it takes answers a PARTIAL
application, which prints as `(partial f (1))` and can be called again later.
Calling one with too many is an error, and the error is an ANSWER: nothing
catches it and the form after it still runs.

Four of the five definitions are ordinary Python functions. `h` names the
engine's `append`, bound with `m.fn` so the Python side of the twin can run it
too, and passes `(a,)`, a one-element Python tuple, which is the one-element
expression `($A)` the original writes.

Two spellings the file needs and Python's operators cannot give.

A PARTIAL application of an operator, `(+ 1)`, has no operator spelling,
because `+` needs both operands to be an operator at all. It is written as the
tuple `(S["+"], 1)`: a tuple IS an expression, and its head here happens to be
the symbol `+`. `(+ 1 2 3)` is the same story from the other side, since
Python's `1 + 2 + 3` left-associates into `(+ (+ 1 2) 3)` and would compute 6
before the engine ever saw it.

Two definitions sit one rung below the decorator, each for its own reason.

`(= (show) (repr (f 1)))`: `repr` inside a compiled body is PYTHON's repr,
which the subset routes to `py-repr`, so a decorated `show` would store a
different equation from the one the original stores.

`overloaded-curry` is two clauses of DIFFERENT ARITY under one name, and
stacking two `@m.define(name="overloaded-curry")` clauses raises
`IndexError: list assignment index out of range` today: two clauses that fix no
literal head are located as a redefinition of each other, and the replacement
index is then used against a twin dispatcher keyed by the PYTHON name, which is
a fresh empty one. `@rules` writes both equations with parameter-scoped
variables and no such path.

The residue table records both against P14.4.
"""

from petta import S, equation, rules, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 12763 to 14982, +2219 (+17.39%), by the rewrite onto
#: the decorator, and every inference of it lands in the three steps that
#: install definitions; the other seven runnable forms cost 848, 756, 715,
#: 970, 882, 762 and 702 either way, unchanged. Installing `f` and `g` costs
#: 1565 as atoms and 3387 decorated, +1822, nearly all of it the one-time
#: setup the FIRST decorated definition in a process pays (2244 against the
#: atom door's 600 for one equation, where every later one costs 793 against
#: 600). Installing `h` costs 931 against 1309 in this file's own nesting,
#: +378, of which 100 is the decorator's extra work when a callee (`append`)
#: is a closure cell rather than a module global. The two `overloaded-curry`
#: equations now enter through one `m.add` instead of two `m +=`, +19, the
#: fixed cost of the many-wire add. 1822 + 378 + 19 = 2219, the whole of it.
#: The lane's parity reads 0.69 of the original. Prior: ADDED 2026-08-22 at
#: 12763 by 7f15dc1's wave-3 baseline.
BUDGET = 14982


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    append = m.fn("append")

    @m.define
    def f(a, b):
        # (= (f $a $b) (+ $a $b))
        return a + b

    @m.define
    def g(a, b, c):
        # (= (g $a $b $c) (+ $c (+ $a $b)))
        return c + (a + b)

    # (= (show) (repr (f 1)))
    # rung: below the function shape: `repr` in a compiled body is PYTHON's repr, which
    #   the subset routes to py-repr, not the engine's own (residue, P14.4)
    m += equation(S.show()).to(S.repr(S.f(1)))

    # !(test (repr (f 1)) "(partial f (1))")
    yield m.eval(S.test(S.repr(S.f(1)), val("(partial f (1))")))

    # !(test ((f 1) 2) 3)
    yield m.eval(S.test((S.f(1), 2), 3))

    # !(test (repr (g 1 2)) "(partial g (1 2))")
    yield m.eval(S.test(S.repr(S.g(1, 2)), val("(partial g (1 2))")))

    @m.define
    def h(a, b):
        # (= (h $A $B) (append ($A) $B))
        return append((a,), b)

    # !(test ((h 42) (1 2 3)) (42 1 2 3))
    yield m.eval(S.test((S.h(42), (1, 2, 3)), (42, 1, 2, 3)))

    # !(test (repr (h 42)) "(partial h (42))")
    yield m.eval(S.test(S.repr(S.h(42)), val("(partial h (42))")))

    # !(test (map-atom (1 2 3) (+ 1)) (2 3 4))
    yield m.eval(S.test(S["map-atom"]((1, 2, 3), (S["+"], 1)), (2, 3, 4)))

    # Too many arguments are an error, both for compiled and runtime-dispatched
    # calls, and the error is an ANSWER: no catch stands between the call and
    # it, and the form after it still runs. A head nothing TYPES is left as
    # written instead, because there is no arity to be wrong about.
    # !(test (+ 1 2 3) (Error (+ 1 2 3) IncorrectNumberOfArguments))
    yield m.eval(
        S.test((S["+"], 1, 2, 3), S.Error((S["+"], 1, 2, 3), S.IncorrectNumberOfArguments))
    )

    # !(test (reduce (+ 1 2 3)) (Error (+ 1 2 3) IncorrectNumberOfArguments))
    yield m.eval(
        S.test(
            S.reduce((S["+"], 1, 2, 3)),
            S.Error((S["+"], 1, 2, 3), S.IncorrectNumberOfArguments),
        )
    )

    # !(test (empty 1 2) (empty 1 2))
    yield m.eval(S.test(S.empty(1, 2), S.empty(1, 2)))

    # A gap between overloaded arities is still a valid partial application.
    # rung: below the function shape: two @m.define clauses of one name that fix no
    #   literal head raise IndexError today, and would be a redefinition rather than
    #   two arities if they did not (residue, P14.4)
    @rules
    def overloaded(a, b, c):
        # (= (overloaded-curry $a) $a)
        yield equation(S["overloaded-curry"](a)).to(a)
        # (= (overloaded-curry $a $b $c) (+ $a (+ $b $c)))
        yield equation(S["overloaded-curry"](a, b, c)).to(a + (b + c))

    m.add(*overloaded)

    # !(test (repr (overloaded-curry 1 2)) "(partial overloaded-curry (1 2))")
    yield m.eval(
        S.test(
            S.repr(S["overloaded-curry"](1, 2)),
            val("(partial overloaded-curry (1 2))"),
        )
    )
