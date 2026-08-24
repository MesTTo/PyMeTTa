"""Purpose: examples/spaces/selfprog.metta in Python: a program editing itself.

An equation is an ordinary atom, so a running program removes one and adds
another, and the same call answers differently either side of the edit: first
`(function1)` itself, unreduced, then `(OK)`.

Both edits go through the container protocol, which is the point made in
Python: `m -= equation(...).to(...)` is the removal and `m +=` the add, the
same two operators that move any other knowledge. The original reads its
answers through `repr` because MeTTa's `test` would reduce them; here the
answers are atoms and Python compares atoms, so no printing is involved.

The definition's body says `S.OK`, the naming factory, which a compiled body
reads as syntax and lowers to the constructor atom. The earlier spelling was a
bare `OK` with an `F821` suppression under it, because the name had no Python
value; the mention door removed both the suppression and the reason for it.
"""

from metta import S, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1


def twin(m):
    """Define a function, delete its equation, then give it another one."""

    @m.define
    def function1():
        return S.OK

    m -= equation(S.function1()).to(S.OK)

    # With no equation left, the call is its own answer.
    assert function1() == [S.function1()]

    m += equation(S.function1()).to(S.OK())

    assert function1() == [S.OK()]
