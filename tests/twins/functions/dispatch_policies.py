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
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 1820 to 1877, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 1877 to 1859, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 1859 to 1837, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 1837 to 1845, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 1845


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
