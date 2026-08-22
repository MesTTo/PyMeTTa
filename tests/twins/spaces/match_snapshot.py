"""The Python twin of examples/spaces/match_snapshot.metta: match finds every row first.

`match` finds all the rows BEFORE any output template runs, so a template that
writes to the space cannot change what the match still has to answer. Three of
the four links form a loop, all three rows are found before the first reversal
breaks the cycle, and all three are reverted. The single-pattern case is the same
property reduced to its detector: two rows, each template removing the OTHER, and
a lazy query would lose the row it had not reached yet.

The facts and the two snapshot items go in through the container protocol. The
two `visit` equations stay at the container door because their heads carry a
literal ARGUMENT, `(visit alpha)`, which the compiled subset spells only as a
literal default, and their bodies call `remove-atom` and answer bare lowercase
symbols, neither of which a compiled body can spell (residue, P14.4).
"""

from petta import S, V, equation, expr

#: The answer group a write form contributes: `bind!` and `add-atom` each
#: answer the unit, which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 7027 to 6003, -1024 (-14.6%), by the P14 twin-style
#: rewrite, and the whole delta is the three write forms: the `bind!` became
#: `m.space("&snapshot")` and the two item adds became `snapshot += item`, 341
#: a form averaged, with the two plain writes inside this folder's 239-to-311
#: band and the space binding the rest. The four link facts already entered at
#: the container door, and the four assertions are unchanged terms.
#: Prior: ADDED 2026-08-22 at 7027 by the wave-3 spaces baseline.
BUDGET = 6003


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    add, remove, here = S["add-atom"], S["remove-atom"], S[m.space_name]

    # Three links form a loop and the fourth does not.
    # (link A B) (link B C) (link C A) (link C E)
    m += (S.link, S.A, S.B)
    m += (S.link, S.B, S.C)
    m += (S.link, S.C, S.A)
    m += (S.link, S.C, S.E)

    # The template reverses each loop link it is given, and all three rows were
    # found before the first reversal broke the cycle.
    # !(test (collapse (match &self (, (link $x $y) (link $y $z) (link $z $x))
    #                              (let () (remove-atom &self (link $x $y))
    #                                      (add-atom &self (link $y $x)))))
    #        (() () ()))
    yield m.eval(
        S.test(
            S.collapse(
                S.match(
                    here,
                    S[","](
                        S.link(V.x, V.y),
                        S.link(V.y, V.z),
                        S.link(V.z, V.x),
                    ),
                    S.let(
                        (),
                        remove(here, S.link(V.x, V.y)),
                        add(here, S.link(V.y, V.x)),
                    ),
                )
            ),
            ((), (), ()),
        )
    )

    # The four atoms upstream prints, as a set.
    # !(test (collapse (match &self (link $x $y) ($x $y))) ((C E) (B A) (C B) (A C)))
    yield m.eval(
        S.test(
            S.collapse(S.match(here, S.link(V.x, V.y), (V.x, V.y))),
            (
                (S.C, S.E),
                (S.B, S.A),
                (S.C, S.B),
                (S.A, S.C),
            ),
        )
    )

    # The single-pattern detector: two rows, each template removing the OTHER.
    # !(bind! &snapshot (new-space))
    snapshot = m.space("&snapshot")
    at_snapshot = S[snapshot.space_name]
    yield WROTE

    # !(add-atom &snapshot (item alpha))
    snapshot += S.item(S.alpha)
    yield WROTE
    # !(add-atom &snapshot (item beta))
    snapshot += S.item(S.beta)
    yield WROTE

    # (= (visit alpha) (let () (remove-atom &snapshot (item beta)) alpha))
    m += equation(S.visit(S.alpha)).to(
        S.let((), remove(at_snapshot, S.item(S.beta)), S.alpha)
    )
    # (= (visit beta) (let () (remove-atom &snapshot (item alpha)) beta))
    m += equation(S.visit(S.beta)).to(
        S.let((), remove(at_snapshot, S.item(S.alpha)), S.beta)
    )

    # A lazy query would lose the row it had not reached yet and answer once.
    # !(test (collapse (match &snapshot (item $x) (visit $x))) (alpha beta))
    yield m.eval(
        S.test(
            S.collapse(S.match(at_snapshot, S.item(V.x), S.visit(V.x))),
            (S.alpha, S.beta),
        )
    )

    # Both removals happened, so the space is empty.
    # !(test (collapse (get-atoms &snapshot)) ())
    yield m.eval(
        S.test(S.collapse(S["get-atoms"](at_snapshot)), ())
    )
