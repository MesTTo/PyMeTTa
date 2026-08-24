"""Purpose: examples/spaces/super.metta in Python: reaching the definition you shadow.

A space can redefine a function it inherits, and `super` is how the new
definition reaches the old one. Without it an override is replace-or-nothing,
and a guard that wants to check a call and then let it through has no way
through. It reaches the ENGINE's own definitions too, so a builtin can be
WRAPPED rather than only replaced.

The base definition compiles: `S.stored` is the mention door reading a
lowercase symbol as the data it is. The two overrides do not, and one blocker
is all that is left of the two this file used to carry: `super` is a translator
form rather than a registry function, so `is_function` answers False and a
compiled body naming it is refused (residue, P14.4)
[measured 2026-08-24: `fn.super` in a compiled body is refused with "names no
target function in this space's catalog"; commit=WORKTREE]. PERFECT: `super`
joins the registry, so an override is `@guarded.define def store(atom)` with
`fn.super` in its body.

Inside those stored terms the comparison is written by its WORD, `S.eq(a, b)`
being the atom `==`, because the four rich comparisons carry the engine's total
order of terms and a term outside a compiled body is built by naming its head.

Asking is ordinary: `space.eval(term)` is evalc, and `space.fn.<name>` is the
same function asked in that space, which is how the wrapped `car-atom` and the
untouched one are the same question put to two handles.
"""

import metta
from metta import S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Shadow one definition and one builtin, then delegate to each."""

    # (= (store $atom) (stored $atom)): the definition every space below
    # this one inherits.
    @m.define
    def store(atom):
        return S.stored(atom)

    # A space that gates it. `super` names the next definition up THIS space's
    # chain, so the guard delegates without naming what it delegates to.
    guarded = metta.space(S.guarded)
    guarded += equation(S.store(V.atom)).to(
        if_(S.eq(V.atom, S.bad), S.refused, fn.super(S.store(V.atom)))  # rung: the stored body of an equation naming `super`, which no compiled body reaches
    )

    assert guarded.eval(S.store(S.good)) == [S.stored(S.good)]
    assert guarded.eval(S.store(S.bad)) == [S.refused]
    # The space above is untouched by the shadow, which is what makes a shadow
    # a shadow rather than a replacement.
    assert store(S.bad) == [S.stored(S.bad)]

    # `super` reaches the engine's own definitions too.
    wrapping = metta.space(S.wrapping)
    head = fn.car_atom(V.expr)
    wrapping += equation(head).to(S.wrapped(fn.super(head)))  # rung: as above

    # `e[0]` is the dissolved spelling of car-atom everywhere the question is
    # "what is this expression's head". It is the wrong question here: this
    # example OVERRIDES car-atom, so the claim has to reach the space's own
    # equations, which only naming the head does.
    assert wrapping.fn.car_atom((1, 2, 3)).one() == S.wrapped(1)  # rung: the subject is the override, not the head
    # And every other space still gets the builtin it always had.
    assert m.fn.car_atom((1, 2, 3)).one() == 1  # rung: as above

    # `evalc` is the other direction: it names the space absolutely, where
    # `super` names the next definition along, relatively.
    assert m.eval(S.store(S.good)) == [S.stored(S.good)]
