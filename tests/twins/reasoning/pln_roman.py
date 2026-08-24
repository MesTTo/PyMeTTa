"""Purpose: examples/reasoning/pln_roman.metta in Python: one bounded PLN proof search.

Four sentences say how strongly A inherits B, A inherits C, B inherits D and C
inherits D, and the query asks what PLN makes of A inheriting D. The answer is
a truth value and the four premises it came from.

`STV` is a `@m.rules` bundle: its four clauses fix a SYMBOL in the head, and a
bundle is the door for equations whose heads are structures rather than
parameter lists. `kb` is one equation whose body is DATA, so it goes through
the write door as the atom it is, and `_sentence` names the shape the four
rows share.

The bounded search is intentionally larger than the evaluator's default fuel,
so the example states its own budget. `max-stack-depth` is branch-local
reduction fuel and has no keyword on `limits()`, which scopes time, inferences
and SWI's stack BYTES, so the pragma is written as the term it is (friction,
P14.14). `with-pragma!` is banged, so the bound namespace performs it on the
line that writes it.
"""

from metta import S, equation

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 3285491, maximum 3285661
#: over 28 observations under `full-lane/218/workers=32`, so the re-pin owes
#: it an envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1

#: How strongly each concept holds on its own, in the example's own order.
STRENGTHS = ((S.A, 0.5), (S.B, 0.25), (S.C, 0.25), (S.D, 0.5))

#: The four premises: a link, its truth value, and its one-item evidence stamp.
PREMISES = ((S.A, S.B, 0.25, 1), (S.A, S.C, 0.25, 2),
            (S.B, S.D, 0.5, 3), (S.C, S.D, 0.5, 4))


def _sentence(left, right, strength, identifier):
    """Build one PLN sentence with its truth value and one-item evidence stamp."""
    return S.Sentence(
        (S.Inheritance(left, right), S.stv(strength, 0.9)),
        (identifier,),
    )


def twin(m):
    """Load PLN, state the Roman-diamond knowledge base, and ask for A to D."""
    # !(import! &self (library lib_pln))
    m.fn["import!"](m, S.library(S["lib_pln"]))

    @m.rules
    def strengths():
        """(= (STV A) (stv 0.5 0.9)), and three more with a symbol in the head."""
        for concept, strength in STRENGTHS:
            yield equation(S.STV(concept)).to(S.stv(strength, 0.9))

    # (= (kb) ((Sentence ((Inheritance A B) (stv 0.25 0.9)) (1)) ...))
    m += equation(S.kb()).to(tuple(_sentence(*premise) for premise in PREMISES))

    # !(test (with-pragma! ((max-stack-depth 100000000))
    #                      (PLN.Query (kb) (Inheritance A D)))
    #        ((stv 0.5 0.9473684210526316) (1 2 3 4)))
    raised_stack = ((S.max_stack_depth, 100_000_000),)
    answer = m.fn.with_pragma(
        raised_stack,
        S["PLN.Query"](S.kb(), S.Inheritance(S.A, S.D)),
    ).one()
    assert answer[0] == S.stv(0.5, 0.9473684210526316)
    assert tuple(answer[1]) == (1, 2, 3, 4)
