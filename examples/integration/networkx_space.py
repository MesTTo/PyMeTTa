"""Purpose: the metagraph reading made executable on the public surface
alone: a space's expressions viewed as a networkx graph, an nx algorithm
answering a question the space cannot, and the answer written back as
atoms. Nothing here is library machinery, and that is the demonstration:
match for the edge shape, enumeration, and the bulk write door are
enough, so the same to_graph call runs unchanged against native atoms,
the SQL bridge, or an attached remote space, because they are all the
one seam.

An n-ary expression has no default graph reading, so the projection is
the caller's to name: an arity-2 shape is an edge per atom, and a wider
shape needs projection="pairwise" (consecutive argument pairs) or
"bipartite" (the expression itself becomes a node linked to each
argument, the hypergraph-faithful reading). Anything else is refused
rather than guessed.
[tested: bindings/python/tests/test_networkx_space.py]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sqlite3
from itertools import pairwise

from _common import check, done, skip

try:
    import networkx as nx
except ImportError:
    skip("networkx is not installed")

from metta import Expression, MeTTa, Variable, parse, tables, ground

_PROJECTIONS = ("pairwise", "bipartite")


def to_graph(space, shape, *, projection: str | None = None) -> nx.DiGraph:
    """The atoms matching `shape`, as a directed graph of atom nodes.

    `shape` is a pattern whose head names the link and whose argument
    slots become graph structure: `(edge $a $b)` reads each answer as
    one a->b edge. A wider shape must name its projection, because an
    n-ary link has no single graph reading.
    """
    pattern = parse(shape) if isinstance(shape, str) else shape
    if not isinstance(pattern, Expression) or len(pattern.children) < 3:
        raise ValueError(
            f"a graph shape is a link expression with at least two argument "
            f"slots, as in (edge $a $b); got {pattern}"
        )
    arity = len(pattern.children) - 1
    if arity == 2 and projection is None:
        projection = "pairwise"  # two slots: both projections agree
    if projection not in _PROJECTIONS:
        raise ValueError(
            f"an arity-{arity} shape has no default graph reading; pass "
            f"projection= one of {_PROJECTIONS!r}"
        )
    graph = nx.DiGraph()
    columns = [c.name for c in pattern.children[1:] if isinstance(c, Variable)]
    for row in space.match(pattern):
        arguments = [row[name] for name in columns]
        if projection == "pairwise":
            graph.add_edges_from(pairwise(arguments))
        else:
            link = Expression(pattern.children[:1] + tuple(arguments))
            graph.add_edges_from((link, argument) for argument in arguments)
    return graph


def main() -> None:
    m = MeTTa().self
    m.run("(edge a b) (edge b c) (edge c d) (edge a d)")

    # The space as a graph: atoms are the nodes, matches are the edges.
    graph = to_graph(m, "(edge $x $y)")
    check("every stored link is an edge", graph.number_of_edges(), 4)

    # An nx algorithm answers what no match can ask: the SHORTEST route.
    route = nx.shortest_path(graph, parse("a"), parse("d"))
    check("networkx answers the shortest path", [str(n) for n in route], ["a", "d"])

    # And the answer goes back to being knowledge, through the bulk door.
    scores = nx.degree_centrality(graph)
    m.add(*(Expression((parse("central"), node, ground(round(score, 3))))
            for node, score in scores.items()))
    (group,) = m.run("!(collapse (match &self (central a $s) $s))")
    check("centrality written back is queryable", len(list(group[0])), 1)

    # The same call against the SQL bridge, unchanged: the seam is one.
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE nxedges (a TEXT, b TEXT)")
    connection.executemany(
        "INSERT INTO nxedges VALUES (?, ?)", [("p", "q"), ("q", "r")]
    )
    tables.declare(m, "&nxdb", "(bridge (edge $a $b) (row nxedges (a $a) (b $b)))")
    m._register_space(tables.TableBridge.from_context(m, "&nxdb", connection), "&nxdb")
    bridged = to_graph(m._at("&nxdb"), "(edge $x $y)")
    check("SQL rows graph identically", sorted(str(n) for n in bridged), ["p", "q", "r"])

    # A wider link refuses to guess its reading, then takes either one.
    m.run("(triple s v o)")
    try:
        to_graph(m, "(triple $s $v $o)")
        raise AssertionError("an arity-3 shape must not default")
    except ValueError as error:
        check("no default reading for arity 3", "projection=" in str(error), True)
    chain = to_graph(m, "(triple $s $v $o)", projection="pairwise")
    check("pairwise walks the arguments", chain.number_of_edges(), 2)
    stars = to_graph(m, "(triple $s $v $o)", projection="bipartite")
    check("bipartite keeps the link as a node", stars.number_of_edges(), 3)
    check(
        "the hypergraph reading survives: the link node IS the expression",
        any(isinstance(node, Expression) for node in stars),
        True,
    )
    done("networkx_space")


if __name__ == "__main__":
    main()
