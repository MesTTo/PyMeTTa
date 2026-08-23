"""examples/integration/import_space_identity.metta in Python: one identity per space.

Two spaces import the same file. Each gets its own copy of what the file
defines, exactly once, and the space that did the importing gets nothing: in
its own space the imported name stays data, an unreduced term answering itself.

`(bind! &import-space-a (new-space))` is `metta.space(name)` plus a Python name
binding, which is what a token was for, and the name is an ATOM rather than
text: `metta.space` takes one, and the ampersand belongs to the door rather
than to the author. Everything the claims ask goes through the handle:
`space[pattern]` matches it and `space.eval(term)` evaluates in it, which is
what the example spells `(metta term %Undefined% &space)`.
"""

import metta
from metta import S

#: The file both spaces import, from the repository root: a Python program has
#: no importing file to resolve a relative import against.
PAYLOAD = S["examples/integration/_fixtures/imports/overhaul/space_payload"]

#: What the payload puts in an importing space, and what it defines there.
MARKER = S["import-space-marker"]()
FUNCTION = S["import-space-function"]()

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Import one payload into two spaces, and ask all three what they hold."""
    # Known issue: `metta.space(name)` is the one space-creation door, and it
    # rides the process-DEFAULT context rather than the one holding `m`. The
    # two reach the same store only because the SWI runtime is process-wide,
    # so the perfect spelling for a twin handed its own handle is a creation
    # door ON that handle's context. `MeTTa.space` is that door one level up
    # and a twin never sees the runtime object [measured 2026-08-24].
    a = metta.space(S["import-space-a"])       # (bind! &import-space-a (new-space))
    b = metta.space(S["import-space-b"])       # (bind! &import-space-b (new-space))

    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    for space in (a, b):
        m.fn["import!"](space, PAYLOAD)

    # Each importing space holds the marker, once.
    assert len(a[MARKER]) == 1
    assert len(b[MARKER]) == 1

    # And each ran its own copy of the definition, once.
    assert a.eval(FUNCTION) == [S["one-result"]]   # (metta (import-space-function) %Undefined% &import-space-a)
    assert b.eval(FUNCTION) == [S["one-result"]]

    # The caller imported nothing, so here the name is still data.
    assert m.eval(FUNCTION) == [FUNCTION]
