"""Purpose: examples/spaces/add_atom_fun_space.metta in Python: the target is computed.

A function answers a SPACE, and the write lands wherever it answered. Nothing
has to create that space first: a name is a space the moment it is written to.

The equation compiles, and it answers the HANDLE. A compiled body reads a
Python name bound to a space as the grounded atom a handle already is, so
`return target` stores `(= (space) &my_space_name)` with no symbol spelling of
a space anywhere in the file
[measured 2026-08-24: a `@m.define`d body returning a handle stores the space
operand itself; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].

The write does NOT go through `space += atom`. That door takes a handle in
hand, and this example's whole subject is a target the program works out for
itself, so the write hands the engine's own `add-atom` the CALL `(space)`,
unevaluated, exactly where the original hands it (residue, P14.10). PERFECT: a
write door that takes a TERM to be resolved at the write. Reading the result is
the container door again: iterating the space the function named is
`for atom in space`.
"""

import metta
from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1


def twin(m):
    """Answer a space from a function, then write into what it answered."""
    target = metta.space(S["my_space_name"])  # rung: the source name contains literal underscores

    # (= (space) &my_space_name)
    @m.define
    def space():
        return target

    # !(add-atom (space) (my test atom)): the space argument is EVALUATED, so
    # the write goes where the function points rather than where a handle does.
    m.fn.add_atom(S.space(), (S.my, S.test, S.atom)).one()  # rung: the write's target is a term, so `space += atom` has no handle to take

    assert list(target) == [S.my(S.test, S.atom)]
