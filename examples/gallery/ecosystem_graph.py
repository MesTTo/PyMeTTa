"""Purpose: express a NetworkX shortest-path algorithm as one MeTTa operation.

Assumes:
  - NetworkX is present. It is not a dependency of the library, so this
    program skips where it is absent, the way every other integration
    example does.
  - the selected graph has one unique shortest path, so no library tie
    ordering can affect the shown answer.
Guarantees:
  - stored edge atoms project through the common space seam, NetworkX computes
    the route, and that route returns to the same space as queryable knowledge
    [tested: test_a_gallery_program_runs; commit=WORKTREE]
Owns resources: one named space and one read-only operation registration;
  unregister_op() and drop() release them after the result is written back,
  while process exit releases them after an earlier failed claim.
"""

from _common import claim, doctest, done, skip

try:
    import networkx as nx
except ImportError:
    skip("networkx is not installed")

from integration.networkx_space import to_graph

from metta import MeTTa, S, V


def hop_count(nodes: int) -> int:
    """Count edges in a nonempty path by its node count.

    >>> !(hop-count 4)
    [3]
    """
    return nodes - 1


engine = MeTTa()
space = engine.space("&gallery-ecosystem")
hops = space.define(hop_count)
doctest("path length doctest", hops)

claim(
    "store graph",
    S.progn(
        S.add_atom(space, S.edge(S.a, S.b)),
        S.add_atom(space, S.edge(S.b, S.c)),
        S.add_atom(space, S.edge(S.c, S.d)),
        S.add_atom(space, S.edge(S.a, S.e)),
        S.add_atom(space, S.edge(S.e, S.f)),
        S.add_atom(space, S.edge(S.f, S.g)),
        S.add_atom(space, S.edge(S.g, S.d)),
    ),
    space.eval,
)
# -> (progn (add-atom &gallery-ecosystem (edge a b)) (add-atom &gallery-ecosystem (edge b c)) (add-atom &gallery-ecosystem (edge c d)) (add-atom &gallery-ecosystem (edge a e)) (add-atom &gallery-ecosystem (edge e f)) (add-atom &gallery-ecosystem (edge f g)) (add-atom &gallery-ecosystem (edge g d)))
# => ()


@space.op(effect="readOnlyLookup")
def ecosystem_shortest_path(source, target):
    """Project edge atoms, run NetworkX, and return one structural path."""
    graph = to_graph(space, S.edge(V.start, V.end))
    return S.Path(*nx.shortest_path(graph, source, target))


path = claim(
    "ecosystem shortest path",
    S.ecosystem_shortest_path(S.a, S.d),
    space.eval,
)[0]
# -> (ecosystem-shortest-path a d)
# => (Path a b c d)
claim("write result back", S.add_atom(space, path), space.eval)
# -> (add-atom &gallery-ecosystem (Path a b c d))
# => ()
claim(
    "result is queryable knowledge",
    S.match(
        space,
        S.Path(V.start, V.middle_1, V.middle_2, V.end),
        S.Path(V.start, V.middle_1, V.middle_2, V.end),
    ),
    space.eval,
)
# -> (match &gallery-ecosystem (Path $start $middle-1 $middle-2 $end) (Path $start $middle-1 $middle-2 $end))
# => (Path a b c d)

space.unregister_op("ecosystem-shortest-path")
space.drop()
done("ecosystem_graph")
