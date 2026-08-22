"""The Python twin of examples/control/sealed.metta: freshening variables.

`sealed` answers an Atom whose variables are fresh, except the ones named in
its ignore list, and the caller runs that Atom with `eval` when it wants to.
Everything here is about the IDENTITY of variables, so every form is built as
a term: a variable is `V.x`, an ignore list is an expression of variables, and
the answers carry variables the lane compares up to consistent renaming, which
is why `((7 $unbound))` and `((7 $anything))` are the same answer.

`mk-tagger` is written at the container door. Its body is a lambda, which a
compiled body does spell, but the lambda's own body mints `(tagged $item
$fresh)`: `tagged` is a lowercase free name a compiled body resolves as a
FUNCTION, and `$fresh` is a variable the equation introduces rather than a
parameter, which no Python binding names. Wave one recorded the first half
against P14.4 for `time_and_pragmas`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9491 to 9793, +302, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 9491 by 47554fc's control/types twin baseline.
BUDGET = 9793


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # The rename happens when the expression is compiled, not after an outer
    # binding has already consumed the variable.
    # !(test (let $atom (sealed () (let $x 2 $x)) (eval $atom)) 2)
    yield m.eval(
        S.test(
            S.let(
                V.atom,
                S.sealed((), S.let(V.x, 2, V.x)),
                S.eval(V.atom),
            ),
            2,
        )
    )

    # An unbound variable is freshened the same way.
    # !(test (let $atom (sealed () (let $y 5 $y)) (eval $atom)) 5)
    yield m.eval(
        S.test(
            S.let(
                V.atom,
                S.sealed((), S.let(V.y, 5, V.y)),
                S.eval(V.atom),
            ),
            5,
        )
    )

    # The ignore list keeps the surrounding identity. Every other variable in
    # the returned Atom is fresh.
    # !(test (collapse (let $z 7 (sealed ($z) ($z $w)))) ((7 $unbound)))
    yield m.eval(
        S.test(
            S.collapse(S.let(V.z, 7, S.sealed((V.z,), (V.z, V.w)))),
            ((7, V.unbound),),
        )
    )

    # A ground Atom has no variable to rename.
    # !(test (sealed () 42) 42)
    yield m.eval(S.test(S.sealed((), 42), 42))

    # Nested sealed forms produce nested data. Each eval consumes one
    # returned layer, and each layer owns a distinct fresh variable.
    # !(test (let $atom (sealed () (let $n 2 (sealed () (let $n 3 $n))))
    #          (let $step (eval $atom) (eval $step)))
    #        3)
    yield m.eval(
        S.test(
            S.let(
                V.atom,
                S.sealed(
                    (),
                    S.let(
                        V.n,
                        2,
                        S.sealed((), S.let(V.n, 3, V.n)),
                    ),
                ),
                S.let(V.step, S.eval(V.atom), S.eval(V.step)),
            ),
            3,
        )
    )

    # A lambda renames its binders on every application; sealed freshens the
    # other variables in its returned Atom.
    # (= (mk-tagger) (|-> ($item) (sealed ($item) (tagged $item $fresh))))
    m += equation(S["mk-tagger"]()).to(
        S["|->"](
            (V.item,),
            S.sealed((V.item,), S.tagged(V.item, V.fresh)),
        )
    )

    # !(test (collapse (let $f (mk-tagger) (superpose (($f 1) ($f 2)))))
    #        ((tagged 1 $a) (tagged 2 $b)))
    yield m.eval(
        S.test(
            S.collapse(
                S.let(
                    V.f,
                    S["mk-tagger"](),
                    S.superpose(((V.f, 1), (V.f, 2))),
                )
            ),
            (S.tagged(1, V.a), S.tagged(2, V.b)),
        )
    )

    # An ignored variable keeps its surrounding binding.
    # !(test (collapse (let $outer 7 (sealed ($outer) (both $outer $local))))
    #        ((both 7 $c)))
    yield m.eval(
        S.test(
            S.collapse(
                S.let(
                    V.outer,
                    7,
                    S.sealed((V.outer,), S.both(V.outer, V.local)),
                )
            ),
            (S.both(7, V.c),),
        )
    )

    # Freshen a rule's variables before adding it so two stored rules do not
    # share one identity. `let` forces sealed first; placing sealed directly
    # under add-atom would store the sealed expression itself.
    # !(let $rule (sealed () (stored-rule $r ok)) (add-atom &self $rule))
    # answers (())
    stored = S.let(
        V.rule,
        S.sealed((), S["stored-rule"](V.r, S.ok)),
        S["add-atom"](S["&self"], V.rule),
    )
    yield m.eval(stored)
    yield m.eval(stored)

    # !(test (collapse (match &self (stored-rule $x $y) ($x $y)))
    #        (($p ok) ($q ok)))
    yield m.eval(
        S.test(
            S.collapse(
                S.match(
                    S["&self"],
                    S["stored-rule"](V.x, V.y),
                    (V.x, V.y),
                )
            ),
            ((V.p, S.ok), (V.q, S.ok)),
        )
    )

    # The ignored $y keeps its binding; the unignored $x is fresh.
    # !(test (collapse (let $x 1 (let $y 2 (sealed ($y) (pair $x $y)))))
    #        ((pair $fresh 2)))
    yield m.eval(
        S.test(
            S.collapse(
                S.let(
                    V.x,
                    1,
                    S.let(
                        V.y,
                        2,
                        S.sealed((V.y,), S.pair(V.x, V.y)),
                    ),
                )
            ),
            (S.pair(V.fresh, 2),),
        )
    )

    # The returned Atom stays inert until eval is asked to run it.
    # !(test (let $atom (sealed () (+ 1 2)) (eval $atom)) 3)
    yield m.eval(
        S.test(
            S.let(
                V.atom,
                S.sealed((), S["+"](1, 2)),
                S.eval(V.atom),
            ),
            3,
        )
    )
