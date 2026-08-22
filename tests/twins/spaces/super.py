"""The Python twin of examples/spaces/super.metta: an override that delegates.

A space can redefine a function it inherits, and `super` is how the new
definition reaches the old one, so a guard can check a call and then let it
through. It reaches the ENGINE's own definitions too, which is how `car-atom`
gets wrapped in one space and left alone in every other.

Naming a space IS Python's own name binding, so `bind! &guarded (new-space)` is
`m.space("&guarded")` and the space exists from its first write; each of the
four write forms answers the unit and the six assertions after them are what
prove which definition each space sees.

All three equations are written at the container door for one reason: their
bodies carry lowercase symbols as DATA (`stored`, `bad`, `refused`, `wrapped`)
and name `super` and `car-atom`. A compiled body reads a capitalised free name as
a data constructor and resolves a lowercase one as a function, `super` is not in
the engine's function registry, and Python cannot spell the hyphen in
`car-atom`, so none of the three has a compiled spelling (residue, P14.4).
"""

from petta import S, V, equation, expr

#: The answer group a write form contributes: `bind!` and `add-atom` each
#: answer the unit, which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13746 to 11780, -1966 (-14.3%), by the P14 twin-style
#: rewrite, and the whole delta is the four write forms: two space bindings
#: became `m.space(name)` and two equation adds became `space += equation(...)`,
#: 492 a form averaged. Both shapes save more than a plain fact does, whose
#: band across this folder is 239 to 311: an equation write compiles a clause
#: on either door and a space binding is a whole form. No equation moved to the
#: decorator door here, so nothing pulls the other way and the six assertions
#: are unchanged terms. Prior: ADDED 2026-08-22 at 13746 by the wave-3 spaces
#: baseline.
BUDGET = 11780


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    car_atom, here = S["car-atom"], S[m.space_name]

    # The definition every space below this one inherits.
    # (= (store $atom) (stored $atom))
    m += equation(S.store(V.atom)).to(S.stored(V.atom))

    # !(bind! &guarded (new-space))
    guarded = m.space("&guarded")
    yield WROTE

    # `super` names the next definition up THIS space's chain, so the guard
    # delegates without naming the space it shadows.
    # !(add-atom &guarded (= (store $atom)
    #                        (if (== $atom bad) refused (super (store $atom)))))
    guarded += equation(S.store(V.atom)).to(
        S["if"](V.atom.eq(S.bad), S.refused, S.super(S.store(V.atom)))
    )
    yield WROTE

    # !(test (evalc (store good) &guarded) (stored good))
    yield m.eval(
        S.test(
            S.evalc(S.store(S.good), S[guarded.space_name]),
            S.stored(S.good),
        )
    )
    # !(test (evalc (store bad) &guarded) refused)
    yield m.eval(
        S.test(S.evalc(S.store(S.bad), S[guarded.space_name]), S.refused)
    )

    # The space above is untouched by the shadow, which is what makes a shadow
    # a shadow rather than a replacement.
    # !(test (store bad) (stored bad))
    yield m.eval(S.test(S.store(S.bad), S.stored(S.bad)))

    # !(bind! &wrapping (new-space))
    wrapping = m.space("&wrapping")
    yield WROTE

    # A builtin can be WRAPPED rather than only replaced.
    # !(add-atom &wrapping (= (car-atom $expr) (wrapped (super (car-atom $expr)))))
    wrapping += equation(car_atom(V.expr)).to(
        S.wrapped(S.super(car_atom(V.expr)))
    )
    yield WROTE

    # !(test (evalc (car-atom (1 2 3)) &wrapping) (wrapped 1))
    yield m.eval(
        S.test(
            S.evalc(car_atom((1, 2, 3)), S[wrapping.space_name]),
            S.wrapped(1),
        )
    )

    # And every other space still gets the builtin it always had.
    # !(test (car-atom (1 2 3)) 1)
    yield m.eval(S.test(car_atom((1, 2, 3)), 1))

    # evalc is the other direction: it names the space to evaluate in
    # absolutely, where super names the next definition along, relatively.
    # !(test (evalc (store good) &self) (stored good))
    yield m.eval(S.test(S.evalc(S.store(S.good), here), S.stored(S.good)))
