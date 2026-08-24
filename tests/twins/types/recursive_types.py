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

from metta import S, arrow, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
BUDGET = 1


def twin(m):
    """Declare two arrows for one name, then ask four questions."""
    kind = m.fn.get_type
    sword = arrow(S.Metal, S.Sword)
    paperclip = arrow(S.Metal, S.Paperclip)

    # (: blacksmith (-> Metal Sword)) (: blacksmith (-> Metal Paperclip))
    # (: iron Metal) (: gold Metal)
    m += typed(S.blacksmith, sword)
    m += typed(S.blacksmith, paperclip)
    m += typed(S.iron, S.Metal)
    m += typed(S.gold, S.Metal)

    # !(test (get-type iron) Metal)
    assert m.type(S.iron) == S.Metal
    # !(test (collapse (get-type blacksmith))
    #        ((-> Metal Sword) (-> Metal Paperclip)))
    assert kind(S.blacksmith) == [sword, paperclip]
    # !(test (collapse (get-type (blacksmith iron))) (Sword Paperclip))
    assert kind(S.blacksmith(S.iron)) == [S.Sword, S.Paperclip]
    # !(test (collapse (get-type (iron blacksmith)))
    #        ((Metal (-> Metal Sword)) (Metal (-> Metal Paperclip))))
    assert kind(S.iron(S.blacksmith)) == [S.Metal(sword), S.Metal(paperclip)]
