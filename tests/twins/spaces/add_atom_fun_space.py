"""Purpose: examples/spaces/add_atom_fun_space.metta in Python: the target is computed.

A function answers a SPACE NAME and the write lands in that space. Nothing has
to create it first: a name is a space the moment it is written to, and the `&`
prefix is what makes it a space name rather than an ordinary symbol.

The equation compiles. A compiled body reads the naming factories as syntax, so
`S["&my_space_name"]` is the bracket spelling of a name Python's grammar cannot
say, and the engine hands the answer back as a handle.

The write does NOT go through `space += atom`. That door takes a handle, and
this example's whole point is a target the program works out for itself, so the
write hands the engine's own `add-atom` the CALL `(space)`, unevaluated,
exactly where the original hands it (residue, P14.10). PERFECT: a write door
that takes a TERM to be resolved at the write. Reading the result is
the container door again: iterating the space the function named is
`for atom in space`.
"""

import petta
from petta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1


def twin(m):
    """Answer a space name from a function, then write into what it names."""
    target = petta.space("&my_space_name")

    # (= (space) &my_space_name)
    @m.define(name="space")
    def space_by_name():
        return S["&my_space_name"]  # rung: the example's whole subject is a bare space NAME answered by a function, which is the one place a name outranks a handle

    # !(add-atom (space) (my test atom)): the space argument is EVALUATED, so
    # the write goes where the function points rather than where a handle does.
    m.fn["add-atom"](S.space(), (S.my, S.test, S.atom)).one()  # rung: the write's target is a term, so `space += atom` has no handle to take

    assert list(target) == [S.my(S.test, S.atom)]
