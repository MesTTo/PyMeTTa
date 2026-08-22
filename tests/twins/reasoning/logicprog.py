"""The Python twin of examples/reasoning/logicprog.metta: a recursive relation.

`successor` is six ground facts, so each is an `equation(head).to(True)` and
`True` is Python's own `True`, which encodes to the atom the example writes.

`later-in-alphabet` stays at the container door for two reasons that both
matter. Its two clauses are ALTERNATIVES, and stacked Python clauses read as
first-match, which would make the recursive clause unreachable; and the second
clause's `$Z` appears in neither head, while a free name in a compiled body is a
parameter, a known function, or a data constructor, never a fresh variable. So
the equation is built as the term it is, with `&` for `and`.

The two `!(add-atom &petta ...)` forms are runnable forms of the original, so
they are evaluated rather than written through the space handle: what the lane
prices is the evaluation the example performs, and `m.space("&petta") += ...`
would answer the expected group without running it.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 9036 across the term-door rewrite: `equation(...).to(...)`
#: and `&` build the same atoms the hand-nested `expr` calls built, which the
#: atom-level differential confirms byte-for-byte. Prior: ADDED 2026-08-22 at
#: 9036 by the wave-3 twin baseline.
BUDGET = 9036


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(add-atom &petta (dispatch-policy successor NoMatchEnum NoMatchFail))
    yield m.eval(
        S["add-atom"](
            S["&petta"],
            S["dispatch-policy"](S.successor, S.NoMatchEnum, S.NoMatchFail),
        )
    )

    # !(add-atom &petta (dispatch-policy later-in-alphabet NoMatchEnum NoMatchFail))
    yield m.eval(
        S["add-atom"](
            S["&petta"],
            S["dispatch-policy"](
                S["later-in-alphabet"], S.NoMatchEnum, S.NoMatchFail
            ),
        )
    )

    # (= (successor b a) True)
    m += equation(S.successor(S.b, S.a)).to(TRUE)
    # (= (successor c b) True)
    m += equation(S.successor(S.c, S.b)).to(TRUE)
    # (= (successor d c) True)
    m += equation(S.successor(S.d, S.c)).to(TRUE)
    # (= (successor e d) True)
    m += equation(S.successor(S.e, S.d)).to(TRUE)
    # (= (successor f e) True)
    m += equation(S.successor(S.f, S.e)).to(TRUE)
    # (= (successor g f) True)
    m += equation(S.successor(S.g, S.f)).to(TRUE)

    # (= (later-in-alphabet $X $Y)
    #    (successor $X $Y))
    m += equation(S["later-in-alphabet"](V.X, V.Y)).to(S.successor(V.X, V.Y))

    # (= (later-in-alphabet $X $Y)
    #    (and (successor $X $Z) (later-in-alphabet $Z $Y)))
    m += equation(S["later-in-alphabet"](V.X, V.Y)).to(
        S.successor(V.X, V.Z) & S["later-in-alphabet"](V.Z, V.Y)
    )

    # !(test (collapse ((later-in-alphabet d $1) $1))
    #        ((True c) (True b) (True a)))
    yield m.eval(
        S.test(
            S.collapse((S["later-in-alphabet"](S.d, V["1"]), V["1"])),
            ((True, S.c), (True, S.b), (True, S.a)),
        )
    )
