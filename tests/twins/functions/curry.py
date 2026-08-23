"""Purpose: examples/functions/curry.metta in Python: too few arguments, and too many.

Calling a function with FEWER arguments than it takes answers a partial
application, which prints as `(partial f (1))` and can be called again later.
Calling one with too many is an error, and the error is an ANSWER: nothing
catches it and the form after it still runs.

Four of the five definitions are ordinary Python functions. `h` names the
engine's `append` through the static function namespace, `fn.append`, and
passes `(a,)`, a one-element Python tuple, which is the one-element expression
`($A)` the original writes. `show` names the engine's own `repr` the same way:
Python's builtin `repr` is bridged into a compiled body as `py-repr`, so
`fn.repr` is what stores the equation the original stores.

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

`overloaded-curry` is the one definition that stays at the rule door.
DEFECT, not a missing spelling: its two clauses have DIFFERENT ARITY under one
name, and the shape this file wants,

    @m.define(name="overloaded-curry")
    def overloaded_curry(a):
        return a

    @m.define(name="overloaded-curry")
    def overloaded_curry_3(a, b, c):
        return a + (b + c)

raises `IndexError: list assignment index out of range` inside
`_define_twins.replace_twin_clause`, because two clauses that fix no literal
head are located as a REDEFINITION of each other and the replacement index is
then used against a dispatcher keyed by the PYTHON name, which is a fresh
empty one. The residue table carries the defect and its root cause against
P14.4; `@m.rules` writes both equations with parameter-scoped variables and
takes no such path.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, equation, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Apply four functions with too few arguments, and three with too many."""

    @m.define
    def f(a, b):
        # (= (f $a $b) (+ $a $b))
        return a + b

    @m.define
    def g(a, b, c):
        # (= (g $a $b $c) (+ $c (+ $a $b)))
        return c + (a + b)

    @m.define
    def show():
        # (= (show) (repr (f 1)))
        return fn.repr(f(1))

    assert m.fn.repr(S.f(1)) == ["(partial f (1))"]
    assert m.eval((S.f(1), 2)) == [3]
    assert m.fn.repr(S.g(1, 2)) == ["(partial g (1 2))"]

    @m.define
    def h(a, b):
        # (= (h $A $B) (append ($A) $B))
        return fn.append((a,), b)

    assert m.eval((S.h(42), (1, 2, 3))) == [Expression((42, 1, 2, 3))]
    assert m.fn.repr(S.h(42)) == ["(partial h (42))"]

    # (map-atom (1 2 3) (+ 1)): a comprehension builds the applications and
    # one evaluation runs them.
    add_one = S["+"](1)
    assert m.eval(tuple((add_one, x) for x in (1, 2, 3))) == [Expression((2, 3, 4))]

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
    #
    # DEFECT, and the bundle below is the workaround. The perfect spelling is
    # two clauses under one name,
    #
    #     @m.define(name="overloaded-curry")
    #     def overloaded_curry(a):
    #         return a
    #
    #     @m.define(name="overloaded-curry")
    #     def overloaded_curry_3(a, b, c):
    #         return a + (b + c)
    #
    # and the second decoration raises `IndexError: list assignment index out
    # of range` in `_define_twins.replace_twin_clause`: two clauses that fix no
    # literal head are located as a REDEFINITION of each other, arity is never
    # consulted, and the replacement index is then used against a dispatcher
    # keyed by the PYTHON name, which is a fresh empty one. Either key the twin
    # dispatcher by the MeTTa name, or refuse the second clause with the
    # sentence `_validate_clause_order` already writes
    # [measured 2026-08-23 on this worktree; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    @m.rules
    def overloaded(a, b, c):
        # (= (overloaded-curry $a) $a)
        yield equation(S["overloaded-curry"](a)).to(a)
        # (= (overloaded-curry $a $b $c) (+ $a (+ $b $c)))
        yield equation(S["overloaded-curry"](a, b, c)).to(a + (b + c))

    assert m.fn.repr(S["overloaded-curry"](1, 2)) == [
        "(partial overloaded-curry (1 2))"
    ]
