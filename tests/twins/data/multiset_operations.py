"""Purpose: examples/data/multiset_operations.metta in Python: Counter is the algebra.

Every one of these operations is MULTISET, not set: `(a a a)` minus `(a)` is
`(a a)`, and an intersection keeps as many copies as both sides can afford.
`collections.Counter` is exactly that algebra, `&` and `-` included, so the
Python spelling of each operation is one line over it, plus a walk that renders
the result in the left side's own order, which is the order the answers come
back in.

Each claim says two things at once: what the operation answers, and that the
Python spelling and the engine's own `-atom` operation agree on it. The second
half is why the dissolution is safe to teach.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from collections import Counter

from metta import Expression, S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
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
        """Duplicates dropped, first occurrence kept: dict.fromkeys is that.

        Known issue: `Expression(iterable)` reads a list or a tuple and wraps
        anything else as ONE grounded value, silently, so the perfect
        `Expression(dict.fromkeys(items))` builds `(<dict>)` and the walk
        below sees one element. `list(...)` is written out until the one-
        iterable constructor accepts any iterable [measured 2026-08-23: a
        dict, a generator and a map all wrap rather than iterate].
        """
        return Expression(list(dict.fromkeys(items)))

    repeated = S.a(S.b, S.c, S.d, S.d)
    left, right = S.a(S.b, S.b, S.c), S.b(S.c, S.c, S.d)
    wide, wider = S.a(S.b, S.c, S.c), S.b(S.c, S.c, S.c, S.d)
    narrow = S.b(S.c, S.d)
    thrice, once = S.a(S.a, S.a), S.a()

    assert once_each(repeated) == m.fn.unique_atom(repeated).one() == S.a(S.b, S.c, S.d)
    assert joined(left, right) == m.fn.union_atom(left, right).one() == S.a(
        S.b, S.b, S.c, S.b, S.c, S.c, S.d)
    assert common(wide, wider) == m.fn.intersection_atom(wide, wider).one() == S.b(S.c, S.c)
    assert without(left, right) == m.fn.subtraction_atom(left, right).one() == S.a(S.b)
    assert common(wide, narrow) == m.fn.intersection_atom(wide, narrow).one() == S.b(S.c)
    assert common(thrice, once) == m.fn.intersection_atom(thrice, once).one() == S.a()
    assert without(thrice, once) == m.fn.subtraction_atom(thrice, once).one() == S.a(S.a)
    assert common(S.a(S.b), Expression(())) == m.fn.intersection_atom(
        S.a(S.b), Expression(())).one() == Expression(())
