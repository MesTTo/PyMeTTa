"""examples/data/constanthead.metta in Python: selecting on a structure.

`h` answers only when its first argument IS `(justdata haha $B)`, and the `$B`
it binds out of the middle of that structure is what it adds. Selecting on a
structure is Python's `match` statement, which lowers to MeTTa's own `case`
tower, so the clause reads as the algorithm it is rather than as an equation
built by hand.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
BUDGET = 1


def twin(m):
    """Define the structural clause, then feed it the structure it wants."""

    @m.define
    def h(data, c):                       # (= (h (justdata haha $B) $C)
        match data:                       #    (+ $B $C))
            case (S.justdata, S.haha, b):
                return b + c

    assert h(S.justdata(S.haha, 30), 40).one() == 70   # [70]
