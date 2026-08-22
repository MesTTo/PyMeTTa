"""Purpose: custom matching logic as a property of grounded atoms, built
entirely on the public surface. An object whose class defines match_ owns
its matching inside (unify ...) with no registration; a scored matcher is
an ordinary operation answering candidates with the degree as each
answer's annotation. Fuzzy, regex, semantic: all outside the library,
a few lines each, composing with structural match through evaluation.
Guarantees:
  - the unannotated ranked operation makes no synthetic type claim [tested:
    test_example_runs_and_verifies_itself; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import difflib
import re

from _common import check, done, skip

try:
    import numpy
except ImportError:
    skip("numpy is not installed")

from petta import Answer, Bindings, MeTTa, S, V, Expression
from petta.arrays import EmbeddingStore
from petta.atoms import Grounded

m = MeTTa().space()

# Crisp lexical closeness: a regex value that matches inside unify. The
# pattern IS the value; matching succeeds exactly when the operand's
# printed form matches it.
class Regex:
    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def match_(self, other):
        text = other.value if isinstance(other, Grounded) else str(other)
        if self.pattern.search(str(text)):
            yield other

starts_with_a = Grounded(Regex("^a"))
(hit,) = m.eval(Expression(S.unify, starts_with_a, S.abbey, S.hit, S.miss))
check("regex value matches", hit, S.hit)
(miss,) = m.eval(Expression(S.unify, starts_with_a, S.zebra, S.hit, S.miss))
check("regex value refuses", miss, S.miss)

# Composition with structural match, no new syntax: the matchable gates
# candidates the pattern produced.
m.add(S.person(S.ada), S.person(S.alan), S.person(S.grace))
(gated,) = m.eval(
    Expression(
        S.collapse,
        Expression(
            S.match,
            Expression(S["context-space"]),
            S.person(V.p),
            Expression(S.unify, starts_with_a, V.p, V.p, Expression(S.superpose, Expression())),
        ),
    )
)
check("composes with structural match", sorted(str(x) for x in gated), ["ada", "alan"])

# Scored matching is an annotated operation: candidates are the values,
# degrees ride as annotations, top orders, (annotation) reads.
lexicon = ["class", "clause", "close"]

def fuzzy(query, candidate=None):
    for word in lexicon:
        degree = difflib.SequenceMatcher(None, str(query), word).ratio()
        yield Answer(value=word, k=round(degree, 6))

m.op(fuzzy, name="fuzmatch")
m.declare_annotations("fuzmatch", "ranked")
(best,) = m.run('!(collapse (top 1 (fuzmatch "clase" $w)))')[0]
check("fuzzy best is difflib's own ranking", str(best.children[0]), '"clause"')
(weighted,) = m.run(
    '!(collapse (let $w (fuzmatch "clase" $c) (pair (annotation) $w)))'
)[0]
check("degrees read through (annotation)", len(weighted.children), 3)

# Semantic closeness: the embedding store's retrieval as matching logic.
# The store binds the variable it was handed to the nearest key.
store = EmbeddingStore(m, name="vec", mirror=False)
store.add(S.espresso, numpy.array([0.9, 0.1, 0.0]))
store.add(S.latte, numpy.array([0.8, 0.3, 0.0]))
store.add(S.granite, numpy.array([0.0, 0.1, 0.9]))

class Nearest:
    def match_(self, other):
        query, out = other.children[0], other.children[1]
        key, _score = next(iter(store.ranked(query, 1)))
        yield Bindings({out: key})

(nearest,) = m.eval(
    Expression(S.unify, Grounded(Nearest()), Expression(S.espresso, V.k), V.k, S.none)
)
check("nearest neighbour", nearest, S.espresso)
done("custom_matchers")
