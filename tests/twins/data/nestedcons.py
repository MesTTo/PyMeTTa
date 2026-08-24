"""examples/data/nestedcons.metta in Python: two cons cells in one pattern.

`(cons $a (cons $b $L))` takes an expression apart twice over and answers the
second element. Python's `match` says the same thing with a nested sequence
pattern, and `_` is MeTTa's own anonymous variable, so the two positions the
clause does not use are marked as unused rather than named and dropped.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
BUDGET = 1


def twin(m):
    """Define the doubly-nested clause and take the second element with it."""

    @m.define
    def f(cell):                              # (= (f (cons $a (cons $b $L)))
        match cell:                           #    $b)
            case (S.cons, _, (S.cons, b, _)):
                return b

    assert f(S.a(S.b, S.c, S.d)).one() == S.b   # [b]
