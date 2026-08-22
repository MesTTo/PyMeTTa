"""examples/data/streamops.metta in Python: the same algebra over ANSWERS.

`superpose` fans an expression out into one answer per element, and the four
operations here work over those answers rather than over children. In Python
that difference disappears: an answer set is an iterable, `list()` of it is
what `collapse` spells, and the multiset algebra is `collections.Counter`
again, exactly as it was over children in the sibling `multiset_operations`.

`m.eval` of a nondeterministic term already answers the whole list, so the
collapse in the original has nothing left to do here. Each claim holds the
Python spelling and the engine's own stream operation to one answer.
"""

from collections import Counter

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4650 to 5024, +374 (+8.04%), by the twin-shape
#: rewrite: four `test`-plus-`collapse` wrappers left the engine for
#: `assert`, and each claim now runs the stream operation TWICE: once as
#: Python's own algebra over the answers `m.eval` already collects, and once
#: as the engine's own operation, holding the two to one answer. The second
#: run is the whole of the increase and it is what makes the dissolution safe
#: to teach. Against the example's 8240 the ratio is 0.6097 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/streamops.metta`]. Prior: RE-PINNED at 4650 by the wave-4
#: idiom rewrite.
BUDGET = 5024


def twin(m):
    """Fan out four streams, then fold them back both ways."""

    def kept(left, budget):
        """`left`'s answers in their own order, while each budget lasts."""
        out = []
        for atom in left:
            if budget[atom]:
                budget[atom] -= 1
                out.append(atom)
        return out

    letters = S.superpose(S.a(S.b, S.c, S.d, S.d))
    left, right = S.superpose(S.a(S.b, S.b, S.c)), S.superpose(S.b(S.c, S.c, S.d))
    wide, wider = S.superpose(S.a(S.b, S.c, S.c)), S.superpose(S.b(S.c, S.c, S.c, S.d))
    seen, other = m.eval(left), m.eval(right)
    here, there = m.eval(wide), m.eval(wider)

    assert list(dict.fromkeys(m.eval(letters))) == [S.a, S.b, S.c, S.d] == m.eval(S.unique(letters))
    assert seen + other == [S.a, S.b, S.b, S.c, S.b, S.c, S.c, S.d] == m.eval(S.union(left, right))
    assert kept(here, Counter(here) & Counter(there)) == [S.b, S.c, S.c] == m.eval(S.intersection(wide, wider))
    assert kept(seen, Counter(seen) - Counter(other)) == [S.a, S.b] == m.eval(S.subtraction(left, right))
