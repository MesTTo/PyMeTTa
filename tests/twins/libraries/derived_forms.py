"""examples/libraries/derived_forms.metta in Python: swapping a fused form for its expansion.

The engine fuses `once` into the compiler, and lib_derived writes the same form
as an ordinary MeTTa equation that rewrites the call into `(take 1 ...)`. This
file swaps one for the other in a live session and shows the answers do not
move, so `once` is the subject throughout and stays named.

`noisy` is an ordinary compiled definition, and both halves of its body have a
spelling now. The write is `fn.add_atom(seen, S.saw(x))`: the STATIC namespace
is what a compiled body reads for a hyphenated engine function, and the space
it writes to is the HANDLE, encoded into the equation at decoration time, so no
space is ever named as a symbol. Binding that call to `_` and answering `x` is
Python's own way of saying `(let $_ <effect> $x)`, which is the sequencing the
example writes; `seen += S.saw(x)` is the write door everywhere else and a
compiled body refuses it, because `+=` on a host object would close over this
process.
"""

import metta
from metta import S, fn

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
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
    seen = metta.space(S.seen)

    @m.define
    def noisy(x):
        # (= (noisy $x) (let $_ (add-atom &seen (saw $x)) $x))
        _ = fn.add_atom(seen, S.saw(x))
        return x

    assert once(S.superpose((S.noisy(S.a), S.noisy(S.b)))) == [S.a]
    assert list(seen) == [S.saw(S.a)]

    # The swap is a session decision, not a per-call one: registering is
    # global, and removing puts the compiler's own clause back in charge.
    m.fn.remove_translator_rule(S.once)

    assert once(S.superpose((1, 2, 3))) == [1]
