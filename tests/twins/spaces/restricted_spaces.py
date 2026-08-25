"""Purpose: examples/spaces/restricted_spaces.metta in Python: a curated execution base.

A restricted space keeps ordinary computation and its own equations, refuses
anything its base does not publish, and gains a capability only when the
capability is granted at creation.

`metta.space(restricted=True)` and `metta.space(restricted=True, grants=...)`
are those two spaces, and neither has a name: the creation options apply only
to an anonymous space, and every door the example uses hangs off the handle
they answer.

A path crosses as the `pathlib.Path` it is and a capability as the vocabulary
value it is, so neither is quoted into text. One gap remains, commented where
it bites: the named restricted space the original writes has no Python door.
"""

from pathlib import Path

import metta
from metta import S
from metta.errors import SpaceCapabilityError
from metta.vocabularies import SpaceCapability

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 52818 to 52949, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 52949 to 52946, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 52946 to 53023, on the release tree:
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
BUDGET = 53023

#: The file the example asks about: a path, which is what pathlib is for.
SOURCE = Path("examples/spaces/restricted_spaces.metta")


def twin(m):  # noqa: ARG001  -- both spaces are created here; the default handle stays untouched
    """Lock a space, watch it refuse a file read, then grant the capability."""
    # GAP: the original NAMES its spaces, `!(new-space &locked (restricted))`,
    # and the answer of that form IS the name it created. metta.space refuses
    # the pair: "inherits, restricted, and grants apply only to anonymous
    # space()" [measured 2026-08-24, unchanged; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT:
    # `locked = metta.space(S.locked, restricted=True)`. Residue P14.10;
    # until it lands the handle carries every door instead.
    locked = metta.space(restricted=True)

    @locked.define
    def double(x):
        return x * 2

    # A restricted space retains ordinary computation and its own equations.
    assert locked.eval(S.double(21)) == [42]

    # A path crosses the call door as the atom its codec makes of it, so
    # nothing quotes it into a string first.
    asked = S["exists_file"](SOURCE)

    # The file operation reaches a refusal that names what is missing.
    refusal = None
    try:
        locked.eval(asked)
    except SpaceCapabilityError as error:
        refusal = error
    assert refusal is not None

    # A capability is granted explicitly when the space is created, as the
    # vocabulary's own value rather than as the word for it.
    reader = metta.space(restricted=True, grants=[SpaceCapability.file])
    assert reader.eval(asked) == [True]
