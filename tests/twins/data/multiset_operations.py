"""examples/data/multiset_operations.metta in Python: Counter is the algebra.

Every one of these operations is MULTISET, not set: `(a a a)` minus `(a)` is
`(a a)`, and an intersection keeps as many copies as both sides can afford.
`collections.Counter` is exactly that algebra, `&` and `-` included, so the
Python spelling of each operation is one line over it, plus a walk that renders
the result in the left side's own order, which is the order the answers come
back in.

Each claim says two things at once: what the operation answers, and that the
Python spelling and the engine's own `-atom` operation agree on it. The second
half is why the dissolution is safe to teach.
"""

from collections import Counter

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6152 to 4320, -1832 (-29.78%), by the twin-shape
#: rewrite: eight `test` wrappers left the engine for `assert`, and each
#: claim now computes its answer in Python with `collections.Counter`, which
#: is the multiset algebra these operations implement, and holds it against
#: the engine's own `-atom` answer. Against the example's 10222 the ratio is
#: 0.4226 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/multiset_operations.metta`]. Prior: RE-PINNED at 6152 by the
#: wave-4 idiom rewrite.
BUDGET = 4320


def twin(m):
    """Run each multiset operation both ways and hold them to one answer."""

    def kept(left, budget):
        """`left`'s atoms in their own order, while the budget for each lasts."""
        out = []
        for atom in left:
            if budget[atom]:
                budget[atom] -= 1
                out.append(atom)
        return expr(*out)

    def common(left, right):
        """Multiset intersection: Counter's `&`, in the left side's order."""
        return kept(left, Counter(left) & Counter(right))

    def without(left, right):
        """Multiset difference: Counter's `-`, in the left side's order."""
        return kept(left, Counter(left) - Counter(right))

    def joined(left, right):
        """Multiset union: every copy from both sides, which is concatenation."""
        return expr(*left, *right)

    def once_each(items):
        """Duplicates dropped, first occurrence kept: dict.fromkeys is that."""
        return expr(*dict.fromkeys(items))

    assert once_each(S.a(S.b, S.c, S.d, S.d)) == S.a(S.b, S.c, S.d) == m.fn(
        "unique-atom")(S.a(S.b, S.c, S.d, S.d))
    assert joined(S.a(S.b, S.b, S.c), S.b(S.c, S.c, S.d)) == S.a(
        S.b, S.b, S.c, S.b, S.c, S.c, S.d) == m.fn("union-atom")(
        S.a(S.b, S.b, S.c), S.b(S.c, S.c, S.d))
    assert common(S.a(S.b, S.c, S.c), S.b(S.c, S.c, S.c, S.d)) == S.b(
        S.c, S.c) == m.fn("intersection-atom")(
        S.a(S.b, S.c, S.c), S.b(S.c, S.c, S.c, S.d))
    assert without(S.a(S.b, S.b, S.c), S.b(S.c, S.c, S.d)) == S.a(
        S.b) == m.fn("subtraction-atom")(S.a(S.b, S.b, S.c), S.b(S.c, S.c, S.d))
    assert common(S.a(S.b, S.c, S.c), S.b(S.c, S.d)) == S.b(S.c) == m.fn(
        "intersection-atom")(S.a(S.b, S.c, S.c), S.b(S.c, S.d))
    assert common(S.a(S.a, S.a), S.a()) == S.a() == m.fn(
        "intersection-atom")(S.a(S.a, S.a), S.a())
    assert without(S.a(S.a, S.a), S.a()) == S.a(S.a) == m.fn(
        "subtraction-atom")(S.a(S.a, S.a), S.a())
    assert common(S.a(S.b), expr()) == expr() == m.fn(
        "intersection-atom")(S.a(S.b), expr())
