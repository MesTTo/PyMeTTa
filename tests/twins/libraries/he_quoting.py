"""Purpose: examples/libraries/he_quoting.metta in Python: what stays unevaluated.

`quote` is an ordinary constructor and `unquote` undoes it, so both stay named:
they are the file's subject. Everything around them is Python's own.

Evaluating a term is `space.answers(term).one()`. Printing one is `str`,
because a built atom already prints as engine-exact swrite text, which is what
MeTTa's `repr` answers. And `noreduce-eq`, which compares two terms WITHOUT
reducing them, is Python's `==` on atoms: outside a compiled body
`S["+"](1, 2) == 3` is structural equality between an expression and a number,
and it is False for exactly the reason the example gives.

`(+ 1 2)` is built by naming the head. The guide's grounded lift, `G(1) + 2`,
would be the operator spelling for it, and it is not the shipped behaviour:
`Grounded` arithmetic COMPUTES, so that expression answers the integer 3 and
the quotation this file is about would have nothing left to quote.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Quote a sum, unquote it, print it, and compare it unreduced."""
    m.eval(S["import!"](m, S.library(S["lib_he"])))

    quoted = S.quote(S["+"](1, 2))
    assert m.eval(quoted) == [quoted]

    assert m.answers(S["+"](1, 2)).one() == 3
    assert m.fn.unquote(quoted) == [3]

    # Printing an atom is what MeTTa's repr answers, character for character.
    assert str(S.unquote(42)) == "(unquote 42)"

    # Comparing without reducing is Python's own structural equality.
    assert S["+"](1, 2) == S["+"](1, 2)
    assert S["+"](1, 2) != 3
