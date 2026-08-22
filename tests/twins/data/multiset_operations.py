"""The Python twin of examples/data/multiset_operations.metta: the -atom family.

Every form is one call over two expressions, so the whole twin is the term
door: a symbol calls to build, and a plain Python TUPLE is the expression its
arguments are. `(a b c d d)` reads `(a, b, c, d, d)`, and `()` reads `()`.

The names are hyphenated engine functions, which is why they are subscripted:
`unique-atom` is not a Python identifier, so `S["unique-atom"]` is the only
spelling for it and not a drop from `S.unique_atom`, which would name a
different symbol.

These are MULTISET operations, which is what the answers show: `union-atom`
concatenates rather than deduplicating, and `intersection-atom` keeps the
lower of the two multiplicities.
"""

from petta import S

#: The symbols these expressions are built from, bound once so a line reads as
#: the multiset it is rather than as five repetitions of the factory.
a, b, c, d = S.a, S.b, S.c, S.d

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6152 to 6152, +0, by the wave-4 idiom rewrite: the
#: forms are the same terms built at the same door, so the rewrite is a
#: SPELLING change and the counter says so.
BUDGET = 6152


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(test (unique-atom (a b c d d)) (a b c d))
    yield m.eval(S.test(S["unique-atom"]((a, b, c, d, d)), (a, b, c, d)))
    # !(test (union-atom (a b b c) (b c c d)) (a b b c b c c d))
    yield m.eval(
        S.test(S["union-atom"]((a, b, b, c), (b, c, c, d)), (a, b, b, c, b, c, c, d))
    )
    # !(test (intersection-atom (a b c c) (b c c c d)) (b c c))
    yield m.eval(
        S.test(S["intersection-atom"]((a, b, c, c), (b, c, c, c, d)), (b, c, c))
    )
    # !(test (subtraction-atom (a b b c) (b c c d)) (a b))
    yield m.eval(S.test(S["subtraction-atom"]((a, b, b, c), (b, c, c, d)), (a, b)))
    # !(test (intersection-atom (a b c c) (b c d)) (b c))
    yield m.eval(S.test(S["intersection-atom"]((a, b, c, c), (b, c, d)), (b, c)))
    # !(test (intersection-atom (a a a) (a)) (a))
    yield m.eval(S.test(S["intersection-atom"]((a, a, a), (a,)), (a,)))
    # !(test (subtraction-atom (a a a) (a)) (a a))
    yield m.eval(S.test(S["subtraction-atom"]((a, a, a), (a,)), (a, a)))
    # !(test (intersection-atom (a b) ()) ())
    yield m.eval(S.test(S["intersection-atom"]((a, b), ()), ()))
