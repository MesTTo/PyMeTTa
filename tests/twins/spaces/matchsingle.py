"""The Python twin of examples/spaces/matchsingle.metta: two ways to take one match.

`(a b)` and `(a c)` both match, and both functions answer only the first: one by
cutting after the match, one by wrapping it in `once`.

Both equations are written at the container door. The reason is the same for
each and it is precise: a compiled body resolves a free name against the engine's
FUNCTION REGISTRY, and `cut` and `once` are not in it — they are forms the
translator handles, so `is_function` answers False for both and a body naming
them is refused (residue, P14.4). The facts above them are ordinary tuples,
which is the shape the knowledge front actually reads.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 3764 across the P14 twin-style rewrite, and the holding
#: is the finding: `m += (S.a, S.b)` stores what `expr(S["a"], S["b"])` stored,
#: equation().to() stores what the nested expr() equation stored, and renaming
#: $x and $temp costs nothing because a variable is an identity rather than a
#: spelling. Measured 3764 before and after.
#: Prior: ADDED 2026-08-22 at 3764 by the wave-3 spaces baseline.
BUDGET = 3764


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    here = S[m.space_name]

    # (a b)
    m += (S.a, S.b)
    # (a c)
    m += (S.a, S.c)

    # (= (match-single-via-cut $space $pattern $outPattern)
    #    (let* (($x (match $space $pattern $outPattern))
    #           ($temp (cut)))
    #          $x))
    m += equation(
        S["match-single-via-cut"](V.space, V.pattern, V.out)
    ).to(
        S["let*"](
            (
                (V.found, S.match(V.space, V.pattern, V.out)),
                (V.cut, S.cut()),
            ),
            V.found,
        )
    )

    # (= (match-single-via-once $space $pattern $outPattern)
    #    (once (match $space $pattern $outPattern)))
    m += equation(
        S["match-single-via-once"](V.space, V.pattern, V.out)
    ).to(S.once(S.match(V.space, V.pattern, V.out)))

    # !(test (collapse (match-single-via-cut &self (a $x) (a $x))) ((a b)))
    yield m.eval(
        S.test(
            S.collapse(
                S["match-single-via-cut"](here, S.a(V.x), S.a(V.x))
            ),
            (S.a(S.b),),
        )
    )

    # !(test (collapse (match-single-via-once &self (a $x) (a $x))) ((a b)))
    yield m.eval(
        S.test(
            S.collapse(
                S["match-single-via-once"](here, S.a(V.x), S.a(V.x))
            ),
            (S.a(S.b),),
        )
    )
