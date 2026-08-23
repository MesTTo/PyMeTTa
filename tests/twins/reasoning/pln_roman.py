"""Purpose: examples/reasoning/pln_roman.metta in Python: one bounded PLN proof search.

Four sentences say how strongly A inherits B, A inherits C, B inherits D and C
inherits D, and the query asks what PLN makes of A inheriting D. The answer is
a truth value and the four premises it came from.

`STV` and `kb` are written as the equations they are: `STV`'s four clauses fix
a SYMBOL in the head, which a compiled parameter list spells only as a literal
default, and `kb`'s body is DATA rather than a computation. The bounded search
is intentionally larger than the evaluator's default fuel, so the example
states its own budget and the twin evaluates the same scoped pragma.
"""

from metta import S, equation, fn

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 3285491, maximum 3285661
#: over 28 observations under `full-lane/218/workers=32`, so the re-pin owes
#: it an envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def _sentence(left, right, strength, identifier):
    """Build one PLN sentence with its truth value and one-item evidence stamp."""
    return S.Sentence(
        (S.Inheritance(left, right), S.stv(strength, 0.9)),
        (identifier,),
    )


def twin(m):
    """Load PLN, state the Roman-diamond knowledge base, and ask for A to D."""
    m.fn["import!"](m, S.library(S["lib_pln"]))

    for concept, strength in (
        (S.A, 0.5),
        (S.B, 0.25),
        (S.C, 0.25),
        (S.D, 0.5),
    ):
        m += equation(S.STV(concept)).to(S.stv(strength, 0.9))

    m += equation(S.kb()).to(
        (
            _sentence(S.A, S.B, 0.25, 1),
            _sentence(S.A, S.C, 0.25, 2),
            _sentence(S.B, S.D, 0.5, 3),
            _sentence(S.C, S.D, 0.5, 4),
        )
    )

    raised_stack = ((S["max-stack-depth"], 100_000_000),)
    answer = m.answers(
        fn.with_pragma(
            raised_stack,
            S["PLN.Query"](S.kb(), S.Inheritance(S.A, S.D)),
        )
    ).one()
    assert answer[0] == S.stv(0.5, 0.9473684210526316)
    assert tuple(answer[1]) == (1, 2, 3, 4)
