"""The Python twin of examples/spaces/matespace.metta: a space grown by rewriting.

`expand` doubles the set of `(num ...)` atoms 390 times and `mate` pairs the M
and W branches, so the one assertion measures a space of 1,063,919 atoms built by
nothing but matching and adding. It is this folder's scale test.

Every equation is written at the container door, and one reason covers all five:
a compiled body resolves a free name against the engine's function registry, and
`case`, `once`, `super`-style forms and the hyphenated `add-atom` are all out of
reach there, the first two because they are translator forms rather than registry
functions and the last because Python cannot spell a hyphen (residue, P14.4).
The single runnable form is an assertion, so it is a term either way.
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 26324213 across the P14 twin-style rewrite, and holding at
#: 26.3 million is the strongest evidence in this folder that the rewrite is
#: spelling and not semantics: equation().to() with named symbols and tuples
#: stores the same five atoms the nested expr() calls stored, and the 390
#: expansion rounds walk the same clauses. Measured 26324213 before and after.
#: Prior: ADDED 2026-08-22 at 26324213 by the wave-3 spaces baseline.
BUDGET = 26324213


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    add, here = S["add-atom"], S[m.space_name]
    once = S["add-atom-no-duplicate"]

    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    m += equation(once(V.space, V.atom)).to(
        S["if"](
            expr().eq(
                S.collapse(S.once(S.match(V.space, V.atom, V.atom)))
            ),
            add(V.space, V.atom),
            S.empty(),
        )
    )

    # (= (expand)
    #    (case (match &self (num $t) $t)
    #          (($t ((add-atom-no-duplicate &self (num (M $t)))
    #                (add-atom-no-duplicate &self (num (W $t))))))))
    m += equation(S.expand()).to(
        S.case(
            S.match(here, S.num(V.t), V.t),
            (
                (
                    V.t,
                    (
                        once(here, S.num(S.M(V.t))),
                        once(here, S.num(S.W(V.t))),
                    ),
                ),
            ),
        )
    )

    # (= (mate)
    #    (case (match &self (num (M $t)) $t)
    #          (($t (case (once (match &self (num (W $t)) $t))
    #                     (($t (add-atom-no-duplicate &self (num (C $t))))))))))
    m += equation(S.mate()).to(
        S.case(
            S.match(here, S.num(S.M(V.t)), V.t),
            (
                (
                    V.t,
                    S.case(
                        S.once(S.match(here, S.num(S.W(V.t)), V.t)),
                        ((V.t, once(here, S.num(S.C(V.t)))),),
                    ),
                ),
            ),
        )
    )

    # Apply expand K times.
    # (= (expandK $n)
    #    (if (== $n 0) done (let $temp1 (expand) (expandK (- $n 1)))))
    m += equation(S.expandK(V.n)).to(
        S["if"](
            V.n.eq(0),
            S.done,
            S.let(V.step, S.expand(), S.expandK(V.n - 1)),
        )
    )

    # Apply expand K times, then mate, then match.
    # (= (mate-space-demo $K)
    #    (let* (($s (add-atom &self (num Z)))
    #           ($g (expandK $K))
    #           ($h (mate)))
    #           (match &self (num $1) (num $1))))
    m += equation(S["mate-space-demo"](V.k)).to(
        S["let*"](
            (
                (V.seed, add(here, S.num(S.Z))),
                (V.grown, S.expandK(V.k)),
                (V.mated, S.mate()),
            ),
            S.match(here, S.num(V.x), S.num(V.x)),
        )
    )

    # !(test (length (collapse (mate-space-demo 390))) 1063919)
    yield m.eval(
        S.test(
            S.length(S.collapse(S["mate-space-demo"](390))), 1063919
        )
    )
