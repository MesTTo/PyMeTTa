"""Purpose: an evolutionary loop where the population is a space and each
generation is space rewriting: variation is Python operations, fitness is an
operation, and the generational loop with its stopping rule is MeTTa source.
The shape MOSES-style program evolution takes on this substrate.
Guarantees:
  - deterministic fitness is pureStructural while random variation and the
    state-rewriting generation step are oracleIO [tested:
    test_example_runs_and_verifies_itself; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import random

from _common import check, done

from metta import MeTTa, S, V, Expression, wire

random.seed(11)
TARGET = [1, 0, 1, 1, 0, 1, 0, 1]
m = MeTTa().space()

for index in range(16):
    genome = [random.randint(0, 1) for _ in TARGET]
    m.add(Expression(S.member, index, Expression(*genome)))


@m.op(effect="pureStructural")
def fitness(genome) -> int:
    bits = [int(wire.decode(b)) for b in genome]
    return sum(1 for got, want in zip(bits, TARGET) if got == want)


@m.op(effect="oracleIO")
def breed(a, b):
    cut = random.randrange(1, len(TARGET))
    bits_a = [int(wire.decode(x)) for x in a]
    bits_b = [int(wire.decode(x)) for x in b]
    child = bits_a[:cut] + bits_b[cut:]
    slot = random.randrange(len(child))
    if random.random() < 0.3:
        child[slot] = 1 - child[slot]
    return Expression(*child)


@m.op(name="next-generation", effect="oracleIO")
def next_generation() -> bool:
    rows = m.match(S.member(V.i, V.g))
    scored = sorted(rows, key=lambda r: -fitness(r.g))
    parents = [r.g for r in scored[: len(scored) // 2]]
    m.run("!(match (context-space) (member $i $g) (remove-atom (context-space) (member $i $g)))")
    for index in range(16):
        a, b = random.sample(parents, 2)
        m.add(Expression(S.member, index, breed(a, b)))
    return True


# The generational loop, stopping rule included, is MeTTa source:
m.run(
    "(= (best) (max-atom (collapse (match (context-space) (member $i $g) (fitness $g)))))\n"
    "(= (evolve! $gen)\n"
    "   (if (== (best) 8)\n"
    "       (Perfect after $gen generations)\n"
    "       (if (> $gen 60)\n"
    "           (Stopped at (best))\n"
    "           (let $next (next-generation) (evolve! (+ $gen 1))))))"
)
(group,) = m.run("!(evolve! 0)")
(outcome,) = group
check("outcome", outcome[0] in (S.Perfect, S.Stopped))
check("population intact", len(m.match(S.member(V.i, V.g))), 16)
best = m.run("!(best)")
check("evolution improved the best genome", best[0][0] >= 7)
done("evolutionary_search")
