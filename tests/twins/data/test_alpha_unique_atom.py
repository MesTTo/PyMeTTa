"""Purpose: examples/data/test_alpha_unique_atom.metta in Python: dedupe modulo renaming.

`alpha-unique-atom` drops a later element when an earlier one is the same term
up to the names of its variables, so three links that differ only in their
variable survive as one. Every claim compares with `a.alpha_eq(b)` rather than
`==`, for the same reason the operation exists: the surviving element carries
whichever variable came first, and the expected answer names a different one.

The Python route is `petta.structures.AlphaSet`, whose membership is that same
equivalence, so a four-line walk over it does what the operation does. The last
claim runs both and holds them to one answer.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V
from petta.structures import AlphaSet

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Dedupe thirteen expressions modulo variable renaming."""

    def dedupe(items):
        """The engine's own alpha-dedupe of one expression.

        Known issue: the perfect spelling is
        `m.fn.alpha_unique_atom(items).one()`, and half of these expressions
        carry variables, where a call through the function namespace answers
        BINDING ROWS rather than the deduped term [measured 2026-08-23]. The
        term door answers the value whatever the term holds.
        """
        return m.eval(S.alpha_unique_atom(items))[0]

    def first_of_each(items):
        """The same walk in Python: AlphaSet membership IS alpha-equivalence."""
        seen, kept = AlphaSet(), []
        for atom in items:
            if atom not in seen:
                seen.add(atom)
                kept.append(atom)
        return Expression(kept)

    link, human = S.link, S.human

    # Duplicates that differ only in their variable.
    assert dedupe(Expression((link(V.x, human), link(V.y, human), link(V.z, human)))).alpha_eq(
        Expression((link(V.a, human),)))
    assert dedupe(Expression((S.parent(V.x, human), S.parent(V.y, human),
                              S.child(V.z, human)))).alpha_eq(
        Expression((S.parent(V.a, human), S.child(V.b, human))))

    # Different functors are all distinct.
    assert dedupe(Expression((S.parent(V.x, human), S.child(V.y, human),
                              S.friend(V.z, human)))).alpha_eq(
        Expression((S.parent(V.a, human), S.child(V.b, human), S.friend(V.c, human))))
    assert dedupe(Expression((S.likes(V.x), S.hates(V.y), S.knows(V.z)))).alpha_eq(
        Expression((S.likes(V.a), S.hates(V.b), S.knows(V.c))))

    # Nested structure is compared all the way down.
    assert dedupe(Expression((link(S.foo(V.x), human), link(S.foo(V.y), human),
                              link(S.bar(V.z), human)))).alpha_eq(
        Expression((link(S.foo(V.a), human), link(S.bar(V.b), human))))
    assert dedupe(Expression((S.parent(S.child(V.x), human),
                              S.parent(S.child(V.y), human),
                              S.parent(S.child(V.x), human)))).alpha_eq(
        Expression((S.parent(S.child(V.a), human),)))

    # A mix of unique elements and duplicates keeps the first of each.
    assert dedupe(Expression((link(V.x, human), S.parent(V.x, human),
                              link(V.y, human), S.parent(V.z, human),
                              link(V.x, human)))).alpha_eq(
        Expression((link(V.a, human), S.parent(V.a, human))))
    assert dedupe(Expression((S.foo(V.x), S.foo(V.y), S.bar(V.x), S.foo(V.x),
                              S.bar(V.y)))).alpha_eq(Expression((S.foo(V.a), S.bar(V.a))))

    # Numbers and plain symbols need no renaming at all.
    assert dedupe(Expression((1, 2, 2, 3, 1, 4, 4, 5))).alpha_eq(Expression((1, 2, 3, 4, 5)))
    assert dedupe(S.a(S.b, S.a, S.c, S.b, S.d, S.e, S.a)).alpha_eq(S.a(S.b, S.c, S.d, S.e))

    # The empty and the single-element cases.
    assert dedupe(Expression(())).alpha_eq(Expression(()))
    assert dedupe(Expression((1,))).alpha_eq(Expression((1,)))

    singleton = Expression((link(V.x, human),))
    expected = Expression((link(V.a, human),))
    assert dedupe(singleton).alpha_eq(expected) and first_of_each(singleton).alpha_eq(expected)
