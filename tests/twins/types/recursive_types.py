"""examples/types/recursive_types.metta in Python: one name, two arrows.

A blacksmith turns Metal into a Sword, and also into a Paperclip. Both arrows
are declared for the one name, so every question about the name answers twice,
and an application answers the results of both. Nothing here is a function
definition: there is no equation for `blacksmith` at all, only what its type
says, which is why the declarations are written as the facts they are.

The last claim is the one worth reading twice. `(iron blacksmith)` is not an
application, it is a two-element expression, so its type is the expression of
its parts' types, elementwise, and it answers once per arrow the second element
has.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4238 to 2011, -2227 (-52.55%), by the twin-shape
#: rewrite: four `test`-plus-`collapse` wrappers left the engine for `assert`
#: over `.all()`; the four declarations and the four questions are what
#: remains. Against the example's 8577 the ratio is 0.2345 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/recursive_types.metta`]. Prior: RE-PINNED at 4238 by
#: P14.8's m.eval fuel-scope alignment.
BUDGET = 2011


def twin(m):
    """Declare two arrows for one name, then ask four questions."""
    typed, arrow = S[":"], S["->"]
    kind = m.fn("get-type")
    sword = arrow(S.Metal, S.Sword)
    paperclip = arrow(S.Metal, S.Paperclip)

    m += typed(S.blacksmith, sword)
    m += typed(S.blacksmith, paperclip)
    m += typed(S.iron, S.Metal)
    m += typed(S.gold, S.Metal)

    assert m.fn("iron").type == S.Metal
    assert kind.all(S.blacksmith) == [sword, paperclip]
    assert kind.all(S.blacksmith(S.iron)) == [S.Sword, S.Paperclip]
    assert kind.all(S.iron(S.blacksmith)) == [S.Metal(sword), S.Metal(paperclip)]
