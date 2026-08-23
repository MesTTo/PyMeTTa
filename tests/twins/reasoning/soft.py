"""Purpose: examples/reasoning/soft.metta in Python: weak unification and attention.

`lib_soft` scores two terms against each other: structure crisp, symbols soft,
minimum aggregation, and a variable binding at degree one. `lib_measure` then
turns the scored candidates into a distribution. Every claim is a call on one
of the two libraries.

The zoo is an ordinary space, and the Python variable IS its binding, so it
needs no name: the handle crosses a term position as itself, which is what
`soft-match` receives where the example writes `&zoo`.

The claim that reads a binding is `solve`, the relational `let`: unify the
score against 1.0 and the subject's own `$who` comes back bound to `cat`,
which is exactly what the example's `(let $probe ... ($probe $who))` says.
"""

import metta
from metta import Expression, S, V

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 186644, maximum 186685 over
#: 28 observations under `full-lane/218/workers=32`, so the re-pin owes it an
#: envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Load soft matching, state two similarities, then check all seventeen claims."""
    m.fn["import!"](m, S.library(S["lib_measure"]))
    m.fn["import!"](m, S.library(S["lib_soft"]))

    m += S.similar(S.cat, S.feline, 0.8)
    m += S.similar(S.dog, S.wolf, 0.7)

    sym_sim = m.fn.sym_sim
    soft_score = m.fn.soft_score

    assert sym_sim(S.cat, S.cat).one() == 1.0
    assert sym_sim(S.cat, S.feline).one() == 0.8
    assert sym_sim(S.feline, S.cat).one() == 0.8
    assert sym_sim(S.cat, S.dog).one() == 0.0

    assert soft_score(S.likes(S.cat, S.fish), S.likes(S.cat, S.fish)).one() == 1.0
    assert soft_score(S.likes(S.feline, S.fish), S.likes(S.cat, S.fish)).one() == 0.8
    assert soft_score(S.likes(S.feline, S.wolf), S.likes(S.cat, S.dog)).one() == 0.7
    assert soft_score(S.likes(S.cat), S.likes(S.cat, S.fish)).one() == 0.0
    assert soft_score(S.likes(S.cat, S.fish), S.hates(S.cat, S.fish)).one() == 0.0
    assert soft_score(3, 3).one() == 1.0
    assert soft_score(3, 4).one() == 0.0

    # A variable binds at degree one, and the binding is real.
    assert soft_score(V.x, S.anything).one() == 1.0
    scored = S["soft-score"](S.likes(V.who, S.fish), S.likes(S.cat, S.fish))
    assert m.solve(1.0, scored).who == S.cat

    # Soft matching over a space, feeding the measure algebra.
    zoo = metta.space()
    zoo += S.likes(S.cat, S.fish)
    zoo += S.likes(S.dog, S.bones)
    zoo += S.likes(S.bird, S.seeds)

    soft_match = m.fn.soft_match
    closest = soft_match(zoo, S.likes(S.feline, S.fish), 0.5).one()
    assert tuple(closest) == (0.8, S.likes(S.cat, S.fish))
    assert m.fn.soft_best(zoo, S.likes(S.feline, S.fish)).one() == S.likes(S.cat, S.fish)

    # Attention over terms: every candidate scored, softmaxed into a
    # distribution, which sums to one whatever the temperature.
    # `Expression(answers)` is the collapse door: the scored candidates become
    # ONE ordered atom, which is what the measure algebra takes.
    assert len(soft_match(zoo, S.likes(V.x, V.y), 0.0)) == 3
    candidates = Expression(soft_match(zoo, S.likes(S.feline, V.f), 0.0))
    distribution = m.fn.ws_softmax(candidates, 1.0).one()
    assert abs(m.fn.ws_total(distribution).one() - 1.0) < 1.0e-9
