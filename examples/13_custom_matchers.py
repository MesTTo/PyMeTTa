"""Purpose: custom matchers are first class: one name, two modes (score a
bound candidate, generate unbound ones best first), every matcher answering
(score value) pairs the measure algebra consumes, so attention runs through
ANY notion of closeness: lexical (difflib), semantic (embeddings), or your
own function. Structural match composes before or after, no new syntax.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done, skip

try:
    import numpy
except ImportError:
    skip("numpy is not installed")

from petta import MeTTa, S, V, matching, measure  # noqa: E402
from petta.arrays import EmbeddingStore  # noqa: E402

m = MeTTa().fresh_space()
measure.install(m)

# Lexical closeness, the standard library's own: a matcher in one call.
matching.install_fuzzy(m, name="fuzmatch")
(scored,) = m.run('!(fuzmatch "recieve" "receive")')[0]
check("fuzzy scores typos", float(scored[0]) > 0.85)

# Semantic closeness: an embedding store IS a matcher.
store = EmbeddingStore(m, name="vec", mirror=False)
store.add(S.espresso, numpy.array([0.9, 0.1, 0.0]))
store.add(S.latte, numpy.array([0.8, 0.3, 0.0]))
store.add(S.granite, numpy.array([0.0, 0.1, 0.9]))
store.matcher(name="semmatch", threshold=0.0)

(best,) = m.run("!(ws-best (collapse (semmatch espresso $k)))")[0]
check("nearest neighbour", best, S.espresso)

# Attention through a matcher: softmax the matches, a distribution over
# candidates by THIS matcher's closeness.
(dist,) = m.run("!(ws-softmax (collapse (semmatch latte $k)) 0.5)")[0]
weights = {str(pair[1]): float(pair[0]) for pair in dist}
check("a distribution", abs(sum(weights.values()) - 1.0) < 1e-9)
check("coffee outweighs rock", weights["latte"] > weights["granite"])

# Your own closeness: any scoring function, same shape, same algebra.
def initials(query, candidate):
    a, b = str(query), matching.text_of(candidate)
    return 1.0 if a[:1] == b[:1] else 0.0

matching.matcher(m, "same-initial", score=initials, threshold=0.5)
m.add(S.person(S.ada), S.person(S.alan), S.person(S.grace))
(hits,) = m.run(
    "!(collapse (match (context-space) (person $p) (same-initial a $p)))"
)[0]
check("composes with structural match", len(hits), 2)
done("13_custom_matchers")
