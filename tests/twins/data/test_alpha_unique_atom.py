"""The Python twin of examples/data/test_alpha_unique_atom.metta.

`alpha-unique-atom` keeps one representative of each group of children that
are equal up to renaming their variables, so every form here asks the same
question of a different expression, and `check` is that question named once.
Naming the shared shape is the composition the design teaches: the cases below
then read as the DATA they are, plain Python tuples holding the children.

Comparing with `=alpha` rather than `==` is the point of the example: the
answer's variables are fresh, so only alpha-equivalence can judge it.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE = val(value=True)

#: The one symbol every group in this example is built around.
human = S.human

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 15730 to 15730, +0, by the wave-4 idiom rewrite: the
#: forms are the same terms built at the same door, so the rewrite is a
#: SPELLING change and the counter says so.
BUDGET = 15730


def check(given, expected):
    """`(test (=alpha (alpha-unique-atom given) expected) True)`, the one form
    every case of this example takes.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return S.test(S["=alpha"](S["alpha-unique-atom"](given), expected), TRUE)


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # 1 Basic duplicates with different variables
    # !(test (=alpha (alpha-unique-atom ((link $x human) (link $y human) (link $z human)))
    #                ((link $a human))) True)
    yield m.eval(
        check(
            (S.link(V.x, human), S.link(V.y, human), S.link(V.z, human)),
            (S.link(V.a, human),),
        )
    )
    # !(test (=alpha (alpha-unique-atom ((parent $x human) (parent $y human) (child $z human)))
    #                ((parent $a human) (child $b human))) True)
    yield m.eval(
        check(
            (S.parent(V.x, human), S.parent(V.y, human), S.child(V.z, human)),
            (S.parent(V.a, human), S.child(V.b, human)),
        )
    )

    # 2 Different functors
    # !(test (=alpha (alpha-unique-atom ((parent $x human) (child $y human) (friend $z human)))
    #                ((parent $a human) (child $b human) (friend $c human))) True)
    yield m.eval(
        check(
            (S.parent(V.x, human), S.child(V.y, human), S.friend(V.z, human)),
            (S.parent(V.a, human), S.child(V.b, human), S.friend(V.c, human)),
        )
    )
    # !(test (=alpha (alpha-unique-atom ((likes $x) (hates $y) (knows $z)))
    #                ((likes $a) (hates $b) (knows $c))) True)
    yield m.eval(
        check(
            (S.likes(V.x), S.hates(V.y), S.knows(V.z)),
            (S.likes(V.a), S.hates(V.b), S.knows(V.c)),
        )
    )

    # 3 Nested structures
    # !(test (=alpha (alpha-unique-atom ((link (foo $x) human) (link (foo $y) human)
    #                                    (link (bar $z) human)))
    #                ((link (foo $a) human) (link (bar $b) human))) True)
    yield m.eval(
        check(
            (
                S.link(S.foo(V.x), human),
                S.link(S.foo(V.y), human),
                S.link(S.bar(V.z), human),
            ),
            (S.link(S.foo(V.a), human), S.link(S.bar(V.b), human)),
        )
    )
    # !(test (=alpha (alpha-unique-atom ((parent (child $x) human) (parent (child $y) human)
    #                                    (parent (child $x) human)))
    #                ((parent (child $a) human))) True)
    yield m.eval(
        check(
            (
                S.parent(S.child(V.x), human),
                S.parent(S.child(V.y), human),
                S.parent(S.child(V.x), human),
            ),
            (S.parent(S.child(V.a), human),),
        )
    )

    # 4 Mix of unique and duplicates
    # !(test (=alpha (alpha-unique-atom ((link $x human) (parent $x human) (link $y human)
    #                                    (parent $z human) (link $x human)))
    #                ((link $a human) (parent $a human))) True)
    yield m.eval(
        check(
            (
                S.link(V.x, human),
                S.parent(V.x, human),
                S.link(V.y, human),
                S.parent(V.z, human),
                S.link(V.x, human),
            ),
            (S.link(V.a, human), S.parent(V.a, human)),
        )
    )
    # !(test (=alpha (alpha-unique-atom ((foo $x) (foo $y) (bar $x) (foo $x) (bar $y)))
    #                ((foo $a) (bar $a))) True)
    yield m.eval(
        check(
            (S.foo(V.x), S.foo(V.y), S.bar(V.x), S.foo(V.x), S.bar(V.y)),
            (S.foo(V.a), S.bar(V.a)),
        )
    )

    # 5 Numbers and atoms
    # !(test (=alpha (alpha-unique-atom (1 2 2 3 1 4 4 5)) (1 2 3 4 5)) True)
    yield m.eval(check((1, 2, 2, 3, 1, 4, 4, 5), (1, 2, 3, 4, 5)))
    # !(test (=alpha (alpha-unique-atom (a b a c b d e a)) (a b c d e)) True)
    yield m.eval(
        check(
            (S.a, S.b, S.a, S.c, S.b, S.d, S.e, S.a),
            (S.a, S.b, S.c, S.d, S.e),
        )
    )

    # 6 Empty and single-element lists
    # !(test (=alpha (alpha-unique-atom ()) ()) True)
    yield m.eval(check((), ()))
    # !(test (=alpha (alpha-unique-atom (1)) (1)) True)
    yield m.eval(check((1,), (1,)))
    # !(test (=alpha (alpha-unique-atom ((link $x human))) ((link $a human))) True)
    yield m.eval(check((S.link(V.x, human),), (S.link(V.a, human),)))
