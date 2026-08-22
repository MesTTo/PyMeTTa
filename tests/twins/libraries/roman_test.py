r"""The Python twin of examples/libraries/roman_test.metta.

lib_roman's whole surface: higher-order mapping and folding, the nine set
operations, function composition, reverse function matching through `let`, and
the two sequencing utilities.

Most of the library's names are punctuation, `/=\`, `\==/`, `.`, `.:`, `&&&`,
`&^&`, which Python cannot spell as attributes, so each is named at the
`S["..."]` door and called. The data is Python tuples, which is what a MeTTa
expression already is.

Two term shapes here name an arithmetic head rather than using the operator.
`(+ 1)` and `(* 2)` are PARTIAL applications, which a binary operator has no
spelling for, and `(+ 1 1)` is over two ground numbers, where Python's `+` is
arithmetic and answers 2 before any term exists.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 212336 to 214065, +1729 (+0.81%), by the P14
#: twin-style rewrite: mfail's equation is now compiled from Python syntax by
#: @m.define instead of added as an already-built atom, and the compile costs
#: 1,729 inferences once. Prior: ADDED 2026-08-22 at 212336 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 214065

def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_roman))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_roman)))

    # Test higher order functions
    # !(test (map-flat (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(S.test(S["map-flat"](S["+"](1), (1, 2, 3)), (2, 3, 4)))
    # !(test (map-nested (+ 1) (1 (2 3))) (2 (3 4)))
    yield m.eval(
        S.test(S["map-nested"](S["+"](1), (1, (2, 3))), (2, (3, 4)))
    )

    # !(test (fold-flat + 0 (1 2 3)) 6)
    yield m.eval(S.test(S["fold-flat"](S["+"], 0, (1, 2, 3)), 6))
    # !(test (foldr-flat cons () (1 (2 3) 4)) (1 (2 3) 4))
    yield m.eval(
        S.test(
            S["foldr-flat"](S.cons, (), (1, (2, 3), 4)), (1, (2, 3), 4)
        )
    )
    # !(test (fold-nested + 0 (1 (2 3))) 6)
    yield m.eval(S.test(S["fold-nested"](S["+"], 0, (1, (2, 3))), 6))

    # Test set operations
    # !(test (/=\ (1 2 $a) (2 3 4)) (2 2))
    yield m.eval(S.test(S["/=\\"]((1, 2, V.a), (2, 3, 4)), (2, 2)))
    # !(test (/==\ (1 2 3) (2 3 4)) (2 3))
    yield m.eval(S.test(S["/==\\"]((1, 2, 3), (2, 3, 4)), (2, 3)))
    # !(test (/=a\ (1 2 $a) (2 $a 4)) (2 $a))
    yield m.eval(S.test(S["/=a\\"]((1, 2, V.a), (2, V.a, 4)), (2, V.a)))

    # !(test (\= (1 2 3) ($a 3 4)) (2))
    yield m.eval(S.test(S["\\="]((1, 2, 3), (V.a, 3, 4)), (2,)))
    # !(test (\== (1 2 3) (2 3 4)) (1))
    yield m.eval(S.test(S["\\=="]((1, 2, 3), (2, 3, 4)), (1,)))
    # !(test (\=a (1 2 $a) (2 $a 4)) (1))
    yield m.eval(S.test(S["\\=a"]((1, 2, V.a), (2, V.a, 4)), (1,)))

    # !(test (\=/ (1 2 3) ($a 3 4)) (2 1 3 4))
    yield m.eval(S.test(S["\\=/"]((1, 2, 3), (V.a, 3, 4)), (2, 1, 3, 4)))
    # !(test (\==/ (1 2 3) (2 3 4)) (1 2 3 4))
    yield m.eval(S.test(S["\\==/"]((1, 2, 3), (2, 3, 4)), (1, 2, 3, 4)))
    # !(test (\=a/ (1 2 $a) (2 $a 4)) (1 2 $a 4))
    yield m.eval(
        S.test(S["\\=a/"]((1, 2, V.a), (2, V.a, 4)), (1, 2, V.a, 4))
    )

    # Test composition
    # !(test (. (+ 1) (* 2) 1) 3)
    yield m.eval(S.test(S["."](S["+"](1), S["*"](2), 1), 3))
    # !(test (.: (+ 1) + 2 3) 6)
    yield m.eval(S.test(S[".:"](S["+"](1), S["+"], 2, 3), 6))
    # !(test (&&& (+ 2) (* 2) 1) (3 2))
    yield m.eval(S.test(S["&&&"](S["+"](2), S["*"](2), 1), (3, 2)))

    empty = m.fn("empty")

    @m.define
    def mfail(_x):
        # (= (mfail $x) (empty))
        return empty()

    # !(test (collapse (&^& (+ 1) (mfail) 1)) (2))
    yield m.eval(
        S.test(S.collapse(S["&^&"](S["+"](1), S.mfail(), 1)), (2,))
    )

    # Test reverse function matching
    # !(test (let (@ $lst (cons $h $t)) (1 2 3) ($lst $h $t)) ((1 2 3) 1 (2 3)))
    yield m.eval(
        S.test(
            S.let(
                S["@"](V.lst, S.cons(V.h, V.t)),
                (1, 2, 3),
                (V.lst, V.h, V.t),
            ),
            ((1, 2, 3), 1, (2, 3)),
        )
    )

    # !(test (let (head $x) (1 2 3) $x) 1)
    yield m.eval(S.test(S.let(S.head(V.x), (1, 2, 3), V.x), 1))
    # !(test (let (tail $xs) (1 2 3) $xs) (2 3))
    yield m.eval(S.test(S.let(S.tail(V.xs), (1, 2, 3), V.xs), (2, 3)))

    # !(test (let (mylast $x) (1 2 3) $x) 3)
    yield m.eval(S.test(S.let(S.mylast(V.x), (1, 2, 3), V.x), 3))
    # !(test (let (init $xs) (1 2 3) $xs) (1 2))
    yield m.eval(S.test(S.let(S.init(V.xs), (1, 2, 3), V.xs), (1, 2)))

    # !(test (let (rcons $xs $x) (1 2 3) ($xs $x)) ((1 2) 3))
    yield m.eval(
        S.test(
            S.let(S.rcons(V.xs, V.x), (1, 2, 3), (V.xs, V.x)), ((1, 2), 3)
        )
    )

    # Test utils
    # !(test (prog1 (+ 1 1) (+ 2 2)) 2)
    yield m.eval(S.test(S.prog1(S["+"](1, 1), S["+"](2, 2)), 2))
    # !(test (progn (+ 1 1) (+ 2 2)) 4)
    yield m.eval(S.test(S.progn(S["+"](1, 1), S["+"](2, 2)), 4))
