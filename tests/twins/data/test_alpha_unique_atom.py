"""Purpose: examples/data/test_alpha_unique_atom.metta in Python: dedupe modulo renaming.

`alpha-unique-atom` drops a later element when an earlier one is the same term
up to the names of its variables, so three links that differ only in their
variable survive as one. Every claim compares with `=alpha` rather than `==`,
for the same reason the operation exists: the surviving element carries
whichever variable came first, and the expected answer names a different one.

The Python route is `petta.structures.AlphaSet`, whose membership is that same
equivalence, so a four-line walk over it does what the operation does. The last
claim runs both and holds them to one answer.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, alpha_eq
from petta.structures import AlphaSet

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 15730 to 9313, -6417 (-40.79%), by the twin-shape
#: rewrite: thirteen `test` wrappers left the engine for `assert`, and the
#: `=alpha` comparison in each of them became `petta.alpha_eq` on the Python
#: side, which costs no engine; the dedupe itself still runs in the engine,
#: with one claim holding it against the AlphaSet walk that does the same
#: thing. Against the example's 30476 the ratio is 0.3056 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/test_alpha_unique_atom.metta`]. Prior: RE-PINNED at 15730 by
#: the wave-4 idiom rewrite.
BUDGET = 9313


def twin(m):
    """Dedupe thirteen expressions modulo variable renaming."""
    dedupe = m.fn("alpha-unique-atom")

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
    assert alpha_eq(dedupe(Expression((link(V.x, human), link(V.y, human), link(V.z, human)))),
                    Expression((link(V.a, human),)))
    assert alpha_eq(dedupe(Expression((S.parent(V.x, human), S.parent(V.y, human),
                                S.child(V.z, human)))),
                    Expression((S.parent(V.a, human), S.child(V.b, human))))

    # Different functors are all distinct.
    assert alpha_eq(dedupe(Expression((S.parent(V.x, human), S.child(V.y, human),
                                S.friend(V.z, human)))),
                    Expression((S.parent(V.a, human), S.child(V.b, human),
                         S.friend(V.c, human))))
    assert alpha_eq(dedupe(Expression((S.likes(V.x), S.hates(V.y), S.knows(V.z)))),
                    Expression((S.likes(V.a), S.hates(V.b), S.knows(V.c))))

    # Nested structure is compared all the way down.
    assert alpha_eq(dedupe(Expression((link(S.foo(V.x), human), link(S.foo(V.y), human),
                                link(S.bar(V.z), human)))),
                    Expression((link(S.foo(V.a), human), link(S.bar(V.b), human))))
    assert alpha_eq(dedupe(Expression((S.parent(S.child(V.x), human),
                                S.parent(S.child(V.y), human),
                                S.parent(S.child(V.x), human)))),
                    Expression((S.parent(S.child(V.a), human),)))

    # A mix of unique elements and duplicates keeps the first of each.
    assert alpha_eq(dedupe(Expression((link(V.x, human), S.parent(V.x, human),
                                link(V.y, human), S.parent(V.z, human),
                                link(V.x, human)))),
                    Expression((link(V.a, human), S.parent(V.a, human))))
    assert alpha_eq(dedupe(Expression((S.foo(V.x), S.foo(V.y), S.bar(V.x), S.foo(V.x),
                                S.bar(V.y)))),
                    Expression((S.foo(V.a), S.bar(V.a))))

    # Numbers and plain symbols need no renaming at all.
    assert alpha_eq(dedupe(Expression((1, 2, 2, 3, 1, 4, 4, 5))), Expression((1, 2, 3, 4, 5)))
    assert alpha_eq(dedupe(S.a(S.b, S.a, S.c, S.b, S.d, S.e, S.a)),
                    S.a(S.b, S.c, S.d, S.e))

    # The empty and the single-element cases.
    assert alpha_eq(dedupe(Expression(())), Expression(()))
    assert alpha_eq(dedupe(Expression((1,))), Expression((1,)))

    singleton = Expression((link(V.x, human),))
    assert alpha_eq(dedupe(singleton), Expression((link(V.a, human),))) and alpha_eq(
        first_of_each(singleton), Expression((link(V.a, human),)))
