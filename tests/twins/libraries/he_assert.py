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
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation, val

#: Why this twin sits below the top rung: every claim here is about a member of
#: the assert family, so naming them is the file's subject rather than MeTTa
#: written in Python punctuation.
RUNG = "the assert family is this file's subject, so each claim names one of its twelve members"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 21497 to 20065, -1432 (-6.66%), by the idiomatic
#: rewrite: twelve `test` wrappers left the engine for `assert`; the twelve
#: assert-family calls they wrapped are the whole of what remains, which is
#: why this file moves least of the he_ set. Measured min-of-three with the
#: MORK backend linked into this worktree, which the earlier figure may not
#: have been. Prior: 21497 was the last figure for the generator twin that
#: yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 20065


def twin(m):
    """Ask each member of the assert family whether it holds."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    assert m.fn("assertEqual")(S["+"](1, 2), S["-"](6, 3)) is True
    alpha = m.fn("assertAlphaEqual")
    assert alpha(S.h(V.x, V.y), S.h(V.a, V.b)) is True
    assert alpha(S.quote(V.x + V.y), S.quote(V.a + V.b)) is True

    # The ToResult forms take the expected results as a tuple, not a bare
    # value, and do not evaluate it. A single result is therefore (3), not 3.
    to_result = m.fn("assertEqualToResult")
    assert to_result(S["+"](1, 2), (3,)) is True
    assert to_result(S.superpose((1, 2)), (1, 2)) is True

    m += equation(S.adder()).to(Expression((V.x,)))
    assert m.fn("assertAlphaEqualToResult")(S.adder(), (Expression((V.y,)),)) is True

    # Every expected result must appear among those produced.
    includes = m.fn("assertIncludes")
    assert includes(S.superpose((1, 2, 3)), (2,)) is True
    assert includes(S.superpose((1, 2, 3)), (2, 3)) is True

    # The Msg variants take a failure message and otherwise behave as their bases.
    assert m.fn("assertEqualMsg")(S["+"](1, 2), S["-"](6, 3), val("sums differ")) is True
    assert m.fn("assertAlphaEqualMsg")(S.h(V.x, V.y), S.h(V.a, V.b), val("not alpha equal")) is True
    assert m.fn("assertEqualToResultMsg")(S["+"](1, 2), (3,), val("not the expected result")) is True
    assert m.fn("assertAlphaEqualToResultMsg")(S.adder(), (Expression((V.y,)),), val("not alpha equal")) is True
