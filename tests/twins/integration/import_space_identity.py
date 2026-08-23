"""examples/integration/import_space_identity.metta in Python: one identity per space.

Two spaces import the same file. Each gets its own copy of what the file
defines, exactly once, and the space that did the importing gets nothing: in
`&self` the imported name stays data, an unreduced term answering itself.

`bind! (new-space)` is `petta.space(name)` plus a Python name binding, which is
what a token was for. Everything the claims ask goes through the handle:
`space[pattern]` matches it and `space.eval(term)` evaluates in it, which is
what the example spells `(metta term %Undefined% &space)`. `import!` takes the
handle too, as a grounded operand, so no space here is named as a symbol; what
stays below the top rung is that `import!` has no Python door of its own.
"""

import petta
from petta import S

#: The file both spaces import, from the repository root: a Python program has
#: no importing file to resolve a relative import against.
PAYLOAD = S["examples/integration/_fixtures/imports/overhaul/space_payload"]

#: What the payload puts in an importing space, and what it defines there.
MARKER = S["import-space-marker"]()
FUNCTION = S["import-space-function"]()

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Import one payload into two spaces, and ask all three what they hold."""
    # Known issue: `petta.space(name)` is the one space-creation door, and it
    # rides the process-DEFAULT context rather than the one holding `m`. The
    # two reach the same store only because the SWI runtime is process-wide,
    # so the perfect spelling for a twin handed its own handle is a creation
    # door ON that handle's context [measured 2026-08-23: petta.engine() is
    # not the twin's MeTTa object, and their runtimes are the same object].
    a, b = petta.space("&import-space-a"), petta.space("&import-space-b")
    # Known issue, two halves. `import!` has no Python door on the handle: the
    # perfect spelling is `m.import_(target)`, or `m += lib.<name>` for a
    # shipped library (appendix stamp 1), and neither exists yet. And the
    # generic call door cannot stand in for it, because a call through the
    # function namespace answers a LAZY view: `m.fn["import!"](m, target)` as a
    # statement IMPORTS NOTHING until something pulls its answers [measured
    # 2026-08-23]. The term door evaluates eagerly, so the directive is written
    # that way.
    for space in (a, b):
        m.eval(S["import!"](space, PAYLOAD))

    # Each importing space holds the marker, once.
    assert len(a[MARKER]) == 1
    assert len(b[MARKER]) == 1

    # And each ran its own copy of the definition, once.
    assert a.eval(FUNCTION) == [S["one-result"]]
    assert b.eval(FUNCTION) == [S["one-result"]]

    # The caller imported nothing, so here the name is still data.
    assert m.eval(FUNCTION) == [FUNCTION]
