"""examples/functions/dispatch_policies.metta in Python: a dispatch override.

`(only-a A)` answers `hit`; `(only-a B)` matches no clause, and the catalogued
default leaves such a call UNREDUCED, so it answers itself. Adding
`(dispatch-policy only-a NoMatchEnum NoMatchFail)` to the reflection space
overrides that for this one function, so the call fails instead and answers
nothing; removing the override restores the default on the same call.

The override is an ordinary atom in an ordinary space, so setting it is `+=`
and clearing it is `-=`: the library steers from inside MeTTa rather than
through a Python knob, and `petta.reflection` is the handle for the space that
holds it.

One wall, measured here 2026-08-22 and filed as friction against P14.4:
`m.eval` DROPS the not-reducible answer that this example is about. For a
defined function whose clauses do not match, `!(pick 2)` answers `(pick 2)`
and `(collapse (pick 2))` holds one answer, while `m.eval(S.pick(2))` answers
`[]`, which is the other of the two nothings and makes the override
indistinguishable from the default. So the three claims are read through the
engine's own reducer, which does apply the policy.

The equation is written at the container door, one rung below the decorator,
because its head fixes a SYMBOL: `(only-a A)` matches the atom `A`. A stacked
`@m.define` clause fixes a head position with a literal default, and a literal
is a bool, int, float or str, never a symbol. The residue table records that
against P14.4 too.
"""

import petta
from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Read one call under the default policy, the override, and the default again."""
    only_a = S["only-a"]
    reduce = m.fn.reduce

    # (= (only-a A) hit)
    m += equation(only_a(S.A)).to(S.hit)  # rung: the head fixes a SYMBOL

    # The catalogued default: a call nothing matches answers itself.
    #
    # DEFECT, and the three claims below are the workaround. The perfect
    # spelling is the evaluation door,
    #
    #     assert m.eval(only_a(S.B)) == [only_a(S.B)]
    #
    # and it answers `[]`: for a DEFINED function whose clauses do not match,
    # `m.eval` drops the unreduced answer a runnable form keeps, so the
    # override and the default become indistinguishable in exactly the file
    # that is about telling them apart. `m.eval`'s own docstring says it is
    # "what !(...) runs, minus the printing". The engine's `reduce` does apply
    # the policy, so these read through it
    # [measured 2026-08-22, reproduced 2026-08-23; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    assert reduce(only_a(S.B)) == [only_a(S.B)]

    reflection = petta.reflection
    policy = S["dispatch-policy"](only_a, S.NoMatchEnum, S.NoMatchFail)

    reflection += policy
    assert reduce(only_a(S.B)) == []

    reflection -= policy
    assert reduce(only_a(S.B)) == [only_a(S.B)]
