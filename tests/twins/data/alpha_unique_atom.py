"""examples/data/alpha_unique_atom.metta in Python: dedupe modulo renaming.

`alpha-unique-atom` drops a later element when an earlier one is the same term
up to the names of its variables, so three links that differ only in their
variable survive as one. Every claim compares with `alpha_eq` rather than `==`,
for the same reason the operation exists: the surviving element carries
whichever variable came first and the expected answer names a different one.

Python has the relation too, as `metta.structures.AlphaSet`, whose membership
IS that equivalence, so a four-line walk over it does what the operation does.
Each claim runs both and holds them to one answer, which is what makes the
Python structure safe to reach for.
"""

from metta import Expression, S, V
from metta.structures import AlphaSet

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
BUDGET = 1


def twin(m):
    """Dedupe thirteen expressions modulo variable renaming, two ways each."""

    def first_of_each(items):
        """The walk in Python: AlphaSet membership IS alpha-equivalence."""
        seen, kept = AlphaSet(), []
        for atom in items:
            if atom not in seen:
                seen.add(atom)
                kept.append(atom)
        return Expression(kept)

    def dedupes(items, expected):
        """Whether both routes drop the same elements, up to renaming."""
        engine = m.fn.alpha_unique_atom(Expression(items)).one()
        return engine.alpha_eq(Expression(expected)) and first_of_each(items).alpha_eq(engine)

    link, human = S.link, S.human
    parent, child, foo, bar = S.parent, S.child, S.foo, S.bar

    # Duplicates that differ only in their variable.
    assert dedupes((link(V.x, human), link(V.y, human), link(V.z, human)),
                   (link(V.a, human),))
    assert dedupes((parent(V.x, human), parent(V.y, human), child(V.z, human)),
                   (parent(V.a, human), child(V.b, human)))

    # Different functors are all distinct.
    assert dedupes((parent(V.x, human), child(V.y, human), S.friend(V.z, human)),
                   (parent(V.a, human), child(V.b, human), S.friend(V.c, human)))
    assert dedupes((S.likes(V.x), S.hates(V.y), S.knows(V.z)),
                   (S.likes(V.a), S.hates(V.b), S.knows(V.c)))

    # Nested structure is compared all the way down.
    assert dedupes((link(foo(V.x), human), link(foo(V.y), human), link(bar(V.z), human)),
                   (link(foo(V.a), human), link(bar(V.b), human)))
    assert dedupes((parent(child(V.x), human), parent(child(V.y), human),
                    parent(child(V.x), human)),
                   (parent(child(V.a), human),))

    # A mix of unique elements and duplicates keeps the first of each.
    assert dedupes((link(V.x, human), parent(V.x, human), link(V.y, human),
                    parent(V.z, human), link(V.x, human)),
                   (link(V.a, human), parent(V.a, human)))
    assert dedupes((foo(V.x), foo(V.y), bar(V.x), foo(V.x), bar(V.y)),
                   (foo(V.a), bar(V.a)))

    # Numbers and plain symbols need no renaming at all.
    assert dedupes((1, 2, 2, 3, 1, 4, 4, 5), (1, 2, 3, 4, 5))
    assert dedupes((S.a, S.b, S.a, S.c, S.b, S.d, S.e, S.a), (S.a, S.b, S.c, S.d, S.e))

    # The empty and the single-element cases.
    assert dedupes((), ())
    assert dedupes((1,), (1,))
    assert dedupes((link(V.x, human),), (link(V.a, human),))
