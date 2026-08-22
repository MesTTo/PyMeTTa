"""examples/spaces/selfprog.metta in Python: a program editing itself.

An equation is an ordinary atom, so a running program removes one and adds
another, and the same call answers differently either side of the edit: first
`(function1)` itself, unreduced, then `(OK)`.

Both edits go through the container protocol, which is the point made in
Python: `m -= equation(...).to(...)` is the removal and `m +=` the add, the
same two operators that move any other knowledge. The original reads its
answers through `repr` because MeTTa's `test` would reduce them; here the
answers are atoms and Python compares atoms, so no printing is involved.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4332 to 3214, -1118 (-25.8%), by the twin contract
#: change: two `(test (repr (function1)) "...")` terms became two `assert`s
#: comparing ATOMS, so the `test` and `repr` wrappers both left the engine and
#: what remains is one definition, two edits and two evaluations. Against the
#: example's 5593 the ratio is 0.5746.
#: Prior: 4332, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 3214


def twin(m):
    """Define a function, delete its equation, then give it another one."""

    @m.define
    def function1():
        # A capitalised free name in a compiled body is a data CONSTRUCTOR,
        # and MeTTa data has no Python value to bind.
        return OK  # noqa: F821

    m -= equation(S.function1()).to(S.OK)

    # With no equation left, the call is its own answer.
    assert m.one(S.function1()) == S.function1()

    m += equation(S.function1()).to(S.OK())

    assert m.one(S.function1()) == S.OK()
