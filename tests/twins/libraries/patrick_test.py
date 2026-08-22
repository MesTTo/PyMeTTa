"""The Python twin of examples/libraries/patrick_test.metta.

lib_patrick's as-pattern, bounded `for`, and lambda-driven `iterate`.

`mirror` stays at the container door, recorded against P14.4: its body is a
`let` whose PATTERN is an as-pattern, `(@ $L (cons $head $tail))`, and a
compiled body binds plain names, so naming the whole and destructuring it at
once has no assignment spelling.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 28309 to 28309, +0 (+0.00%), by the P14 twin-style
#: rewrite: the twin's atoms are unchanged: mirror stays a container-door
#: equation because its let binds an as-pattern, and equation(...).to(...)
#: builds what S["="](...) built. Prior: ADDED 2026-08-22 at 28309 by the
#: wave-3 libraries baseline, which recorded no cause.
BUDGET = 28309


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_patrick))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_patrick)))

    # The as-pattern names the whole argument and destructures it at the same
    # time. It is a function, so it goes in the body under a `let` that unifies
    # it with the argument: a head is a pattern and matches structurally.
    # (= (mirror $A)
    #    (let $A (@ $L (cons $head $tail))
    #         (append (reverse $L) $tail)))
    m += equation(S.mirror(V.A)).to(
        S.let(
            V.A,
            S["@"](V.L, S.cons(V.head, V.tail)),
            S.append(S.reverse(V.L), V.tail),
        )
    )

    # !(test (mirror (h a n n e s)) (s e n n a h a n n e s))
    yield m.eval(
        S.test(
            S.mirror((S.h, S.a, S.n, S.n, S.e, S.s)),
            (S.s, S.e, S.n, S.n, S.a, S.h, S.a, S.n, S.n, S.e, S.s),
        )
    )

    # !(test (collapse (for $x (1 2 3 4 5 6)
    #                       (if (> $x 3) $x)))
    #        (4 5 6))
    yield m.eval(
        S.test(
            S.collapse(
                S["for"](V.x, (1, 2, 3, 4, 5, 6), S["if"](V.x > 3, V.x))
            ),
            (4, 5, 6),
        )
    )

    # !(test (iterate 0 10
    #                 1 (|-> ($i $x)
    #                        (+ $x $i)))
    #        46)
    yield m.eval(
        S.test(S.iterate(0, 10, 1, S["|->"]((V.i, V.x), V.x + V.i)), 46)
    )
