"""examples/data/streamops.metta in Python: the same algebra over ANSWERS.

`superpose` fans an expression out into one answer per element, and the four
operations here work over those answers rather than over children. In Python
that difference disappears: the answers of a superposition of a literal ARE
that literal's members, an answer set is an iterable, `list()` of it is what
`collapse` spells, and the multiset algebra is `collections.Counter` again,
exactly as it was over children in the sibling `multiset_operations`.

So each claim holds three things to one answer: the Python spelling over the
members, the engine's own stream operation over the superposition terms, and
the expected list.
"""

from collections import Counter

from metta import Expression, S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
BUDGET = 1


def twin(m):
    """Fan out four streams, then fold them back both ways."""

    def fan(members):
        """The term whose answers are `members`, one each."""
        return S.superpose(Expression(members))

    def kept(left, budget):
        """`left`'s answers in their own order, while each budget lasts."""
        out = []
        for atom in left:
            if budget[atom]:
                budget[atom] -= 1
                out.append(atom)
        return out

    letters = (S.a, S.b, S.c, S.d, S.d)
    left, right = (S.a, S.b, S.b, S.c), (S.b, S.c, S.c, S.d)
    wide, wider = (S.a, S.b, S.c, S.c), (S.b, S.c, S.c, S.c, S.d)

    # (collapse (unique (superpose (a b c d d)))) -> (a b c d)
    assert list(dict.fromkeys(letters)) == m.fn.unique(fan(letters)) == [S.a, S.b, S.c, S.d]

    # (collapse (union ...)) -> (a b b c b c c d): every copy from both sides
    assert [*left, *right] == m.fn.union(fan(left), fan(right)) == [
        S.a, S.b, S.b, S.c, S.b, S.c, S.c, S.d]

    # (collapse (intersection ...)) -> (b c c): as many copies as both afford
    assert kept(wide, Counter(wide) & Counter(wider)) == m.fn.intersection(
        fan(wide), fan(wider)) == [S.b, S.c, S.c]

    # (collapse (subtraction ...)) -> (a b)
    assert kept(left, Counter(left) - Counter(right)) == m.fn.subtraction(
        fan(left), fan(right)) == [S.a, S.b]
