"""Purpose: examples/types/builin_types.metta in Python: the library's declared types.

Thirty-six names, imported from `lib_builtin_types` and read back. Nothing is
defined here, only asked, so every claim is one line: `space.type(atom)` is the
get-type accessor, and the arrow it should answer is built from PYTHON TYPES
through the one conversion table, `arrow(int, int, int)` for
`(-> Number Number Number)`, so the numeric surface is one shape said many
times and no type atom is spelled by hand.

Two of the arrows carry a type VARIABLE, `(-> $a $a Bool)` for `==` and `!=`,
which is what says both arguments share one type. A variable's identity is
fresh on every answer, so those two are compared with `alpha_eq`, the relation
the law itself uses for answer equivalence, rather than with `==`.

The import itself is an evaluated directive, and its space argument is the
handle: a space crosses a term position as itself, so no `&self` symbol
appears. There is still no Python verb for importing a library (residue,
P14.13).
"""

from metta import S, V, arrow

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Import the library, then read every arrow it declares."""
    binary = arrow(int, int, int)
    unary = arrow(int, int)
    compare = arrow(int, int, bool)
    predicate = arrow(int, bool)
    one_type = arrow(V.a, V.a, bool)
    over_expression = arrow(V.a, int)
    logical = arrow(bool, bool, bool)

    m.fn["import!"](m, S.library(S["lib_builtin_types"]))

    # Arithmetic.
    assert m.type(S["+"]) == binary
    assert m.type(S["-"]) == binary
    assert m.type(S["*"]) == binary
    assert m.type(S["/"]) == binary
    assert m.type(S["%"]) == binary

    # Comparison.
    assert m.type(S["<"]) == compare
    assert m.type(S["<="]) == compare
    assert m.type(S[">"]) == compare
    assert m.type(S[">="]) == compare

    # ONE type variable, twice: == compares two things of one type, and
    # refuses two of different KNOWN types.
    assert m.type(S["=="]).alpha_eq(one_type)
    assert m.type(S["!="]).alpha_eq(one_type)

    # Mathematics.
    assert m.type(S["pow-math"]) == binary
    assert m.type(S["sqrt-math"]) == unary
    assert m.type(S["abs-math"]) == unary
    assert m.type(S["log-math"]) == binary
    assert m.type(S["trunc-math"]) == unary
    assert m.type(S["ceil-math"]) == unary
    assert m.type(S["floor-math"]) == unary
    assert m.type(S["round-math"]) == unary
    assert m.type(S["sin-math"]) == unary
    assert m.type(S["asin-math"]) == unary
    assert m.type(S["cos-math"]) == unary
    assert m.type(S["acos-math"]) == unary
    assert m.type(S["tan-math"]) == unary
    assert m.type(S["atan-math"]) == unary
    assert m.type(S["min-atom"]).alpha_eq(over_expression)
    assert m.type(S["max-atom"]).alpha_eq(over_expression)
    assert m.type(S.min) == binary
    assert m.type(S.max) == binary
    assert m.type(S.exp) == unary

    # The float predicates.
    assert m.type(S["isnan-math"]) == predicate
    assert m.type(S["isinf-math"]) == predicate

    # The boolean operators.
    assert m.type(S["and"]) == logical
    assert m.type(S["or"]) == logical
    assert m.type(S["not"]) == arrow(bool, bool)
    assert m.type(S.xor) == logical
