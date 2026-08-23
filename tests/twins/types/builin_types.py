"""Purpose: examples/types/builin_types.metta in Python: the library's declared types.

Thirty-six names, imported from `lib_builtin_types` and read back. Nothing is
defined here, only asked, so every claim is one line: `space.type(atom)` is the
get-type accessor, and the arrow it should answer is built from PYTHON TYPES
through the one conversion table, `arrow(int, int, int)` for
`(-> Number Number Number)`, so the numeric surface is one shape said many
times and no type atom is spelled by hand.

The heads being asked about are the operators themselves, and the operator WORD
table names each one at the attribute door: `S.add` IS `+` and `S.le` IS `<=`,
which is rung 4 of the descent ladder rather than rung 5's bracket. Three heads
have no word and keep the bracket, because `and`, `or` and `not` are Python
keywords the factory cannot spell as attributes. `truediv` is the roster's one
flagged pair (appendix 13), and it is the shipped word for `/`.

Two of the arrows carry a type VARIABLE, `(-> $a $a Bool)` for `==` and `!=`,
which is what says both arguments share one type. A variable's identity is
fresh on every answer, so those two are compared with `alpha_eq`, the relation
the law itself uses for answer equivalence, rather than with `==`.

The import itself is an evaluated directive, and its space argument is the
handle: a space crosses a term position as itself, so no `&self` symbol
appears. There is still no Python verb for importing a library (friction,
P14.13).
"""

from metta import S, V, arrow

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
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

    # !(import! &self (library lib_builtin_types))
    m.fn["import!"](m, S.library(S["lib_builtin_types"]))

    # Arithmetic: five heads, one arrow.
    # !(test (get-type +) (-> Number Number Number)), and four of the same shape
    assert m.type(S.add) == binary
    assert m.type(S.sub) == binary
    assert m.type(S.mul) == binary
    assert m.type(S.truediv) == binary
    assert m.type(S.mod) == binary

    # Comparison: four heads, one arrow.
    # !(test (get-type <) (-> Number Number Bool)), and three of the same shape
    assert m.type(S.lt) == compare
    assert m.type(S.le) == compare
    assert m.type(S.gt) == compare
    assert m.type(S.ge) == compare

    # ONE type variable, twice: == compares two things of one type, and
    # refuses two of different KNOWN types.
    # !(test (get-type ==) (-> $a $a Bool))
    # !(test (get-type !=) (-> $a $a Bool))
    assert m.type(S.eq).alpha_eq(one_type)
    assert m.type(S.ne).alpha_eq(one_type)

    # Mathematics: the hyphenated names take rung 4's underscore map.
    # !(test (get-type pow-math) (-> Number Number Number)), and eighteen more
    assert m.type(S.pow) == binary
    assert m.type(S.sqrt_math) == unary
    assert m.type(S.abs_math) == unary
    assert m.type(S.log_math) == binary
    assert m.type(S.trunc_math) == unary
    assert m.type(S.ceil_math) == unary
    assert m.type(S.floor_math) == unary
    assert m.type(S.round_math) == unary
    assert m.type(S.sin_math) == unary
    assert m.type(S.asin_math) == unary
    assert m.type(S.cos_math) == unary
    assert m.type(S.acos_math) == unary
    assert m.type(S.tan_math) == unary
    assert m.type(S.atan_math) == unary
    assert m.type(S.min_atom).alpha_eq(over_expression)
    assert m.type(S.max_atom).alpha_eq(over_expression)
    assert m.type(S.min) == binary
    assert m.type(S.max) == binary
    assert m.type(S.exp) == unary

    # The float predicates.
    # !(test (get-type isnan-math) (-> Number Bool))
    # !(test (get-type isinf-math) (-> Number Bool))
    assert m.type(S.isnan_math) == predicate
    assert m.type(S.isinf_math) == predicate

    # The boolean operators. Three of the four are Python keywords, so they
    # take rung 5's bracket; `xor` is an ordinary name with no operator word.
    # !(test (get-type and) (-> Bool Bool Bool)), and three more
    assert m.type(S["and"]) == logical
    assert m.type(S["or"]) == logical
    assert m.type(S["not"]) == arrow(bool, bool)
    assert m.type(S.xor) == logical
