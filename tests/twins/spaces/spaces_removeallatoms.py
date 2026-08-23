"""Purpose: examples/spaces/spaces_removeallatoms.metta in Python: emptying a space.

`remove-all-atoms` takes everything out, equations included, and the example's
sharpest claim is what that does to the function itself: it was imported INTO
this space, so the first call removes it, and the second call has no definition
left and answers itself. `(f 42)` goes the same way.

The removal is the engine's own function rather than `del space[pattern]`,
because the two are different operations: the pattern form removes what unifies
and leaves the space standing, while this one drains the store and takes the
imported definitions with it (residue, P14.10). PERFECT: `space.clear()`
answers one unit per removed atom, so the container spelling and the engine's
own agree on cardinality and the pair can be taught side by side the way `-=`
and `del kb[pattern]` are. Reading the aftermath is the
container door, `len(space)`.

`import!` is a directive with no Python door yet, so the library arrives
through the engine's own function, with the handle in the space position
(residue, P14.13). PERFECT: `m += lib.lib_spaces`, a library landing through
the one write door because a library IS knowledge. Its name keeps the underscore MeTTa gives it: `S.lib_spaces`
would be the atom `lib-spaces` and no such library exists.
"""

from petta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Fill a space, empty it, then see what is left to answer with."""
    m.fn["import!"](m, S.library(S["lib_spaces"])).one()

    m += (S.friend, S.tim, S.tom)

    @m.define
    def f(_x):
        return 42

    m.fn["remove-all-atoms"](m).one()

    # The function was imported into this space, so it left with everything
    # else: a second call has nothing to reduce it and answers itself.
    assert m.answers(S["remove-all-atoms"](m)).one() == S["remove-all-atoms"](m)
    assert m.answers(S.f(42)).one() == S.f(42)
    assert len(m) == 0
