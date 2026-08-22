"""examples/integration/import_space_identity.metta in Python: one identity per space.

Two spaces import the same file. Each gets its own copy of what the file
defines, exactly once, and the space that did the importing gets nothing: in
`&self` the imported name stays data, an unreduced term answering itself.

`bind!` and `new-space` are a Python name binding, which is what a token was
for. Everything the claims ask goes through the space handle: `space[pattern]`
matches it and `space.eval(term)` evaluates in it, which is what the example
spells `(metta term %Undefined% &space)`. Only `import!` still needs the space
NAMED, because no import door hangs off the handle; that is the residue, and
the handles are built from the atoms so the name is written once.
"""

from petta import S

#: The two importing spaces, and the file they both import.
A, B = S["&import-space-a"], S["&import-space-b"]  # rung: import! has no handle door, so it takes the space as a symbol
PAYLOAD = S["examples/integration/_fixtures/imports/overhaul/space_payload"]

#: What the payload puts in an importing space, and what it defines there.
MARKER = S["import-space-marker"]()
FUNCTION = S["import-space-function"]()

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9672 to 5390, -4282 (-44.3%), by the twin contract
#: change: five `test` wrappers, five `collapse` calls, two `bind!`/`new-space`
#: forms and four `match`/`metta` forms left the engine for `assert`, `len()`,
#: a Python name binding and the space handle's own `[...]` and `.eval`. The
#: two imports did not move. Against the example's 16442 the ratio is 0.3278
#: [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/integration/import_space_identity.metta`]. Prior: ADDED 2026-08-22
#: at 9672 by the wave-3 twin baseline, which priced a transliteration.
BUDGET = 5390


def twin(m):
    """Import one payload into two spaces, and ask all three what they hold."""
    a, b = m.space(A.name), m.space(B.name)
    for space in (A, B):
        m.eval(S["import!"](space, PAYLOAD))

    # Each importing space holds the marker, once.
    assert len(a[MARKER]) == 1
    assert len(b[MARKER]) == 1

    # And each ran its own copy of the definition, once.
    assert a.eval(FUNCTION) == [S["one-result"]]
    assert b.eval(FUNCTION) == [S["one-result"]]

    # The caller imported nothing, so here the name is still data.
    assert m.eval(FUNCTION) == [FUNCTION]
