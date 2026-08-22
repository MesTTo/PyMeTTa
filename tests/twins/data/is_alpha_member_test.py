"""The Python twin of examples/data/is_alpha_member_test.metta.

`is-alpha-member` asks whether an expression holds a child equal to the given
one up to renaming its variables, so every case is the same question over a
different pair, and `member` names that question once. The cases then read as
the data they are: a plain Python tuple IS the expression its children make.

Two edges worth reading off the answers. Alpha-equivalence is structural, so
`(f $x)` is a member of `((f $y) (g $z))` but not of `((f $x $y) (g $z))`,
because arity differs. And a bare variable is a member of a list of variables
and of nothing else, which is why case 2 answers false and case 12 answers
true.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `true` and `false` mean inside a term.
#: Named rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 16069 to 16069, +0, by the wave-4 idiom rewrite: the
#: forms are the same terms built at the same door, so the rewrite is a
#: SPELLING change and the counter says so.
BUDGET = 16069


def member(needle, haystack, expected):
    """`(test (is-alpha-member needle haystack) expected)`, the one form every
    case of this example takes.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return S.test(S["is-alpha-member"](needle, haystack), expected)


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # Test 1: Empty list should return false
    # !(test (is-alpha-member x ()) false)
    yield m.eval(member(S.x, (), FALSE))

    # Test 2: Variable in list of atoms should not match
    # !(test (is-alpha-member $x (a b c)) false)
    yield m.eval(member(V.x, (S.a, S.b, S.c), FALSE))

    # Test 3: Ground term membership
    # !(test (is-alpha-member a (a b c)) true)
    yield m.eval(member(S.a, (S.a, S.b, S.c), TRUE))
    # !(test (is-alpha-member d (a b c)) false)
    yield m.eval(member(S.d, (S.a, S.b, S.c), FALSE))

    # Test 4: Alpha-equivalence with variables
    # !(test (is-alpha-member (f $x) ((f $y) (g $z))) true)
    yield m.eval(member(S.f(V.x), (S.f(V.y), S.g(V.z)), TRUE))
    # !(test (is-alpha-member (f $x) ((f $y) (f $y))) true)
    yield m.eval(member(S.f(V.x), (S.f(V.y), S.f(V.y)), TRUE))

    # Test 5: Complex nested structures
    # !(test (is-alpha-member (f (g $x) $y) ((f (g $a) $b) (h $c $d))) true)
    yield m.eval(
        member(
            S.f(S.g(V.x), V.y),
            (S.f(S.g(V.a), V.b), S.h(V.c, V.d)),
            TRUE,
        )
    )
    # !(test (is-alpha-member (f (g $x) $x) ((f (g $a) $b) (f (g $c) $c))) true)
    yield m.eval(
        member(
            S.f(S.g(V.x), V.x),
            (S.f(S.g(V.a), V.b), S.f(S.g(V.c), V.c)),
            TRUE,
        )
    )

    # Test 6: Different arities should fail
    # !(test (is-alpha-member (f $x) ((f $x $y) (g $z))) false)
    yield m.eval(member(S.f(V.x), (S.f(V.x, V.y), S.g(V.z)), FALSE))

    # Test 7: Numbers and atoms
    # !(test (is-alpha-member 42 (1 2 42 3)) true)
    yield m.eval(member(42, (1, 2, 42, 3), TRUE))
    # !(test (is-alpha-member 99 (1 2 42 3)) false)
    yield m.eval(member(99, (1, 2, 42, 3), FALSE))

    # Test 8: Nested lists
    # !(test (is-alpha-member (1 $x) ((1 2) (3 4))) true)
    yield m.eval(member((1, V.x), ((1, 2), (3, 4)), TRUE))
    # !(test (is-alpha-member (1 $x) ((2 3) (4 5))) false)
    yield m.eval(member((1, V.x), ((2, 3), (4, 5)), FALSE))

    # Test 9: Multiple occurrences
    # !(test (is-alpha-member a (a b a c)) true)
    yield m.eval(member(S.a, (S.a, S.b, S.a, S.c), TRUE))

    # Test 10: Complex terms with same structure but different variables
    # !(test (is-alpha-member (f $x $y) ((f $a $b) (f $c $d))) true)
    yield m.eval(
        member(S.f(V.x, V.y), (S.f(V.a, V.b), S.f(V.c, V.d)), TRUE)
    )

    # Test 11: Single element list
    # !(test (is-alpha-member a (a)) true)
    yield m.eval(member(S.a, (S.a,), TRUE))
    # !(test (is-alpha-member b (a)) false)
    yield m.eval(member(S.b, (S.a,), FALSE))

    # Test 12: List with variables as elements
    # !(test (is-alpha-member $x ($y $z $w)) true)
    yield m.eval(member(V.x, (V.y, V.z, V.w), TRUE))

    # Test 13: Deeply nested structures
    # !(test (is-alpha-member (a (b (c $x))) ((a (b (c $d))) (e $f))) true)
    yield m.eval(
        member(
            S.a(S.b(S.c(V.x))),
            (S.a(S.b(S.c(V.d))), S.e(V.f)),
            TRUE,
        )
    )

    # Test 14: Terms with different functors
    # !(test (is-alpha-member (f $x) ((g $y) (h $z))) false)
    yield m.eval(member(S.f(V.x), (S.g(V.y), S.h(V.z)), FALSE))

    # Test 15: Empty complex terms
    # !(test (is-alpha-member () (() a b)) true)
    yield m.eval(member((), ((), S.a, S.b), TRUE))
    # !(test (is-alpha-member () (a b c)) false)
    yield m.eval(member((), (S.a, S.b, S.c), FALSE))

    # The closing form prints rather than tests: a let* chain whose last two
    # pairs name their results only to run them for the printing.
    # !(let* (($pat (hi name boss))
    #         ($dummy1 (println! (pattern:- $pat)))
    #         ($bool (is-alpha-member $new $pat))
    #         ($dummy2 (println! (is member:- $bool in pattern:- $pat))))
    #        ())
    yield m.eval(
        S["let*"](
            (
                (V.pat, (S.hi, S.name, S.boss)),
                (V.dummy1, S["println!"](S["pattern:-"](V.pat))),
                (V.bool, S["is-alpha-member"](V.new, V.pat)),
                (
                    V.dummy2,
                    S["println!"](
                        (S["is"], S["member:-"], V.bool, S["in"], S["pattern:-"], V.pat)
                    ),
                ),
            ),
            (),
        )
    )
