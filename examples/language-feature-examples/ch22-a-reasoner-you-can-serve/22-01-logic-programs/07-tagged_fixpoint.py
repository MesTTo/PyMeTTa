"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/07-tagged_fixpoint.metta in Python: a tagged program's fixpoint under several carriers.

The same graph with a cycle, written through the tagged doors, asked with
`match(..., under=carrier)`. The engine takes the fixpoint route for the
cyclic rules under a carrier whose combine is idempotent, and `derivations=False`
asks for it on the acyclic graph too. `formula` then `.under(prob)` is the
MeTTa `(formula prob)`: the exact probability, shared edges counted once.
"""

import metta
from metta import S, V


def _graph(space, edges):
    for start, end, weight in edges:
        space.add_tagged_fact(weight, S.edge(start, end))
    space.add_tagged_rule(1, S.path(V.x, V.y), S.edge(V.x, V.y))
    space.add_tagged_rule(1, S.path(V.x, V.z), S.edge(V.x, V.y), S.path(V.y, V.z))


def twin(m):
    """The strongest, the cheapest, the exact and the counted path."""
    _graph(m, ((S.a, S.b, 0.6), (S.b, S.a, 0.5), (S.a, S.c, 0.2), (S.b, S.c, 0.3)))
    query = S.path(S.a, S.c)

    # bool is max of products: the direct 0.2 beats 0.6 * 0.3, the cycle adds nothing.
    assert abs(m.match(query, under=metta.bool).one().annotation - 0.2) < 1e-9
    # tropical is min of sums, each rule adding its own tag 1.
    assert abs(m.match(query, under=metta.tropical).one().annotation - 1.2) < 1e-9
    # Every pair the cycle reaches from a, once each.
    assert len(list(m.match(S.path(S.a, V.y), under=metta.set))) == 3
    # The exact probability: the formula read back under prob.
    exact = m.match(query, under=metta.formula).one().under(metta.prob).annotation
    assert abs(exact - (1 - (1 - 0.2) * (1 - 0.6 * 0.3))) < 1e-6

    # On an acyclic graph every carrier is exact on the fixpoint route.
    dag = metta.space()
    _graph(dag, ((S.a, S.b, 0.6), (S.b, S.c, 0.5), (S.a, S.c, 0.2)))
    assert dag.match(query, under=metta.counting).one().annotation == 2
    assert abs(dag.match(query, under=metta.prob, derivations=False).one().annotation - 0.5) < 1e-9


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. Its first reading was 757958 inferences, 24.5x the
#: example's, every `match(under=)` reading the whole catalog into Python to
#: find one annotations row; the catalog reads became pattern matches and the
#: twin dropped to below the original [measured 2026-09-18: 26374 inferences,
#: 0.8538x the example's 30891, min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/07-tagged_fixpoint.metta;
#: commit=12609a929638e7a2b08d3ff8f517abc1a399e7a9].
BUDGET = 26374
