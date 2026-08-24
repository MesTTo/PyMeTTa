"""Purpose: examples/types/types_nondet.metta in Python: one name, two signatures.

`f` is declared for Type1 AND for Type2, so its argument arrives as either and
the OUTPUT type decides which calls survive. `T3in` is a Type1, and a Type1
argument cannot reach a Type2 answer, so `(f T3in)` has no answer at all until
`T3in` is also declared a Type2, at which point the Tdefault branch is
acceptable and answers.

The two arrows are written as the atoms they are, because one Python signature
cannot say two, and the def itself carries no annotations, so it publishes no
third arrow of its own. Its body is Python's own `if` chain, which lowers to
the example's nested conditional exactly; the comparison is `=alpha` and not
`==` for this file's own reason: `(== T2in T1in)` compares two KNOWN and
different types, which `==` refuses by name. Both references refuse the `==`
spelling too, hyperon and the mechanised interpreter alike.
"""

from metta import UNIT, S, arrow, fn, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
BUDGET = 1


def twin(m):
    """Declare two arrows for one name, then watch the output type filter."""
    # (: f (-> Type1 Type1)) (: f (-> Type2 Type2))
    m += typed(S.f, arrow(S.Type1, S.Type1))
    m += typed(S.f, arrow(S.Type2, S.Type2))

    @m.define
    def f(a):
        """(= (f $a) (if (=alpha $a T1in) T1out (if (=alpha $a T2in) T2out Tdefault)))."""
        if fn["=alpha"](a, S.T1in):
            return S.T1out
        if fn["=alpha"](a, S.T2in):
            return S.T2out
        return S.Tdefault

    # (: T1in Type1) (: T1out Type1) (: T2in Type2) (: T2out Type2)
    # (: T3in Type1) (: Tdefault Type2)
    for name, declared in (
        (S.T1in, S.Type1),
        (S.T1out, S.Type1),
        (S.T2in, S.Type2),
        (S.T2out, S.Type2),
        (S.T3in, S.Type1),
        (S.Tdefault, S.Type2),
    ):
        m += typed(name, declared)

    # !(test (f T1in) T1out)
    assert f(S.T1in) == [S.T1out]
    # !(test (f T2in) T2out)
    assert f(S.T2in) == [S.T2out]

    # Type1 in, Type2 out: no signature admits that, so nothing answers.
    # This one is asked through collapse because a FLAT call at the Python
    # door skips the output-type filter the engine's own form applies and
    # answers Tdefault (friction, P14.9, with the reproduction).
    # !(test-no-answer (f T3in))
    assert m.eval(fn.collapse(S.f(S.T3in))) == [UNIT]  # rung: collapse is list(), but list() over the Python call door would collect an answer the engine does not give

    # Declare T3in a Type2 as well and the Type2 signature admits it.
    # (: T3in Type2)
    # !(test (f T3in) Tdefault)
    m += typed(S.T3in, S.Type2)
    assert f(S.T3in) == [S.Tdefault]
