"""The Python twin of examples/reasoning/peano.metta: growing a space 300 times.

All four definitions stay at the container door, and each names the construct
that has no compiled spelling:

- `add-atom-no-duplicate` matches against a space its CALLER names, and a
  compiled `match()` takes its space as a literal `"&name"`, never a parameter;
- `expand-once` is a `case`, which is what Python's `match` statement would
  spell and the subset has no lowering for it yet;
- `expandK` and `demo-peano` bind with `let` and `let*` over calls to the two
  names above, and a compiled body reaches an undefined name only through
  `m.fn`, which would put back the very indirection the ladder is measuring.

What the term door does reach is Python's own operators: `x.eq(y)` is the
equality TERM (`==` itself is structural equality between atoms) and `n - 1`
is `(- $n 1)`, so no arithmetic here is written as a call.
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 2186406 across the term-door rewrite: `equation(...)`,
#: `.eq`, `-` and the tuple form build the same atoms the hand-nested `expr`
#: calls built, which the atom-level differential confirms byte-for-byte.
#: Prior: ADDED 2026-08-22 at 2186406 by the wave-3 twin baseline.
BUDGET = 2186406


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    m += equation(S["add-atom-no-duplicate"](V.Space, V.Atom)).to(
        S["if"](
            expr().eq(S.collapse(S.once(S.match(V.Space, V.Atom, V.Atom)))),
            S["add-atom"](V.Space, V.Atom),
            S.empty(),
        )
    )

    # For every existing num($t), add num(S $t):
    # (= (expand-once)
    #    (case (match &self (num $t) $t)
    #          (($x (add-atom-no-duplicate &self (num (S $x)))))))
    m += equation(S["expand-once"]()).to(
        S.case(
            S.match(S["&self"], S.num(V.t), V.t),
            ((V.x, S["add-atom-no-duplicate"](S["&self"], S.num(S.S(V.x)))),),
        )
    )

    # Peano builders:
    # (= (expandK $n)
    #    (if (== $n 0)
    #        done
    #        (let $temp1 (expand-once)
    #             (expandK (- $n 1)))))
    m += equation(S.expandK(V.n)).to(
        S["if"](
            V.n.eq(0),
            S.done,
            S.let(V.temp1, S["expand-once"](), S.expandK(V.n - 1)),
        )
    )

    # Peano demo:
    # (= (demo-peano $K)
    #    (let* (($s (add-atom &self (num Z)))
    #           ($g (expandK $K)))
    #          (match &self (num $1) $1)))
    m += equation(S["demo-peano"](V.K)).to(
        S["let*"](
            (
                (V.s, S["add-atom"](S["&self"], S.num(S.Z))),
                (V.g, S.expandK(V.K)),
            ),
            S.match(S["&self"], S.num(V["1"]), V["1"]),
        )
    )

    # !(test (length (collapse (demo-peano 300))) 301)
    yield m.eval(S.test(S.length(S.collapse(S["demo-peano"](300))), 301))
