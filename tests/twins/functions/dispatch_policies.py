"""examples/functions/dispatch_policies.metta in Python: a dispatch override.

`(only-a A)` answers `hit`; `(only-a B)` matches no clause, and the catalogued
default leaves such a call UNREDUCED, so it answers itself. Adding
`(dispatch-policy only-a NoMatchEnum NoMatchFail)` to the reflection space
overrides that for this one function, so the call fails instead and answers
nothing; removing the override restores the default on the same call.

The override is an ordinary atom in an ordinary space, so setting it is `+=`
and clearing it is `-=`: the library steers from inside MeTTa rather than
through a Python knob, and the space handle carries both.

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

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4594 to 2319, -2275 (-49.5%), by the twin contract
#: change: three `test` wrappers and one `collapse` left the engine for
#: `assert`, and both `add-atom`/`remove-atom` forms became `+=` and `-=`
#: on the reflection space handle; the three claims are read through
#: `m.fn("reduce")` because `m.eval` drops the not-reducible answer this
#: example is about. Against the example's 8165 the ratio is 0.2840
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 2319


def twin(m):
    """Read one call under the default policy, the override, and the default again."""
    only_a = S["only-a"]
    reduce = m.fn("reduce")

    # (= (only-a A) hit)
    m += equation(only_a(S.A)).to(S.hit)  # rung: the head fixes a SYMBOL

    # The catalogued default: a call nothing matches answers itself.
    assert reduce.all(only_a(S.B)) == [only_a(S.B)]

    reflection = m.space("&petta")
    policy = S["dispatch-policy"](only_a, S.NoMatchEnum, S.NoMatchFail)

    reflection += policy
    assert reduce.all(only_a(S.B)) == []

    reflection -= policy
    assert reduce.all(only_a(S.B)) == [only_a(S.B)]
