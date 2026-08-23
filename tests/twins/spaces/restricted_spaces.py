"""Purpose: examples/spaces/restricted_spaces.metta in Python: a curated execution base.

A restricted space keeps ordinary computation and its own equations, refuses
anything its base does not publish, and gains a capability only when the
capability is granted at creation.

`petta.space(restricted=True)` and `petta.space(restricted=True, grants=...)`
are those two spaces, and neither has a name: the creation options apply only
to an anonymous space, and every door the example uses hangs off the handle
they answer.

Two gaps are visible in the code below and both are commented where they bite:
the named restricted space the original writes has no Python door, and a
capability is granted as text where the surface rules an enum.
"""

from pathlib import Path

import petta
from petta import S, ground
from petta.errors import SpaceCapabilityError

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1

#: The file the example asks about: a path, which is what pathlib is for.
SOURCE = Path("examples/spaces/restricted_spaces.metta")


def twin(m):  # noqa: ARG001  -- both spaces are created here; the default handle stays untouched
    """Lock a space, watch it refuse a file read, then grant the capability."""
    # GAP: the original NAMES its spaces, `!(new-space &locked (restricted))`,
    # and the answer of that form IS the name it created. petta.space refuses
    # the pair: "inherits, restricted, and grants apply only to anonymous
    # space()". PERFECT: `locked = petta.space("&locked", restricted=True)`.
    # Residue P14.10; until it lands the handle carries every door instead.
    locked = petta.space(restricted=True)

    @locked.define
    def double(x):
        return x * 2

    # A restricted space retains ordinary computation and its own equations.
    assert locked.eval(S.double(21)) == [42]

    # GAP: a path crosses as text rather than as a path. `ground(Path(...))`
    # reaches the engine as an opaque box and `exists_file` refuses it,
    # "cannot write <py_Box> as MeTTa text" [measured 2026-08-23]. PERFECT:
    # `S["exists_file"](SOURCE)`, with a Path codec doing the conversion the
    # str() below does by hand.
    asked = S["exists_file"](ground(str(SOURCE)))

    # The file operation reaches a refusal that names what is missing.
    refusal = None
    try:
        locked.eval(asked)
    except SpaceCapabilityError as error:
        refusal = error
    assert refusal is not None

    # A capability is granted explicitly when the space is created.
    # GAP: the capability arrives as text. petta.vocabularies.SpaceCapability
    # is a Literal type, so mypy checks the word and nothing autocompletes it
    # or renames with it. PERFECT: `grants=[SpaceCapability.FILE]`, the enum
    # the surface rules for every option value.
    reader = petta.space(restricted=True, grants=["file"])
    assert reader.eval(asked) == [True]
