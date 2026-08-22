"""The Python twin of examples/control/and_then_or_else.metta: short-circuiting.

`and-then` and `or-else` are the SHORT-CIRCUITING boolean connectives, and they
are special forms rather than functions, which is the whole point: a function's
arguments are evaluated before the call, so a function could not skip its
second one. `and` and `or` are the other pair, RELATIONAL, evaluating both
sides and able to solve for an unbound argument.

Python has both readings too, and they do not line up with the operators.
`x and y` in Python short-circuits, so it is `and-then`; `&` on a built term
lowers to `(and ...)`, the relational one. This twin builds terms rather than
using either operator, because every operand here is a term the form must
receive UNEVALUATED, which is what a built term already is.

The two `note` equations are written at the container door: their bodies name
`add-atom`, and a compiled body resolves a free name EXACTLY, so a hyphenated
engine function cannot be reached from one (wave one recorded that against
P14.4 for `fibsmart`).
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11461 to 11903, +442, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 11461 by 47554fc's control/types twin baseline.
BUDGET = 11903


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (and-then True yes) yes)
    yield m.eval(S.test(S["and-then"](TRUE, S.yes), S.yes))
    # !(test (and-then False yes) False)
    yield m.eval(S.test(S["and-then"](FALSE, S.yes), FALSE))
    # !(test (or-else True no) True)
    yield m.eval(S.test(S["or-else"](TRUE, S.no), TRUE))
    # !(test (or-else False fallback) fallback)
    yield m.eval(S.test(S["or-else"](FALSE, S.fallback), S.fallback))

    # They take expressions, not just literals.
    # !(test (and-then (> 2 1) (> 3 2)) True)
    yield m.eval(S.test(S["and-then"](S[">"](2, 1), S[">"](3, 2)), TRUE))
    # !(test (or-else (> 1 2) (> 3 2)) True)
    yield m.eval(S.test(S["or-else"](S[">"](1, 2), S[">"](3, 2)), TRUE))

    # The skipping itself, which is the reason they are special forms. A
    # branch that is skipped must leave no trace, so this records what
    # actually ran.
    # !(bind! &ran (new-space)) answers (())
    yield m.eval(S["bind!"](S["&ran"], S["new-space"]()))

    # (= (note $tag) (let $_ (add-atom &ran (ran $tag)) True))
    m += equation(S.note(V.tag)).to(
        S.let(
            V.ignored,
            S["add-atom"](S["&ran"], S.ran(V.tag)),
            TRUE,
        )
    )

    # !(and-then False (note skipped-by-and-then)) answers (False)
    yield m.eval(S["and-then"](FALSE, S.note(S["skipped-by-and-then"])))
    # !(or-else True (note skipped-by-or-else)) answers (True)
    yield m.eval(S["or-else"](TRUE, S.note(S["skipped-by-or-else"])))
    # !(and-then True (note taken-by-and-then)) answers (True)
    yield m.eval(S["and-then"](TRUE, S.note(S["taken-by-and-then"])))
    # !(or-else False (note taken-by-or-else)) answers (True)
    yield m.eval(S["or-else"](FALSE, S.note(S["taken-by-or-else"])))

    # !(test (collapse (get-atoms &ran))
    #        ((ran taken-by-and-then) (ran taken-by-or-else)))
    yield m.eval(
        S.test(
            S.collapse(S["get-atoms"](S["&ran"])),
            (
                S.ran(S["taken-by-and-then"]),
                S.ran(S["taken-by-or-else"]),
            ),
        )
    )

    # The contrast, in one place: `and` does NOT skip, so its second
    # argument runs even though the first is False.
    # !(bind! &ran2 (new-space)) answers (())
    yield m.eval(S["bind!"](S["&ran2"], S["new-space"]()))

    # (= (note2 $tag) (let $_ (add-atom &ran2 (ran $tag)) True))
    m += equation(S.note2(V.tag)).to(
        S.let(
            V.ignored,
            S["add-atom"](S["&ran2"], S.ran(V.tag)),
            TRUE,
        )
    )

    # !(and False (note2 and-runs-it)) answers (False)
    yield m.eval(FALSE & S.note2(S["and-runs-it"]))
    # !(and-then False (note2 and-then-skips-it)) answers (False)
    yield m.eval(S["and-then"](FALSE, S.note2(S["and-then-skips-it"])))
    # !(test (collapse (get-atoms &ran2)) ((ran and-runs-it)))
    yield m.eval(
        S.test(
            S.collapse(S["get-atoms"](S["&ran2"])),
            (S.ran(S["and-runs-it"]),),
        )
    )

    # And the other side of the trade: and-then cannot be solved backwards,
    # where `and` can.
    # !(test (collapse (if (and-then (or-else $p True) $q) ($p $q))) ())
    yield m.eval(
        S.test(
            S.collapse(
                S["if"](
                    S["and-then"](S["or-else"](V.p, TRUE), V.q),
                    (V.p, V.q),
                )
            ),
            (),
        )
    )
