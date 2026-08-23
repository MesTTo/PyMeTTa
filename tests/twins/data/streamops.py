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

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


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

    assert list(dict.fromkeys(m.eval(letters))) == [S.a, S.b, S.c, S.d] == m.fn.unique(letters)
    assert seen + other == [S.a, S.b, S.b, S.c, S.b, S.c, S.c, S.d] == m.fn.union(left, right)
    assert kept(here, Counter(here) & Counter(there)) == [S.b, S.c, S.c] == m.fn.intersection(wide, wider)
    assert kept(seen, Counter(seen) - Counter(other)) == [S.a, S.b] == m.fn.subtraction(left, right)
