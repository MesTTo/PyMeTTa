"""Purpose: examples/functions/curry.metta in Python: too few arguments, and too many.

Calling a function with FEWER arguments than it takes answers a partial
application, which prints as `(partial f (1))` and can be called again later.
Calling one with too many is an error, and the error is an ANSWER: nothing
catches it and the form after it still runs.

Three of the five definitions are ordinary Python functions. `h` names the
engine's `append`, bound with `m.fn` so the Python side of the twin runs it
too, and passes `(a,)`, a one-element Python tuple, which is the one-element
expression `($A)` the original writes.

`map-atom` dissolves the way the table says: a comprehension builds the three
applications and ONE evaluation runs them, which is the crossing rule as well
as the spelling, since applying a partial per element from Python would cross
three times.

Two spellings Python's operators cannot give. A PARTIAL application of an
operator, `(+ 1)`, has no operator spelling, because `+` needs both operands
to be an operator at all; it is written by CALLING the symbol, `S["+"](1)`,
which is what builds an expression out of a head and its arguments. And
`(+ 1 2 3)` is the same story from the other side, because Python's
`1 + 2 + 3` left-associates into `(+ (+ 1 2) 3)` and would compute 6 before
the engine saw anything.

Two definitions sit one rung below the decorator, each for its own reason.
`(= (show) (repr (f 1)))`: `repr` inside a compiled body is PYTHON's repr,
which the subset routes to `py-repr`, so a decorated `show` would store a
different equation from the one the original stores. And `overloaded-curry` is
two clauses of DIFFERENT ARITY under one name; stacking two
`@m.define(name="overloaded-curry")` clauses raises `IndexError` today,
because two clauses that fix no literal head are located as a redefinition of
each other and the replacement index is then used against a twin dispatcher
keyed by the PYTHON name, which is a fresh empty one. `@rules` writes both
equations with parameter-scoped variables and no such path. The residue table
records both against P14.4.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 14982 to 12965, -2017 (-13.5%), by the twin
#: contract change: ten `test` wrappers left the engine for `assert`, and
#: `map-atom` left it for a comprehension that builds the three
#: applications so ONE evaluation runs them, which is the crossing rule as
#: well as the spelling. Against the example's 21688 the ratio is 0.5978
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 12965


def twin(m):
    """Apply four functions with too few arguments, and three with too many."""
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
    # rung: `repr` in a compiled body is PYTHON's repr, which the subset routes to
    #   py-repr, not the engine's own (residue, P14.4)
    m += equation(S.show()).to(S.repr(S.f(1)))

    assert m.one(S.repr(S.f(1))) == "(partial f (1))"
    assert m.eval((S.f(1), 2)) == [3]
    assert m.one(S.repr(S.g(1, 2))) == "(partial g (1 2))"

    @m.define
    def h(a, b):
        # (= (h $A $B) (append ($A) $B))
        return append((a,), b)

    assert tuple(m.one((S.h(42), (1, 2, 3)))) == (42, 1, 2, 3)
    assert m.one(S.repr(S.h(42))) == "(partial h (42))"

    # (map-atom (1 2 3) (+ 1)): a comprehension builds the applications and
    # one evaluation runs them.
    add_one = S["+"](1)
    assert tuple(m.one(tuple((add_one, x) for x in (1, 2, 3)))) == (2, 3, 4)

    # Too many arguments are an error, both for compiled and for
    # runtime-dispatched calls, and the error is an ANSWER: no catch stands
    # between the call and it. A head nothing TYPES is left as written
    # instead, because there is no arity to be wrong about.
    too_many = S["+"](1, 2, 3)
    wrong_count = S.Error(too_many, S.IncorrectNumberOfArguments)
    assert m.eval(too_many) == [wrong_count]
    assert m.eval(S.reduce(too_many)) == [wrong_count]
    assert m.eval(S.empty(1, 2)) == [S.empty(1, 2)]

    # A gap between overloaded arities is still a valid partial application.
    # rung: two @m.define clauses of one name that fix no literal head raise
    #   IndexError today, and would be a redefinition rather than two arities if
    #   they did not (residue, P14.4)
    @rules
    def overloaded(a, b, c):
        # (= (overloaded-curry $a) $a)
        yield equation(S["overloaded-curry"](a)).to(a)
        # (= (overloaded-curry $a $b $c) (+ $a (+ $b $c)))
        yield equation(S["overloaded-curry"](a, b, c)).to(a + (b + c))

    m.add(*overloaded)

    assert m.one(S.repr(S["overloaded-curry"](1, 2))) == (
        "(partial overloaded-curry (1 2))"
    )
