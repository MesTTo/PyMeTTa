"""Purpose: examples/spaces/spaces_removeallatoms.metta in Python: emptying a space.

`remove-all-atoms` takes everything out, equations included, and the example's
sharpest claim is what that does to the function itself: it was imported INTO
this space, so the first call removes it, and the second call has no definition
left and answers itself. `(f 42)` goes the same way.

The removal is the engine's own function rather than `space.clear()`, because
the two are different operations: `clear()` empties the same space through the
same funnel but answers NOTHING, where `(remove-all-atoms &self)` answers ONE
UNIT PER REMOVED ATOM, and the example's own claim is about that answer
(residue, P14.10). PERFECT: a container spelling that agrees with the engine's
own on cardinality, so the pair can be taught side by side the way `-=` and
`del kb[pattern]` are. Reading the aftermath is the container door, `len(space)`.

`import!` is a directive with no Python door yet, so the library arrives
through the engine's own function, with the handle in the space position
(residue, P14.13). PERFECT: `m += lib.lib_spaces`, a library landing through
the one write door because a library IS knowledge. Its name keeps the
underscore MeTTa gives it, at both doors: `S.lib_spaces` would be the atom
`lib-spaces` and `fn.import_` would be `import-`, so each takes the bracket
that spells the name exactly.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Fill a space, empty it, then see what is left to answer with."""
    m.fn["import!"](m, S.library(S["lib_spaces"])).one()  # rung: import! is a directive, and no Python door claims it

    m += (S.friend, S.tim, S.tom)

    @m.define
    def f(_x):
        return 42

    m.fn.remove_all_atoms(m).one()  # rung: clear() empties the same space and answers nothing, where this answers one unit per atom

    # The function was imported into this space, so it left with everything
    # else: a second call has nothing to reduce it and answers itself.
    assert m.answers(S.remove_all_atoms(m)).one() == S.remove_all_atoms(m)
    assert m.answers(S.f(42)).one() == S.f(42)
    assert len(m) == 0
