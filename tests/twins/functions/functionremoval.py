"""examples/functions/functionremoval.metta in Python: equations move.

An equation is an ATOM, so it can be taken out of the space and put back, and
the function answers differently while it is gone. When both clauses are gone
`(f g)` matches nothing and answers itself.

Two definitional doors, one per shape. `g` is a computation, so it is a
decorated Python function. `f`'s two clauses are ALTERNATIVES that both
answer, which stacked `@m.define` clauses cannot mean (stacking reads as
first-match, and two clauses fixing no literal head are a redefinition of one
another), so they come from `@rules`: the generator's parameter IS the
equation's variable and each `yield` is one equation.

The point of the file then writes itself, because the two equations are Python
VALUES: named once, they are handed to `-=` and `+=` as the atoms they are.

The last claim reads through the engine's own reducer rather than `m.eval`,
for the reason examples/functions/dispatch_policies.metta's twin measures:
with both clauses gone the call is not reducible, and `m.eval` drops that
answer where a runnable form keeps it.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11719 to 9416, -2303 (-19.7%), by the twin
#: contract change: four `test` wrappers and four `collapse` calls left the
#: engine for `assert` and the answer list, and the four
#: `add-atom`/`remove-atom` forms became `+=` and `-=` over the two named
#: equations. Against the example's 14237 the ratio is 0.6614 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 9416


def twin(m):
    """Take one clause out, put it back, take the other, then both."""

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
        # (= (f $g) 42)
        yield equation(S.f(g)).to(42)

    call, const = clauses
    m.add(call, const)

    assert m.eval(S.f(S.g)) == [2, 42]

    m -= const
    assert m.eval(S.f(S.g)) == [2]

    m += const
    m -= call
    assert m.eval(S.f(S.g)) == [42]

    m -= const
    assert m.fn("reduce").all(S.f(S.g)) == [S.f(S.g)]
