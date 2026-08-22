"""examples/spaces/restricted_spaces.metta in Python: a curated execution base.

A restricted space keeps ordinary computation and its own equations, refuses
anything its base does not publish, and gains a capability only when the
capability is granted at creation.

`m.new_space(restricted=True)` and `m.new_space(restricted=True, grants=...)`
are those two spaces, and neither needs a name: every door the example uses
hangs off the handle, and the named restricted form has no Python door
(residue, P14.10). The refusal is an exception carrying its own sentence,
which is the loud spelling the original reaches with `catch` and `if-error`.

`grants` takes the capability's NAME, and the name is written `S.file.name`
rather than as a bare string, because the lane reads a string constant as
possible MeTTa source and a capability name is not source (residue, P14.1).
"""

from petta import S, SpaceCapabilityError, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 46180 to 43389, -2791 (-6.0%), by the twin contract
#: change: three `(test ...)` terms became three Python `assert`s, so the
#: `test` wrapper left the engine three times and the middle form dropped its
#: `catch` and `if-error` with it, because a refused capability is an exception
#: at this door. The two space creations, the definition and both file
#: questions are unchanged. Against the example's 49813 the ratio is 0.8710.
#: Prior: 46180, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 43389

#: The file the example asks about: its own source, and ordinary path data.
HERE = val("examples/spaces/restricted_spaces.metta")


def twin(m):
    """Lock a space, watch it refuse a file read, then grant the capability."""
    locked = m.new_space(restricted=True)

    @locked.define
    def double(x):
        return x * 2

    # A restricted space retains ordinary computation and its own equations.
    assert locked.eval(S.double(21)) == [42]

    # The file operation reaches a refusal that names what is missing.
    refusal = None
    try:
        locked.eval(S.exists_file(HERE))
    except SpaceCapabilityError as error:
        refusal = error
    assert refusal is not None

    # A capability is granted explicitly when the space is created.
    reader = m.new_space(restricted=True, grants=[S.file.name])
    assert reader.eval(S.exists_file(HERE)) == [True]
