"""Purpose: examples/data/is_alpha_member_test.metta in Python: membership modulo renaming.

`is-alpha-member` asks whether a list holds a term that is the same as the one
you have UP TO the names of its variables, so `(f $x)` is a member of
`((f $y) (g $z))` while Python's own `in`, which compares structurally, says it
is not. That difference is the whole subject, so the claims go to the operation
itself, and the two spellings are put side by side once to show where they part.

Known issue: the perfect spelling of every question below is
`m.fn.is_alpha_member(needle, haystack).one()`, and half of these needles carry
variables, where a call through the function namespace answers BINDING ROWS
rather than the value: `is-alpha-member (f $x) ((f $y) (g $z))` comes back as
`Row(x=..., y=..., z=...)` and the verdict is gone [measured 2026-08-23]. The
term door answers the value whatever the term holds, so each question is one
`m.eval` of the built term until a call can answer a value and its bindings.

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

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Ask about membership for twenty-two shapes of needle and haystack."""

    def holds(needle, haystack):
        """Whether `haystack` holds a term alpha-equal to `needle`."""
        return m.eval(S.is_alpha_member(needle, haystack)) == [True]

    letters = S.a(S.b, S.c)

    assert not holds(S.x, Expression(()))
    assert not holds(V.x, letters)
    assert holds(S.a, letters)
    assert not holds(S.d, letters)

    # Alpha-equivalence: the variable names differ and the structure does not.
    assert holds(S.f(V.x), Expression((S.f(V.y), S.g(V.z))))
    assert holds(S.f(V.x), Expression((S.f(V.y), S.f(V.y))))
    assert S.f(V.x) not in Expression((S.f(V.y), S.g(V.z)))

    # Nested structure, and a repeated variable that must repeat in the match.
    assert holds(S.f(S.g(V.x), V.y), Expression((S.f(S.g(V.a), V.b), S.h(V.c, V.d))))
    assert holds(S.f(S.g(V.x), V.x), Expression((S.f(S.g(V.a), V.b), S.f(S.g(V.c), V.c))))

    # Different arities never match.
    assert not holds(S.f(V.x), Expression((S.f(V.x, V.y), S.g(V.z))))

    assert holds(42, Expression((1, 2, 42, 3)))
    assert not holds(99, Expression((1, 2, 42, 3)))

    assert holds(Expression((1, V.x)), Expression((Expression((1, 2)), Expression((3, 4)))))
    assert not holds(Expression((1, V.x)), Expression((Expression((2, 3)), Expression((4, 5)))))

    assert holds(S.a, S.a(S.b, S.a, S.c))
    assert holds(S.f(V.x, V.y), Expression((S.f(V.a, V.b), S.f(V.c, V.d))))

    assert holds(S.a, S.a())
    assert not holds(S.b, S.a())

    # Every element is a variable, and so is the needle.
    assert holds(V.x, Expression((V.y, V.z, V.w)))

    assert holds(S.a(S.b(S.c(V.x))), Expression((S.a(S.b(S.c(V.d))), S.e(V.f))))
    assert not holds(S.f(V.x), Expression((S.g(V.y), S.h(V.z))))

    # The empty expression is an ordinary member.
    assert holds(Expression(()), Expression((Expression(()), S.a, S.b)))
    assert not holds(Expression(()), S.a(S.b, S.c))

    pattern = S.hi(S.name, S.boss)
    print(pattern, holds(V.new, pattern))
