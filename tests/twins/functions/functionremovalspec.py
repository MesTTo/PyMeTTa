"""examples/functions/functionremovalspec.metta in Python: removal under specialization.

`f` applies its argument, so a call `(f g)` SPECIALIZES on `g`; removing one
of `f`'s two clauses must leave the specialized call working over the clause
that remains, and putting the clause back must bring its answer back.

`g` is a computation, so it is a decorated Python function. `f`'s two clauses
are ALTERNATIVES that both answer, which stacked `@m.define` clauses cannot
mean, so they come from `@rules`, whose parameter IS the equation's variable.
Naming the two equations is what lets `-=` and `+=` take them as the atoms
they are.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11696 to 10392, -1304 (-11.1%), by the twin
#: contract change: three `test` wrappers and one `collapse` left the
#: engine for `assert` and the answer list, and the two
#: `add-atom`/`remove-atom` forms became `+=` and `-=`. Against the
#: example's 13525 the ratio is 0.7684 [measured 2026-08-22 min-of-3,
#: `twin_coverage.py --measure`]. The old figure priced a different
#: program.
BUDGET = 10392


def twin(m):
    """Remove one clause of a specialized function, then put it back."""

    @m.define
    def g(x):
        # (= (g $x) (+ $x 1))
        return x + 1

    # rung: the two clauses are ALTERNATIVES that both answer, which stacked
    #   @m.define clauses read as first-match (residue, P14.4)
    @rules
    def clauses(g):
        # (= (f $g) ($g 1))
        yield equation(S.f(g)).to((g, 1))
        # (= (f $g) ($g 2))
        yield equation(S.f(g)).to((g, 2))

    one, two = clauses
    m.add(one, two)

    assert m.eval(S.f(S.g)) == [2, 3]

    m -= one
    # The specialized call still runs, over the one clause left.
    assert m.eval(S.f(S.g)) == [3]

    m += one
    assert m.eval(S.f(S.g)) == [3, 2]
