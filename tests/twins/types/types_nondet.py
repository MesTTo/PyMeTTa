"""examples/types/types_nondet.metta in Python: one name, two signatures.

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
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9449 to 4773, -4676 (-49.49%), by the twin-shape
#: rewrite: three `test` wrappers left the engine for `assert`, and the
#: fourth claim still runs in the engine, through `collapse`, because a flat
#: call at the Python door skips the output-type filter. Against the
#: example's 16134 the ratio is 0.2958 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/types/types_nondet.metta`]. Prior:
#: RE-PINNED at 9449 by P14.8's m.eval fuel-scope alignment.
BUDGET = 4773


def twin(m):
    """Declare two arrows for one name, then watch the output type filter."""
    typed, arrow = S[":"], S["->"]
    alpha = S["=alpha"]

    m += typed(S.f, arrow(S.Type1, S.Type1))
    m += typed(S.f, arrow(S.Type2, S.Type2))

    otherwise = S["if"](alpha(V.a, S.T2in), S.T2out, S.Tdefault)  # rung: the clause is a term because its test is `=alpha` (P14.4)
    m += equation(S.f(V.a)).to(S["if"](alpha(V.a, S.T1in), S.T1out, otherwise))  # rung: same clause, same reason

    m += typed(S.T1in, S.Type1)
    m += typed(S.T1out, S.Type1)
    m += typed(S.T2in, S.Type2)
    m += typed(S.T2out, S.Type2)
    m += typed(S.T3in, S.Type1)
    m += typed(S.Tdefault, S.Type2)

    assert m.fn("f")(S.T1in) == S.T1out
    assert m.fn("f")(S.T2in) == S.T2out

    # Type1 in, Type2 out: no signature admits that, so nothing answers.
    # This one is asked through collapse because a FLAT call at the Python
    # door skips the output-type filter the engine's own form applies and
    # answers Tdefault (filed as friction, with the reproduction).
    assert m.eval(S.collapse(S.f(S.T3in))) == [expr()]  # rung: collapse is list(), but list() over the Python call door would collect an answer the engine does not give

    # Declare T3in a Type2 as well and the Type2 signature admits it.
    m += typed(S.T3in, S.Type2)
    assert m.fn("f")(S.T3in) == S.Tdefault
