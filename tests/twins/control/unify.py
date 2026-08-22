"""The Python twin of examples/control/unify.metta: the matching conditional.

`(unify a b then else)` runs the THEN branch once per binding set under which
`a` and `b` match, and the ELSE branch exactly when no binding set exists. All
four arguments are typed `Atom`, so they cross unevaluated, and only the
selected branch runs; a built term is unevaluated by construction, so the term
door is the natural spelling for every form here.

The two probe equations are written at the container door: their bodies name
`chain` with a variable of its own and `add-atom`, and a compiled body resolves
a free name EXACTLY, so a hyphenated engine function cannot be reached from one
(wave one recorded that against P14.4 for `fibsmart`).
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9027 to 9314, +287, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 9027 by 47554fc's control/types twin baseline.
BUDGET = 9314


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # Ground decisions, including numeric promotion: 1 matches 1.0.
    # !(test (unify 1 1 same different) same)
    yield m.eval(S.test(S.unify(1, 1, S.same, S.different), S.same))
    # !(test (unify 1 2 same different) different)
    yield m.eval(S.test(S.unify(1, 2, S.same, S.different), S.different))
    # !(test (unify 1 1.0 same different) same)
    yield m.eval(S.test(S.unify(1, 1.0, S.same, S.different), S.same))
    # !(test (unify "x" "x" same different) same)
    yield m.eval(S.test(S.unify(val("x"), val("x"), S.same, S.different), S.same))
    # !(test (unify "x" "y" same different) different)
    yield m.eval(
        S.test(
            S.unify(val("x"), val("y"), S.same, S.different),
            S.different,
        )
    )

    # Bindings flow from the match into the branch, both directions at once.
    # !(test (unify (f $x b) (f a $y) (pair $x $y) nope) (pair a b))
    yield m.eval(
        S.test(
            S.unify(
                S.f(V.x, S.b),
                S.f(S.a, V.y),
                S.pair(V.x, V.y),
                S.nope,
            ),
            S.pair(S.a, S.b),
        )
    )

    # The occurs check rejects a cyclic binding.
    # !(test (unify $x (f $x) cyclic sound) sound)
    yield m.eval(S.test(S.unify(V.x, S.f(V.x), S.cyclic, S.sound), S.sound))

    # Only the selected branch evaluates: each probe leaves a marker, and
    # exactly one marker lands per query.
    # (= (then-probe) (chain (add-atom &self then-ran) $_ 3))
    m += equation(S["then-probe"]()).to(
        S.chain(S["add-atom"](S["&self"], S["then-ran"]), V.ignored, 3)
    )
    # (= (else-probe) (chain (add-atom &self else-ran) $_ 4))
    m += equation(S["else-probe"]()).to(
        S.chain(S["add-atom"](S["&self"], S["else-ran"]), V.ignored, 4)
    )

    # !(test (unify A A (then-probe) (else-probe)) 3)
    yield m.eval(
        S.test(
            S.unify(S.A, S.A, S["then-probe"](), S["else-probe"]()),
            3,
        )
    )
    # !(test (collapse (match &self else-ran hit)) ())
    yield m.eval(
        S.test(
            S.collapse(S.match(S["&self"], S["else-ran"], S.hit)),
            (),
        )
    )
    # !(test (unify A B (then-probe) (else-probe)) 4)
    yield m.eval(
        S.test(
            S.unify(S.A, S.B, S["then-probe"](), S["else-probe"]()),
            4,
        )
    )
    # !(test (collapse (match &self then-ran hit)) (hit))
    yield m.eval(
        S.test(
            S.collapse(S.match(S["&self"], S["then-ran"], S.hit)),
            (S.hit,),
        )
    )

    # A space is a grounded atom whose custom matching is query, so a space
    # operand routes through match: one then-answer per stored match, the
    # else branch when nothing matches.
    # (friend Bob Alice)
    m += S.friend(S.Bob, S.Alice)
    # (friend Sam Alice)
    m += S.friend(S.Sam, S.Alice)

    # !(test (collapse (unify &self (friend $who Alice) $who no-friends))
    #        (Bob Sam))
    yield m.eval(
        S.test(
            S.collapse(
                S.unify(
                    S["&self"],
                    S.friend(V.who, S.Alice),
                    V.who,
                    S["no-friends"],
                )
            ),
            (S.Bob, S.Sam),
        )
    )
    # !(test (unify &self (friend Pol $who) $who no-friends) no-friends)
    yield m.eval(
        S.test(
            S.unify(
                S["&self"],
                S.friend(S.Pol, V.who),
                V.who,
                S["no-friends"],
            ),
            S["no-friends"],
        )
    )

    # A variable operand binds the space whole without querying it.
    # !(test (unify $s &self bound queried) bound)
    yield m.eval(S.test(S.unify(V.s, S["&self"], S.bound, S.queried), S.bound))

    # Empty in a branch is the branch remover: the else here answers nothing
    # at all, so collapse answers the empty list.
    # !(test (collapse (unify a b then Empty)) ())
    yield m.eval(
        S.test(
            S.collapse(S.unify(S.a, S.b, S.then, S.Empty)),
            (),
        )
    )
