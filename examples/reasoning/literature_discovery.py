"""Purpose: literature-based discovery as one neurosymbolic query: a
hypothesis no paper states, found across a vocabulary gap no symbolic prover
crosses, returned as a provenance polynomial naming every source it rests on.

Swanson found in 1986 that fish oil might treat Raynaud's syndrome. Nobody had
written that. One literature reported that fish oil lowers blood viscosity; a
different literature, which did not cite the first, reported that raised blood
viscosity aggravates Raynaud's. The conclusion followed from the two together
and was stated by neither, and it went unnoticed partly because the two
literatures did not share vocabulary.

That problem needs both halves, which is why it is the example here:

  - the CHAIN is symbolic. A join over stored claims, which a language model
    does not do reliably and cannot show its working for. What comes back is
    not a plausible sentence but a derivation naming p1 and p2.
  - the vocabulary GAP is neural. The query asks about `fish-oil`; every paper
    says `omega-3`. No symbolic machinery closes that, because the two names
    share nothing but their meaning.

And the evidence is algebra rather than bookkeeping. Facts and rules carry
tags, so the same question read under `counting` answers how many independent
literature paths support the hypothesis, and under `prov` answers which papers,
as a polynomial whose product is joint use and whose sum is alternative
derivation
[source: Green, Karvounarakis and Tannen, "Provenance semirings", PODS 2007].

Neither half works alone, and neither is bolted on: the embedding decides what
unifies, the engine decides what follows, and the answer carries its citations.
Guarantees:
  - the hypothesis is unreachable without the embedding, and the same query
    without it answers nothing [tested: test_example_runs_and_verifies_itself]
  - the neural gate, the tagged rule and the semiring compose in ONE query
    [tested: test_example_runs_and_verifies_itself]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done, skip

try:
    import torch
except ImportError:
    skip("torch is not installed")

from metta import TRUE, G, S, V, counting, prov, space
from metta.arrays import EmbeddingStore

m = space()

# Two literatures that never cite each other, and a red herring. Each claim
# carries the paper it came from, which is what the provenance answers are made
# of. Nothing here states a conclusion.
CORPUS = [
    ("p1", "omega-3", "lowers", "blood-viscosity"),
    ("p2", "blood-viscosity", "aggravates", "raynaud"),
    ("p4", "omega-3", "lowers", "platelet-aggregation"),
    ("p5", "platelet-aggregation", "aggravates", "raynaud"),
    ("p3", "aspirin", "lowers", "inflammation"),
]
for paper, agent, verb, target in CORPUS:
    m.add_tagged_fact(S[paper], S.reports(S[agent], S[verb], S[target]))

# Swanson's ABC rule, tagged like any other source: if A lowers B and B
# aggravates C, then A is worth trying against C.
m.add_tagged_rule(
    S.abc,
    S.suggests(V.agent, V.condition),
    S.reports(V.agent, S.lowers, V.factor),
    S.reports(V.factor, S.aggravates, V.condition),
)

# Term vectors. A real corpus embeds its vocabulary with a trained encoder;
# what matters is that these are torch tensors the engine never converts.
TERMS = {
    "omega-3": [0.90, 0.10, 0.0],
    "fish-oil": [0.88, 0.16, 0.0],
    "aspirin": [0.10, 0.90, 0.0],
    "blood-viscosity": [0.0, 0.10, 0.90],
}
store = EmbeddingStore(m, name="terms", mirror=False)
for term, vector in TERMS.items():
    store.add(S[term], torch.tensor(vector))


class Like:
    """A term that unifies with whatever the embedding puts within `floor`.

    `match_` is the whole interface: a class defining it owns its matching
    inside `(unify ...)` with no registration, so this composes with an
    ordinary query instead of replacing one.
    """

    def __init__(self, key, floor=0.95):
        self.key = key
        self.floor = floor

    def match_(self, other):
        for key, score in store.ranked(self.key, len(TERMS)):
            if str(key) == str(other) and float(score) >= self.floor:
                yield other


near_fish_oil = S.unify(G(Like(S.fish_oil)), V.agent, TRUE, S.superpose(()))

# Symbolically there is nothing: no paper contains the phrase the query uses.
check(
    "no paper mentions fish oil",
    m.match(S.reports(S.fish_oil, S.lowers, V.factor)).to_dicts(),
    [],
)

# The same corpus, asked with a term the embedding can place. A tagged rule
# lives in the ANNOTATED layer, so a query over it names the algebra it wants;
# that is the point rather than a formality, because a discovered hypothesis
# without its evidence is not worth having.
found = m.match(S.suggests(V.agent, S.raynaud), where=near_fish_oil, under=prov).one()
check(
    "fish oil is worth trying against Raynaud's",
    str(found.value),
    "(suggests omega-3 raynaud)",
)

# How much independent support? The same question under a different algebra.
check(
    "two independent literature paths support it",
    m.match(S.suggests(S["omega-3"], S.raynaud), under=counting).one(),
    2,
)

# Which papers? The provenance polynomial: `times` is joint use and `plus` is
# an alternative derivation, so this reads as "the rule with p1 and p2, or the
# rule with p4 and p5". The neural gate, the tagged rule and the semiring are
# all in this one query.
check(
    "and the answer carries its citations",
    str(found.annotation),
    "(plus (times (times abc p1) p2) (times (times abc p4) p5))",
)

# The same derivation, rendered for a reader who wants to go and check it.
derivation = found.why().render()
check(
    "the derivation names the rule and every source",
    [name for name in ("abc", "p1", "p2", "p4", "p5") if name in derivation],
    ["abc", "p1", "p2", "p4", "p5"],
)

done("literature_discovery")
