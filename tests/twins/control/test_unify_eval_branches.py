"""The Python twin of examples/control/test_unify_eval_branches.metta.

Space-based `unify` EVALUATES the branch it selects, so a then-branch holding
`(+ 1 2)` answers 3 rather than the expression, and an else-branch holding
another `unify` runs it. The original was inspired by pverify's `add_c`/`add_v`
conflict checks, which nest `unify` calls in the else branch.

The knowledge-base atoms carry MeTTa STRING literals, `"$c"` and `"$v"`, which
are data rather than programs: `val(...)` marks them so that reading the twin
says which strings the engine sees as values. `"$c"` is not a variable; the
quotes are the whole reason it is a string.
"""

from petta import S, val

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `(+ 1 2)` and `(+ 10 20)` are branches `unify` is handed as DATA and have two GROUND
#: operands each, where Python's `+` computes the sum instead of building the term.
RUNG = "ground operands: the branches (+ 1 2) and (+ 10 20) have two each, where Python's + computes the sum"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11955 to 12097, +142, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 11955 by 47554fc's control/types twin baseline.
BUDGET = 12097


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_he)) answers (())
    yield m.eval(S["import!"](S["&self"], (S.library, S.lib_he)))

    # Knowledge base atoms, like pverify's Constant/Var declarations.
    # (Constant wff (Type "$c"))
    m += S.Constant(S.wff, S.Type(val("$c")))
    # (Var x 0 (Type "$v"))
    m += S.Var(S.x, 0, S.Type(val("$v")))

    # Test 1: then-branch needs eval (expression in matched case).
    # !(test (unify &self (Constant wff (Type "$c"))
    #          (Error (Constant wff) "already declared")
    #          ())
    #        (Error (Constant wff) "already declared"))
    declared = S.Error(S.Constant(S.wff), val("already declared"))
    yield m.eval(
        S.test(
            S.unify(
                S["&self"],
                S.Constant(S.wff, S.Type(val("$c"))),
                declared,
                (),
            ),
            declared,
        )
    )

    # Test 2: else-branch needs eval (fallthrough to nested unify).
    # !(test (unify &self (Constant y (Type "$c"))
    #          (Error (Constant y) "already declared")
    #          (unify &self (Var y 0 (Type "$v"))
    #            (Error (Var y) "active variable conflict")
    #            ()))
    #        ())
    yield m.eval(
        S.test(
            S.unify(
                S["&self"],
                S.Constant(S.y, S.Type(val("$c"))),
                S.Error(S.Constant(S.y), val("already declared")),
                S.unify(
                    S["&self"],
                    S.Var(S.y, 0, S.Type(val("$v"))),
                    S.Error(S.Var(S.y), val("active variable conflict")),
                    (),
                ),
            ),
            (),
        )
    )

    # Test 3: else-branch nested unify hits (real conflict chain).
    # !(test (unify &self (Constant x (Type "$c"))
    #          (Error (Constant x) "already declared")
    #          (unify &self (Var x 0 (Type "$v"))
    #            (Error (Var x) "active variable conflict")
    #            ()))
    #        (Error (Var x) "active variable conflict"))
    conflict = S.Error(S.Var(S.x), val("active variable conflict"))
    yield m.eval(
        S.test(
            S.unify(
                S["&self"],
                S.Constant(S.x, S.Type(val("$c"))),
                S.Error(S.Constant(S.x), val("already declared")),
                S.unify(
                    S["&self"],
                    S.Var(S.x, 0, S.Type(val("$v"))),
                    conflict,
                    (),
                ),
            ),
            conflict,
        )
    )

    # Test 4: arithmetic in branches (minimal reproducer).
    # !(test (unify &self (Constant wff (Type "$c")) (+ 1 2) 0) 3)
    yield m.eval(
        S.test(
            S.unify(
                S["&self"],
                S.Constant(S.wff, S.Type(val("$c"))),
                S["+"](1, 2),
                0,
            ),
            3,
        )
    )

    # Test 5: arithmetic in else-branch.
    # !(test (unify &self (Constant NOSUCH (Type "$c")) 0 (+ 10 20)) 30)
    yield m.eval(
        S.test(
            S.unify(
                S["&self"],
                S.Constant(S.NOSUCH, S.Type(val("$c"))),
                0,
                S["+"](10, 20),
            ),
            30,
        )
    )
