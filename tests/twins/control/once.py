"""The Python twin of examples/control/once.metta: taking the first answer.

The same program cut.metta writes with `cut`, written with `once`: two atoms
match `(foo $1)`, and `once` commits to the first, so only `(bar 1)` is stored.

`match-single` is written at the container door for the reason cut.py gives:
the compiled subset's `match(...)` takes a literal space name and a structural
pattern, so a definition parameterised over space, pattern and template has no
compiled spelling (P14.4).
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2331 to 2376, +45, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 2331 by 47554fc's control/types twin baseline.
BUDGET = 2376


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (foo 1)
    m += S.foo(1)
    # (foo 2)
    m += S.foo(2)

    # (= (match-single $space $pat $ret) (once (match $space $pat $ret)))
    m += equation(S["match-single"](V.space, V.pat, V.ret)).to(
        S.once(S.match(V.space, V.pat, V.ret))
    )

    # !(let $x (match-single &self (foo $1) $1) (add-atom &self (bar $x)))
    # answers (())
    yield m.eval(
        S.let(
            V.x,
            S["match-single"](S["&self"], S.foo(V.one), V.one),
            S["add-atom"](S["&self"], S.bar(V.x)),
        )
    )

    # !(test (collapse (match &self (bar $1) (bar $1))) ((bar 1)))
    yield m.eval(
        S.test(
            S.collapse(S.match(S["&self"], S.bar(V.one), S.bar(V.one))),
            (S.bar(1),),
        )
    )
