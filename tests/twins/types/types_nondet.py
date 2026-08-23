"""Purpose: examples/types/types_nondet.metta in Python: one name, two signatures.

`f` is declared for Type1 AND for Type2, so its argument arrives as either and
the OUTPUT type decides which calls survive. `T3in` is a Type1, and a Type1
argument cannot reach a Type2 answer, so `(f T3in)` has no answer at all until
`T3in` is also declared a Type2, at which point the Tdefault branch is
acceptable and answers.

The clause is written as an equation because its body compares with `=alpha`,
which a compiled body has no name for, and because this file's own subject
says why `=alpha` and not `==`: `(== T2in T1in)` compares two KNOWN and
different types, which `==` refuses by name. Both references refuse the `==`
spelling too, hyperon and the mechanised interpreter alike.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, arrow, equation, fn, if_, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Declare two arrows for one name, then watch the output type filter."""
    alpha = fn["=alpha"]

    m += typed(S.f, arrow(S.Type1, S.Type1))
    m += typed(S.f, arrow(S.Type2, S.Type2))

    otherwise = if_(alpha(V.a, S.T2in), S.T2out, S.Tdefault)
    m += equation(S.f(V.a)).to(if_(alpha(V.a, S.T1in), S.T1out, otherwise))

    m += typed(S.T1in, S.Type1)
    m += typed(S.T1out, S.Type1)
    m += typed(S.T2in, S.Type2)
    m += typed(S.T2out, S.Type2)
    m += typed(S.T3in, S.Type1)
    m += typed(S.Tdefault, S.Type2)

    assert m.fn.f(S.T1in) == [S.T1out]
    assert m.fn.f(S.T2in) == [S.T2out]

    # Type1 in, Type2 out: no signature admits that, so nothing answers.
    # This one is asked through collapse because a FLAT call at the Python
    # door skips the output-type filter the engine's own form applies and
    # answers Tdefault (filed as friction, with the reproduction).
    assert m.eval(fn.collapse(S.f(S.T3in))) == [Expression(())]  # rung: collapse is list(), but list() over the Python call door would collect an answer the engine does not give

    # Declare T3in a Type2 as well and the Type2 signature admits it.
    m += typed(S.T3in, S.Type2)
    assert m.fn.f(S.T3in) == [S.Tdefault]
