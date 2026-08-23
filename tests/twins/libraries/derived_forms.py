"""examples/libraries/derived_forms.metta in Python: swapping a fused form for its expansion.

The engine fuses `once` into the compiler, and lib_derived writes the same form
as an ordinary MeTTa equation that rewrites the call into `(take 1 ...)`. This
file swaps one for the other in a live session and shows the answers do not
move, so `once` is the subject throughout and stays named.

`noisy` stays at the container door because its body calls `add-atom`, which a
compiled body cannot spell. The space it writes to is the HANDLE, not a name: a
space crosses a term position as a grounded operand, so the equation carries the
handle the twin already holds.
"""

import metta
from metta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Answer with the compiler's `once`, then the library's, then the compiler's."""
    once = m.fn.once

    # Before the import, `once` is the compiler's own clause.
    assert once(S.superpose((1, 2, 3))) == [1]

    m.fn["import!"](m, S.library(S["lib_derived"]))

    # After it, `once` is an ordinary MeTTa equation, and it answers the same.
    assert once(S.superpose((1, 2, 3))) == [1]
    assert list(once(S.superpose((1, 2, 3)))) == [1]
    assert list(once(S.empty())) == []

    # It is still the FIRST answer of a generator with side effects, so the
    # rest of the generator does not run.
    seen = metta.space("&seen")
    m += equation(S.noisy(V.x)).to(S.let(V._, S["add-atom"](seen, S.saw(V.x)), V.x))  # rung: this is the equation's stored BODY, and `space += atom` and assignment are Python statements, which an atom cannot hold

    assert once(S.superpose((S.noisy(S.a), S.noisy(S.b)))) == [S.a]
    assert list(seen) == [S.saw(S.a)]

    # The swap is a session decision, not a per-call one: registering is
    # global, and removing puts the compiler's own clause back in charge.
    m.fn.remove_translator_rule(S.once)

    assert once(S.superpose((1, 2, 3))) == [1]
