"""examples/libraries/derived_forms.metta in Python: swapping a fused form for its expansion.

The engine fuses `once` into the compiler, and lib_derived writes the same form
as an ordinary MeTTa equation that rewrites the call into `(take 1 ...)`. This
file swaps one for the other in a live session and shows the answers do not
move, so `once` is the subject throughout and stays named.

`noisy` stays at the container door for two reasons, and the second is the
interesting one: its body calls `add-atom`, which a compiled body cannot spell,
and it NAMES a space, which is what an equation must do. An equation is data
that outlives the process, so the atom carries the space's name where Python
holds a handle.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 15603 to 13485, -2118 (-13.57%), by the idiomatic
#: rewrite: seven `test` wrappers and three `collapse`s left the engine for
#: `assert` and `.all()`; `once`, the library swap and the side-effecting
#: generator still run there. Measured min-of-three with the MORK backend
#: linked into this worktree, which the earlier figure may not have been.
#: Prior: 15603 was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 13485


def twin(m):
    """Answer with the compiler's `once`, then the library's, then the compiler's."""
    once = m.fn("once")

    # Before the import, `once` is the compiler's own clause.
    assert once(S.superpose((1, 2, 3))) == 1

    m.eval(S["import!"](S["&self"], S.library(S.lib_derived)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    # After it, `once` is an ordinary MeTTa equation, and it answers the same.
    assert once(S.superpose((1, 2, 3))) == 1
    assert once.all(S.superpose((1, 2, 3))) == [1]
    assert once.all(S.empty()) == []

    # It is still the FIRST answer of a generator with side effects, so the
    # rest of the generator does not run.
    seen = m.space("&seen")
    m += equation(S.noisy(V.x)).to(S.let(V._, S["add-atom"](S["&seen"], S.saw(V.x)), V.x))  # rung: an equation is DATA, so the space it writes to is carried by name; a Python handle is a process-local object and cannot be stored in an atom

    assert once(S.superpose((S.noisy(S.a), S.noisy(S.b)))) == S.a
    assert list(seen) == [S.saw(S.a)]

    # The swap is a session decision, not a per-call one: registering is
    # global, and removing puts the compiler's own clause back in charge.
    m.eval(S["remove-translator-rule!"](S.once))

    assert once(S.superpose((1, 2, 3))) == 1
