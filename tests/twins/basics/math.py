"""Purpose: examples/basics/math.metta in Python: the numeric surface.

Every `-math` operation is an engine function, so the space's own function
namespace names it once and it is then an ordinary Python callable: `sqrt(9)`
is `(sqrt-math 9)` evaluated, and its answers are `[3.0]`. An operation that
refuses answers an Error ATOM rather than raising, which is why the refusals
below are compared as data, and comparing the whole answer list states the
cardinality as well as the value.

Two namespaces, one split, and this file uses both on purpose. `m.fn.<name>`
is the BOUND namespace: its members evaluate in this space when called.
Package-level `fn.<name>` is the STATIC one: its members are the symbols
themselves, which is what a NESTED argument needs, since `(isnan-math
(sqrt-math -1))` is one term to evaluate once rather than two crossings.

One thing Python's own punctuation will not do here. `==` is Python's own
structural equality on atoms, so MeTTa's `==` and `!=`, which compare NUMERIC
VALUES across int and float, are named at the function-namespace door. The
arithmetic terms whose refusals this file is about ARE written as operators:
one grounded operand stages the term, so `G(7) / 0` builds `(/ 7 0)` rather
than raising ZeroDivisionError.

`min-atom` and `max-atom` dissolve: an expression is a sequence, so Python's
own `min` and `max` read it with no engine crossing at all.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, G, S, fn, ground

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1

#: The six numbers `min-atom` and `max-atom` are asked about.
NUMBERS = Expression((2, 6, 7, 4, 9, 3))


def twin(m):
    """Ask every numeric operation what it answers, refusals included."""
    equal, unequal = m.fn["=="], m.fn["!="]
    divide, remainder = m.fn["/"], m.fn["%"]
    sqrt, power, log = m.fn.sqrt_math, m.fn.pow_math, m.fn.log_math
    isnan, isinf = m.fn.isnan_math, m.fn.isinf_math
    absolute = m.fn.abs_math
    trunc, ceil, floor, rounded = (
        m.fn.trunc_math, m.fn.ceil_math, m.fn.floor_math, m.fn.round_math
    )
    sin, asin, cos, acos = (
        m.fn.sin_math, m.fn.asin_math, m.fn.cos_math, m.fn.acos_math
    )
    tan, atan = m.fn.tan_math, m.fn.atan_math

    # Mixed integer/float equality compares numeric VALUES.
    assert equal(1, 1.0) == [True]
    assert unequal(1.0, 1) == [False]

    # Division and remainder by zero answer contained error atoms, and an
    # error is an ordinary ANSWER: the answer list holds it where a scalar
    # door would raise, and the form after it still runs.
    assert divide(7, 0) == [S.Error(G(7) / 0, S.DivisionByZero)]
    assert remainder(7, 0) == [S.Error(G(7) % 0, S.DivisionByZero)]
    # (collapse (/ 7 0)) adds the cardinality: exactly one answer, and it is
    # that error. `len()` is the size question over the answers a collapse
    # would have built.
    assert len(divide(7, 0)) == 1

    @m.define
    def math_string():
        # (= (math-string) "s")
        return "s"

    # A COMPUTED string reaches the operation's own guard and is refused
    # there, before the host can treat one character as its code.
    assert sqrt(S.math_string()) == [
        S.Error(fn.sqrt_math(ground("s")), S.BadArgType(1, S.Number, S.String))
    ]

    assert power(2, 3) == [8.0]
    assert isnan(fn.sqrt_math(-1)) == [True]
    assert isinf(fn.pow_math(0, -1)) == [True]
    # An integer exponent is bounded to signed i32; a float one is not.
    assert power(2, 2147483648) == [
        S.Error(
            fn.pow_math(2, 2147483648),
            ground("power argument is too big, try using float value"),
        )
    ]
    assert power(1, 2147483648.0) == [1.0]

    # Real-valued operations promote integer operands to Float.
    assert sqrt(9) == [3.0]
    assert absolute(-5) == [5]
    assert log(10, 100) == [2.0]
    assert trunc(5.6) == [5]
    assert ceil(5.2) == [6]
    assert floor(5.8) == [5]
    assert rounded(5.4) == [5]
    assert rounded(5.6) == [6]
    assert sin(0) == [0.0]
    assert asin(0) == [0.0]
    assert cos(0) == [1.0]
    assert acos(1) == [0.0]
    assert tan(0) == [0.0]
    assert atan(0) == [0.0]
    assert isnan(0.0) == [False]
    assert isinf(0.0) == [False]

    # (min-atom (2 6 7 4 9 3)) and (max-atom ...): an expression IS a
    # sequence, so these are Python's own, at no engine cost.
    assert min(NUMBERS) == 2
    assert max(NUMBERS) == 9

    assert isinf(S.inf) == [True]
    assert isnan(S.nan) == [True]
