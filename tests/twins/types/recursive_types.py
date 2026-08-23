"""Purpose: examples/types/recursive_types.metta in Python: one name, two arrows.

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

from petta import S, arrow, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Declare two arrows for one name, then ask four questions."""
    kind = m.fn.get_type
    sword = arrow(S.Metal, S.Sword)
    paperclip = arrow(S.Metal, S.Paperclip)

    m += typed(S.blacksmith, sword)
    m += typed(S.blacksmith, paperclip)
    m += typed(S.iron, S.Metal)
    m += typed(S.gold, S.Metal)

    assert m.type(S.iron) == S.Metal
    assert kind(S.blacksmith) == [sword, paperclip]
    assert kind(S.blacksmith(S.iron)) == [S.Sword, S.Paperclip]
    assert kind(S.iron(S.blacksmith)) == [S.Metal(sword), S.Metal(paperclip)]
