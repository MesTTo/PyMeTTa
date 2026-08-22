"""The Python twin of examples/spaces/spaces.metta: two writes inside a let, then a match.

`matchtrickery` adds two atoms and matches them in one expression, so what the
example shows is that `let*`'s bindings run before the match reads the space.

The equation is written at the container door rather than compiled from a Python
body, and the reason is one rung down: its body calls `add-atom`, a compiled body
resolves a free name EXACTLY as written, and Python cannot spell a hyphen, so no
compiled body reaches a hyphenated engine function (residue, P14.4).
`equation(lhs).to(rhs)` is that door's own builder for `(= lhs rhs)`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 2220 across the P14 twin-style rewrite, which is itself
#: the finding: equation().to() with named symbols and tuples stores the SAME
#: atom the nested expr() calls stored, and renaming the two throwaway let*
#: bindings ($t1, $t2 to $first, $second) costs nothing because a variable is
#: an identity rather than a spelling. Measured 2220 before and after.
#: Prior: ADDED 2026-08-22 at 2220 by the wave-3 spaces baseline.
BUDGET = 2220


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    add, here = S["add-atom"], S[m.space_name]

    # (= (matchtrickery)
    #    (let* (($t1 (add-atom &self (foo a)))
    #           ($t2 (add-atom &self (foo b))))
    #          (match &self (foo $1) (bar $1))))
    m += equation(S.matchtrickery()).to(
        S["let*"](
            (
                (V.first, add(here, S.foo(S.a))),
                (V.second, add(here, S.foo(S.b))),
            ),
            S.match(here, S.foo(V.x), S.bar(V.x)),
        )
    )

    # !(test (collapse (matchtrickery)) ((bar a) (bar b)))
    yield m.eval(S.test(S.collapse(S.matchtrickery()), (S.bar(S.a), S.bar(S.b))))
