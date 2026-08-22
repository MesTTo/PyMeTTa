"""examples/spaces/matespace.metta in Python: a space grown to a million atoms.

`expand` doubles every `num` atom into an M-branch and a W-branch, `expandK`
does that 390 times, `mate` pairs the branches, and the whole thing answers
just over a million atoms. It is a scale example, and the scale is what its
Python twin has to respect.

So this file counts IN THE ENGINE, and the measurement is the reason.
`list(answers)` is what `collapse` dissolves into, and at this size that
dissolution costs 111,707,981 inferences and 34.8 seconds against the engine's
own 26,313,301 and 5.9 seconds, a 4.25x on the counter and a 5.9x on the clock,
because a million atoms then cross the seam one at a time to be counted in
Python [measured 2026-08-22 on this tree]. Cross per collection, never per
element: here the collection is the answer set and the element is an atom, and
the number is the only thing worth carrying across.

Every definition is a term for reasons the residue already records: bodies
naming `case`, `once` and `add-atom`, and a `match` whose space is a parameter
(P14.4). The declaration below states that drop once rather than five times.
"""

from petta import S, V, equation

#: Why this twin sits below the top rung, stated once for the whole file.
RUNG = (
    "every definition here is built as a term: their bodies name case, once "
    "and add-atom, and add-atom-no-duplicate matches against a space its "
    "CALLER names, none of which a compiled body reaches (residue, P14.4); "
    "and the closing count stays in the engine because collapsing a million "
    "answers into Python costs 4.25x the inferences (measured 2026-08-22)"
)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 26324213 to 26324058, -155 (-0.0%), by the twin
#: contract change: `(test (length (collapse ...)) 1063919)` became one
#: `assert`, so the `test` wrapper left the engine while `length` and
#: `collapse` stayed in it deliberately. The million-atom rewrite underneath is
#: untouched, which is why the delta is three figures against twenty-six
#: million. Against the
#: example's 27400934 the ratio is 0.9607.
#: Prior: 26324213, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 26324058


def twin(m):
    """Grow a space by 390 doublings, mate the branches, and count what is left."""
    here = S[m.space_name]
    nodup = S["add-atom-no-duplicate"]

    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    seen = S.collapse(S.once(S.match(V.space, V.atom, V.atom)))
    m += equation(nodup(V.space, V.atom)).to(
        S["if"](S["=="]((), seen), S["add-atom"](V.space, V.atom), S.empty())
    )

    # (= (expand) (case (match &self (num $t) $t) (($t ((add-atom-no-duplicate ...))))))
    m += equation(S.expand()).to(
        S.case(
            S.match(here, S.num(V.t), V.t),
            ((V.t, (nodup(here, S.num(S.M(V.t))), nodup(here, S.num(S.W(V.t))))),),
        )
    )

    # (= (mate) (case (match &self (num (M $t)) $t) (($t (case (once ...) ...)))))
    paired = S.case(
        S.once(S.match(here, S.num(S.W(V.t)), V.t)),
        ((V.t, nodup(here, S.num(S.C(V.t)))),),
    )
    m += equation(S.mate()).to(
        S.case(S.match(here, S.num(S.M(V.t)), V.t), ((V.t, paired),))
    )

    # (= (expandK $n) (if (== $n 0) done (let $temp1 (expand) (expandK (- $n 1)))))
    m += equation(S.expandK(V.n)).to(
        S["if"](S["=="](V.n, 0), S.done, S.let(V.step, S.expand(), S.expandK(V.n - 1)))
    )

    # (= (mate-space-demo $K) (let* (($s (add-atom ...)) ($g (expandK $K)) ($h (mate)))
    #                               (match &self (num $1) (num $1))))
    m += equation(S["mate-space-demo"](V.k)).to(
        S["let*"](
            (
                (V.seed, S["add-atom"](here, S.num(S.Z))),
                (V.grown, S.expandK(V.k)),
                (V.mated, S.mate()),
            ),
            S.match(here, S.num(V.x), S.num(V.x)),
        )
    )

    assert m.one(S.length(S.collapse(S["mate-space-demo"](390)))) == 1063919
