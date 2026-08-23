"""examples/data/multiset_operations.metta in Python: Counter is the algebra.

Every one of these operations is MULTISET, not set: `(a a a)` minus `(a)` is
`(a a)`, and an intersection keeps as many copies as both sides can afford.
`collections.Counter` is exactly that algebra, `&` and `-` included, so each
Python spelling is one line over it plus a walk that renders the result in the
left side's own order, which is the order the answers come back in.

Each claim says two things at once: what the operation answers, and that the
Python spelling and the engine's own `-atom` operation agree on it. The second
half is why the dissolution is safe to teach.
"""

from collections import Counter

from metta import Expression, S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Run each multiset operation both ways and hold them to one answer."""

    def kept(left, budget):
        """`left`'s atoms in their own order, while the budget for each lasts."""
        out = []
        for atom in left:
            if budget[atom]:
                budget[atom] -= 1
                out.append(atom)
        return Expression(out)

    def common(left, right):
        """Multiset intersection: Counter's `&`, in the left side's order."""
        return kept(left, Counter(left) & Counter(right))

    def without(left, right):
        """Multiset difference: Counter's `-`, in the left side's order."""
        return kept(left, Counter(left) - Counter(right))

    def joined(left, right):
        """Multiset union: every copy from both sides, which is concatenation."""
        return Expression((*left, *right))

    def once_each(items):
        """Duplicates dropped, first occurrence kept: dict.fromkeys is that."""
        return Expression(dict.fromkeys(items))

    repeated = S.a(S.b, S.c, S.d, S.d)
    left, right = S.a(S.b, S.b, S.c), S.b(S.c, S.c, S.d)
    wide, wider = S.a(S.b, S.c, S.c), S.b(S.c, S.c, S.c, S.d)
    narrow = S.b(S.c, S.d)
    thrice, once = S.a(S.a, S.a), S.a()
    nothing = Expression(())

    assert once_each(repeated) == m.fn.unique_atom(repeated).one() == S.a(S.b, S.c, S.d)
    assert joined(left, right) == m.fn.union_atom(left, right).one() == S.a(
        S.b, S.b, S.c, S.b, S.c, S.c, S.d)
    assert common(wide, wider) == m.fn.intersection_atom(wide, wider).one() == S.b(S.c, S.c)
    assert without(left, right) == m.fn.subtraction_atom(left, right).one() == S.a(S.b)
    assert common(wide, narrow) == m.fn.intersection_atom(wide, narrow).one() == S.b(S.c)
    assert common(thrice, once) == m.fn.intersection_atom(thrice, once).one() == S.a()
    assert without(thrice, once) == m.fn.subtraction_atom(thrice, once).one() == S.a(S.a)
    assert common(S.a(S.b), nothing) == m.fn.intersection_atom(
        S.a(S.b), nothing).one() == nothing
