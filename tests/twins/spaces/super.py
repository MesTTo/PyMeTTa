"""examples/spaces/super.metta in Python: reaching the definition you shadow.

A space can redefine a function it inherits, and `super` is how the new
definition reaches the old one. Without it an override is replace-or-nothing,
and a guard that wants to check a call and then let it through has no way
through. It reaches the ENGINE's own definitions too, so a builtin can be
WRAPPED rather than only replaced.

Every equation here is written at the container door, and the reasons stack up.
`super` is a translator form rather than a registry function, so `is_function`
answers False and a compiled body naming it is refused. The bodies also carry
lowercase symbols as DATA, `(stored $atom)` and `refused`, where a compiled
body reads a lowercase free name as a call and a capitalised one as a different
atom (residue, P14.4).

Asking is ordinary: `space.eval(term)` is evalc, and `space.fn(name)` is the
same function asked in that space, which is how the wrapped `car-atom` and the
untouched one are the same question put to two handles.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11780 to 8357, -3423 (-29.1%), by the twin contract
#: change: six `(test ...)` terms became six Python `assert`s, so the `test`
#: wrapper left the engine six times while the three equations and every
#: evaluation over them stayed in it. Against the example's 22035 the ratio is
#: 0.3793.
#: Prior: 11780, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 8357


def twin(m):
    """Shadow one definition and one builtin, then delegate to each."""
    # (= (store $atom) (stored $atom)): the definition every space below
    # this one inherits.
    m += equation(S.store(V.atom)).to(S.stored(V.atom))

    # A space that gates it. `super` names the next definition up THIS space's
    # chain, so the guard delegates without naming what it delegates to.
    guarded = m.space("&guarded")
    guarded += equation(S.store(V.atom)).to(
        S["if"](S["=="](V.atom, S.bad), S.refused, S.super(S.store(V.atom)))  # rung: the stored body of an equation naming `super`, which no compiled body reaches
    )

    assert guarded.eval(S.store(S.good)) == [S.stored(S.good)]
    assert guarded.eval(S.store(S.bad)) == [S.refused]
    # The space above is untouched by the shadow, which is what makes a shadow
    # a shadow rather than a replacement.
    assert m.eval(S.store(S.bad)) == [S.stored(S.bad)]

    # `super` reaches the engine's own definitions too.
    wrapping = m.space("&wrapping")
    head = S["car-atom"](V.expr)  # rung: an override OF `car-atom`, so the head is the point rather than e[0]
    wrapping += equation(head).to(S.wrapped(S.super(head)))

    assert wrapping.fn("car-atom")((1, 2, 3)) == S.wrapped(1)
    # And every other space still gets the builtin it always had.
    assert m.fn("car-atom")((1, 2, 3)) == 1

    # `evalc` is the other direction: it names the space absolutely, where
    # `super` names the next definition along, relatively.
    assert m.eval(S.store(S.good)) == [S.stored(S.good)]
