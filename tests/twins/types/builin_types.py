"""examples/types/builin_types.metta in Python: the library's declared types.

Thirty-six names, imported from `lib_builtin_types` and read back. Nothing is
defined here, only asked, so every claim is one line: the declared type of a
NAME is a property of its function object, and the arrow it should be is an
ordinary expression built once and reused, because MeTTa's numeric surface is
one shape said many times.

Two of the arrows carry a type VARIABLE, `(-> $a $a Bool)` for `==` and `!=`,
which is what says both arguments share one type. A variable's identity is
fresh on every answer, so those two are compared with `alpha_eq`, the relation
the law itself uses for answer equivalence, rather than with `==`.
"""

from petta import S, V, alpha_eq

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 146130 to 136493, -9637 (-6.59%), by the twin-shape
#: rewrite: the thirty-six `test` wrappers left the engine for Python's own
#: `assert`, and each question is now the function object's `type` property
#: rather than a `(get-type name)` term the engine has to reduce. The import
#: is most of what remains. Against the example's 161661 the ratio is 0.8443
#: [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/builin_types.metta`]. Prior: RE-PINNED at 142406 then
#: 146130 by P14.8's m.eval fuel-scope alignment.
BUDGET = 136493


def twin(m):
    """Import the library, then read every arrow it declares."""
    arrow = S["->"]
    binary = arrow(S.Number, S.Number, S.Number)
    unary = arrow(S.Number, S.Number)
    compare = arrow(S.Number, S.Number, S.Bool)
    predicate = arrow(S.Number, S.Bool)
    one_type = arrow(V.a, V.a, S.Bool)
    over_expression = arrow(V.a, S.Number)
    logical = arrow(S.Bool, S.Bool, S.Bool)

    m.eval(S["import!"](S["&self"], (S.library, S.lib_builtin_types)))  # rung: import! is a directive with no Python door, and its space sits in a term position (P14.13)

    # Arithmetic.
    assert m.fn("+").type == binary
    assert m.fn("-").type == binary
    assert m.fn("*").type == binary
    assert m.fn("/").type == binary
    assert m.fn("%").type == binary

    # Comparison.
    assert m.fn("<").type == compare
    assert m.fn("<=").type == compare
    assert m.fn(">").type == compare
    assert m.fn(">=").type == compare

    # ONE type variable, twice: == compares two things of one type, and
    # refuses two of different KNOWN types.
    assert alpha_eq(m.fn("==").type, one_type)
    assert alpha_eq(m.fn("!=").type, one_type)

    # Mathematics.
    assert m.fn("pow-math").type == binary
    assert m.fn("sqrt-math").type == unary
    assert m.fn("abs-math").type == unary
    assert m.fn("log-math").type == binary
    assert m.fn("trunc-math").type == unary
    assert m.fn("ceil-math").type == unary
    assert m.fn("floor-math").type == unary
    assert m.fn("round-math").type == unary
    assert m.fn("sin-math").type == unary
    assert m.fn("asin-math").type == unary
    assert m.fn("cos-math").type == unary
    assert m.fn("acos-math").type == unary
    assert m.fn("tan-math").type == unary
    assert m.fn("atan-math").type == unary
    assert alpha_eq(m.fn("min-atom").type, over_expression)
    assert alpha_eq(m.fn("max-atom").type, over_expression)
    assert m.fn("min").type == binary
    assert m.fn("max").type == binary
    assert m.fn("exp").type == unary

    # The float predicates.
    assert m.fn("isnan-math").type == predicate
    assert m.fn("isinf-math").type == predicate

    # The boolean operators.
    assert m.fn("and").type == logical
    assert m.fn("or").type == logical
    assert m.fn("not").type == arrow(S.Bool, S.Bool)
    assert m.fn("xor").type == logical
