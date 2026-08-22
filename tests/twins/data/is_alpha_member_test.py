"""Purpose: examples/data/is_alpha_member_test.metta in Python: membership modulo renaming.

`is-alpha-member` asks whether a list holds a term that is the same as the one
you have UP TO the names of its variables, so `(f $x)` is a member of
`((f $y) (g $z))` while Python's own `in`, which compares structurally, says it
is not. That difference is the whole subject, so the claims go to the operation
itself, and the two spellings are put side by side once to show where they part.

The cases walk the edges: an empty list, a variable against ground terms, a
ground term, nested structure, a repeated variable that must repeat in the
match too, differing arities, numbers, and the empty expression as a member.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 16069 to 12361, -3708 (-23.08%), by the twin-shape
#: rewrite: twenty-two `test` wrappers left the engine for `assert`; every
#: membership question still runs in the engine, because alpha-equivalence is
#: what Python's own `in` does NOT do, and the twin says so with a claim.
#: Against the example's 29435 the ratio is 0.4199 [measured 2026-08-22 min-
#: of-3: `twin_coverage.py --measure
#: examples/data/is_alpha_member_test.metta`]. Prior: RE-PINNED at 16069 by
#: the wave-4 idiom rewrite.
BUDGET = 12361


def twin(m):
    """Ask about membership for twenty-two shapes of needle and haystack."""
    member = m.fn("is-alpha-member")
    letters = S.a(S.b, S.c)

    assert member(S.x, Expression(())) is False
    assert member(V.x, letters) is False
    assert member(S.a, letters) is True
    assert member(S.d, letters) is False

    # Alpha-equivalence: the variable names differ and the structure does not.
    assert member(S.f(V.x), Expression((S.f(V.y), S.g(V.z)))) is True
    assert member(S.f(V.x), Expression((S.f(V.y), S.f(V.y)))) is True
    assert S.f(V.x) not in Expression((S.f(V.y), S.g(V.z)))

    # Nested structure, and a repeated variable that must repeat in the match.
    assert member(S.f(S.g(V.x), V.y), Expression((S.f(S.g(V.a), V.b), S.h(V.c, V.d)))) is True
    assert member(S.f(S.g(V.x), V.x), Expression((S.f(S.g(V.a), V.b), S.f(S.g(V.c), V.c)))) is True

    # Different arities never match.
    assert member(S.f(V.x), Expression((S.f(V.x, V.y), S.g(V.z)))) is False

    assert member(42, Expression((1, 2, 42, 3))) is True
    assert member(99, Expression((1, 2, 42, 3))) is False

    assert member(Expression((1, V.x)), Expression((Expression((1, 2)), Expression((3, 4))))) is True
    assert member(Expression((1, V.x)), Expression((Expression((2, 3)), Expression((4, 5))))) is False

    assert member(S.a, S.a(S.b, S.a, S.c)) is True
    assert member(S.f(V.x, V.y), Expression((S.f(V.a, V.b), S.f(V.c, V.d)))) is True

    assert member(S.a, S.a()) is True
    assert member(S.b, S.a()) is False

    # Every element is a variable, and so is the needle.
    assert member(V.x, Expression((V.y, V.z, V.w))) is True

    assert member(S.a(S.b(S.c(V.x))), Expression((S.a(S.b(S.c(V.d))), S.e(V.f)))) is True
    assert member(S.f(V.x), Expression((S.g(V.y), S.h(V.z)))) is False

    # The empty expression is an ordinary member.
    assert member(Expression(()), Expression((Expression(()), S.a, S.b))) is True
    assert member(Expression(()), S.a(S.b, S.c)) is False

    pattern = S.hi(S.name, S.boss)
    print(pattern, member(V.new, pattern))
