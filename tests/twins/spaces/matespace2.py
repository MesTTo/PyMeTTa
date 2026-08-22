"""The Python twin of examples/spaces/matespace2.metta: expand and mate interleaved.

Same growth as matespace, with `expand` and `mate` run together on each of the 80
rounds and each one reading a COLLAPSED snapshot of the matches rather than a live
stream. The one assertion measures a space of 1,297,533 atoms.

Every equation is written at the container door for the same single reason: a
compiled body resolves a free name against the engine's function registry, and
`case`, `once` and the hyphenated `add-atom` are all out of reach there
(residue, P14.4). The single runnable form is an assertion, so it is a term
either way.
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 39336332 across the P14 twin-style rewrite: equation().to()
#: with named symbols and tuples stores the same five atoms the nested expr()
#: calls stored, and the 80 interleaved rounds walk the same clauses. Measured
#: 39336332 before and after, which with matespace's own held figure is this
#: folder's evidence that the rewrite is spelling and not semantics.
#: Prior: ADDED 2026-08-22 at 39336332 by the wave-3 spaces baseline.
BUDGET = 39336332


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

    # The superpose of a collapse is the snapshot: every match is taken before
    # the first write lands.
    # (= (expand)
    #    (case (superpose (collapse (match &self (num $t) $t)))
    #          (($t ((add-atom-no-duplicate &self (num (M $t)))
    #                (add-atom-no-duplicate &self (num (W $t))))))))
    m += equation(S.expand()).to(
        S.case(
            S.superpose(S.collapse(S.match(here, S.num(V.t), V.t))),
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
    #    (case (superpose (collapse (match &self (num (M $t)) $t)))
    #          (($t (case (once (match &self (num (W $t)) $t))
    #                     (($t (add-atom-no-duplicate &self (num (C $t))))))))))
    m += equation(S.mate()).to(
        S.case(
            S.superpose(
                S.collapse(S.match(here, S.num(S.M(V.t)), V.t))
            ),
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

    # Apply expand and mate K times.
    # (= (rewriteK $n)
    #    (if (== $n 0) done (let* (($temp1 (expand)) ($temp2 (mate)))
    #                             (rewriteK (- $n 1)))))
    m += equation(S.rewriteK(V.n)).to(
        S["if"](
            V.n.eq(0),
            S.done,
            S["let*"](
                ((V.grown, S.expand()), (V.mated, S.mate())),
                S.rewriteK(V.n - 1),
            ),
        )
    )

    # Apply the rewrites K times, then match.
    # (= (mate-space-demo $K)
    #    (let* (($s (add-atom &self (num Z)))
    #           ($g (rewriteK $K)))
    #           (match &self (num $1) (num $1))))
    m += equation(S["mate-space-demo"](V.k)).to(
        S["let*"](
            (
                (V.seed, add(here, S.num(S.Z))),
                (V.grown, S.rewriteK(V.k)),
            ),
            S.match(here, S.num(V.x), S.num(V.x)),
        )
    )

    # !(test (length (collapse (mate-space-demo 80))) 1297533)
    yield m.eval(
        S.test(
            S.length(S.collapse(S["mate-space-demo"](80))), 1297533
        )
    )
