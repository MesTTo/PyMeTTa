"""Purpose: examples/libraries/he_assert.metta in Python: the assert family itself.

Python's `assert` is what MeTTa's assert family dissolves into, which is why
this one file cannot dissolve it: the twelve functions here ARE the subject, so
each claim is a Python assert ABOUT one of them. That is what the `RUNG`
declaration below records.

Three distinctions the file draws, and they are the reason it exists.
`assertEqual` compares evaluated results, so both sides are built as terms
rather than computed in Python. The `ToResult` forms take the expected results
as a TUPLE and do not evaluate it, so a single result is written `(3)` and not
`3`. The `Alpha` forms compare modulo variable renaming, and the `Msg` variants
add a failure message and otherwise behave as their bases.

`adder` stays at the container door: its body is a bare MeTTa variable, which a
compiled body has no spelling for.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, V, equation

#: Why this twin sits below the top rung: every claim here is about a member of
#: the assert family, so naming them is the file's subject rather than MeTTa
#: written in Python punctuation.
RUNG = "the assert family is this file's subject, so each claim names one of its twelve members"

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Ask each member of the assert family whether it holds."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    assert m.fn.assertEqual(S["+"](1, 2), S["-"](6, 3)) == [True]

    # Comparing modulo variable renaming carries variables by definition, and
    # the call answers the True this family reports all the same.
    alpha_equal = m.fn.assertAlphaEqual
    assert alpha_equal(S.h(V.x, V.y), S.h(V.a, V.b)) == [True]
    assert alpha_equal(S.quote(V.x + V.y), S.quote(V.a + V.b)) == [True]

    # The ToResult forms take the expected results as a tuple, not a bare
    # value, and do not evaluate it. A single result is therefore (3), not 3.
    to_result = m.fn.assertEqualToResult
    assert to_result(S["+"](1, 2), (3,)) == [True]
    assert to_result(S.superpose((1, 2)), (1, 2)) == [True]

    m += equation(S.adder()).to(Expression((V.x,)))
    assert m.fn.assertAlphaEqualToResult(
        S.adder(), (Expression((V.y,)),)
    ) == [True]

    # Every expected result must appear among those produced.
    includes = m.fn.assertIncludes
    assert includes(S.superpose((1, 2, 3)), (2,)) == [True]
    assert includes(S.superpose((1, 2, 3)), (2, 3)) == [True]

    # The Msg variants take a failure message and otherwise behave as their bases.
    assert m.fn.assertEqualMsg(S["+"](1, 2), S["-"](6, 3), G("sums differ")) == [True]
    assert m.fn.assertAlphaEqualMsg(
        S.h(V.x, V.y), S.h(V.a, V.b), G("not alpha equal")
    ) == [True]
    assert m.fn.assertEqualToResultMsg(
        S["+"](1, 2), (3,), G("not the expected result")
    ) == [True]
    assert m.fn.assertAlphaEqualToResultMsg(
        S.adder(), (Expression((V.y,)),), G("not alpha equal")
    ) == [True]
