"""examples/functions/dispatch_policies.metta in Python: a dispatch override.

`(only-a A)` answers `hit`; `(only-a B)` matches no clause, and the catalogued
default leaves such a call UNREDUCED, so it answers itself. Adding
`(dispatch-policy only-a NoMatchEnum NoMatchFail)` to the reflection space
overrides that for this one function, so the call fails instead and answers
nothing; removing the override restores the default on the same call.

The override is an ordinary atom in an ordinary space, so setting it is `+=`
and clearing it is `-=`: the library steers from inside MeTTa rather than
through a Python knob, and `metta.reflection` is the handle for the space that
holds it.

The three claims are read through `m.eval`, which keeps the not-reducible
answer this example is about: a call nothing matches answers itself under the
default, and answers nothing under the override, so the two nothings stay
apart.

The equation is written at the container door, one rung below the decorator,
because its head fixes a SYMBOL: `(only-a A)` matches the atom `A`. A stacked
`@m.define` clause fixes a head position with a literal default, and a literal
is a bool, int, float or str, never a symbol. The residue table records that
against P14.4 too.
"""

import metta
from metta import S, equation
from metta.vocabularies import NoMatchEnum

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Read one call under the default policy, the override, and the default again."""
    only_a = S.only_a

    # (= (only-a A) hit)
    m += equation(only_a(S.A)).to(S.hit)  # rung: the head fixes a SYMBOL

    # The catalogued default: a call nothing matches answers itself.
    assert m.eval(only_a(S.B)) == [only_a(S.B)]

    reflection = metta.reflection
    policy = S.dispatch_policy(S.only_a, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail])

    reflection += policy
    assert m.eval(only_a(S.B)) == []

    reflection -= policy
    assert m.eval(only_a(S.B)) == [only_a(S.B)]
