"""Purpose: directed graphs as expressions, from Python.

A graph is a tuple of (Vertex Neighbours) pairs, so the example's two `bind!`
forms are ordinary Python names holding what `graph-of` answered. Where the
example NESTS one call inside another it is written here as the built call it is,
`S.graph_transpose(tasks)` rather than `transpose(tasks).one()`: draining the
inner answer would copy a whole graph into the host and pass it back, which is
the crossing the three-lane model prices per value. `rows` reads a graph or an
edge relation as a list of tuples, which is how a (Vertex Neighbours) pair and a
(From To) edge both read.

Guarantees: the same claims as 25-graph_lib.metta, including reconstructed and
specialized graph recipes and variable-sharing graphs.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/25-graph_lib.metta; commit=WORKTREE].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, lib
from metta._errors.errors import MettaError


def twin(m):
    """Build, ask, add, remove, transpose, unite, close, reach and order."""
    m += lib.graph

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def elements(answers):
        """One answer's expression, as a list."""
        return list(answers.one())

    def rows(answers):
        """One answer's expression of pairs, as a list of tuples."""
        return [tuple(row) for row in answers.one()]

    def graph_rows(value):
        """A graph as (vertex, [neighbours]) tuples, whatever holds it."""
        return [(row[0], list(row[1])) for row in value]

    graph_of, is_graph = m.fn.graph_of, m.fn.graph_is
    vertices, edges, neighbours = m.fn.graph_vertices, m.fn.graph_edges, m.fn.graph_neighbours
    add_vertices, remove_vertices = m.fn.graph_add_vertices, m.fn.graph_remove_vertices
    add_edges, remove_edges = m.fn.graph_add_edges, m.fn.graph_remove_edges
    reachable, order, acyclic = m.fn.graph_reachable, m.fn.graph_topological_order, m.fn.graph_is_acyclic

    # A graph is built from its edges, each written (From To). Every vertex an
    # edge mentions is a vertex; the first argument adds the ISOLATED ones, and
    # the answer is a collection of (Vertex Neighbours) pairs in the standard
    # order of terms.
    tasks = graph_of((S.lunch,), ((S.wake, S.shower), (S.shower, S.dress), (S.wake, S.coffee))).one()
    assert graph_rows(tasks) == [
        (S.coffee, []),
        (S.dress, []),
        (S.lunch, []),
        (S.shower, [S.dress]),
        (S.wake, [S.coffee, S.shower]),
    ]
    assert elements(graph_of((), ())) == []
    assert graph_rows(graph_of((S.a,), ()).one()) == [(S.a, [])]

    # graph-is asks whether a value is in that shape, which includes the
    # condition a hand-written graph most often misses: every neighbour is itself
    # a vertex.
    assert is_graph(tasks) == [True]
    assert is_graph(((S.a, (S.b,)),)) == [False]
    assert is_graph(((S.b, ()), (S.a, (S.b,)))) == [False]
    assert is_graph(((S.a, ()), (S.b, ()))) == [True]
    assert is_graph(7) == [False]

    # The vertices are a SET, so lib_sets asks about them, and the edges are a
    # RELATION, so lib_pairs walks them.
    assert elements(vertices(tasks)) == [S.coffee, S.dress, S.lunch, S.shower, S.wake]
    assert rows(edges(tasks)) == [(S.shower, S.dress), (S.wake, S.coffee), (S.wake, S.shower)]
    assert elements(edges(S.graph_of((), ()))) == []

    # The neighbours of a vertex are what it points at. A vertex the graph does
    # not hold is a refusal naming it, not an empty answer that would read as a
    # sink.
    assert elements(neighbours(tasks, S.wake)) == [S.coffee, S.shower]
    assert elements(neighbours(tasks, S.lunch)) == []
    assert refused(S.graph_neighbours(tasks, S.dinner))

    # Adding and removing. A vertex arrives with no neighbours, an edge brings its
    # vertices with it, and removing a vertex removes every edge that touched it.
    assert graph_rows(add_vertices(tasks, (S.nap,)).one()) == [
        (S.coffee, []),
        (S.dress, []),
        (S.lunch, []),
        (S.nap, []),
        (S.shower, [S.dress]),
        (S.wake, [S.coffee, S.shower]),
    ]
    assert graph_rows(add_edges(S.graph_of((), ()), ((S.a, S.b),)).one()) == [
        (S.a, [S.b]), (S.b, []),
    ]
    assert graph_rows(remove_vertices(tasks, (S.shower,)).one()) == [
        (S.coffee, []), (S.dress, []), (S.lunch, []), (S.wake, [S.coffee]),
    ]
    assert graph_rows(remove_edges(tasks, ((S.wake, S.coffee),)).one()) == [
        (S.coffee, []),
        (S.dress, []),
        (S.lunch, []),
        (S.shower, [S.dress]),
        (S.wake, [S.shower]),
    ]
    # The input is left alone by all four.
    assert elements(vertices(tasks)) == [S.coffee, S.dress, S.lunch, S.shower, S.wake]

    # The transpose reverses every edge and keeps every vertex, so the union of a
    # graph and its transpose is the undirected reading of it.
    assert rows(edges(S.graph_transpose(tasks))) == [
        (S.coffee, S.wake), (S.dress, S.shower), (S.shower, S.wake),
    ]
    assert elements(vertices(S.graph_transpose(tasks))) == [
        S.coffee, S.dress, S.lunch, S.shower, S.wake,
    ]
    assert rows(edges(S.graph_union(tasks, S.graph_transpose(tasks)))) == [
        (S.coffee, S.wake), (S.dress, S.shower), (S.shower, S.dress),
        (S.shower, S.wake), (S.wake, S.coffee), (S.wake, S.shower),
    ]

    # The closure holds an edge for every path of one step or more, and
    # reachability is the same question asked from one vertex, reflexively.
    assert rows(edges(S.graph_closure(tasks))) == [
        (S.shower, S.dress), (S.wake, S.coffee), (S.wake, S.dress), (S.wake, S.shower),
    ]
    assert elements(reachable(tasks, S.wake)) == [S.coffee, S.dress, S.shower, S.wake]
    assert elements(reachable(tasks, S.lunch)) == [S.lunch]

    # A topological order puts every edge's tail before its head, and a graph with
    # a cycle has none: the refusal names a vertex that reaches itself.
    assert elements(order(tasks)) == [S.lunch, S.wake, S.coffee, S.shower, S.dress]
    assert acyclic(tasks) == [True]
    loop = graph_of((), ((S.a, S.b), (S.b, S.c), (S.c, S.a))).one()
    assert acyclic(loop) == [False]
    assert refused(S.graph_topological_order(loop))
    # A self-edge is the smallest cycle there is.
    assert acyclic(S.graph_of((), ((S.a, S.a),))) == [False]
    assert elements(reachable(loop, S.a)) == [S.a, S.b, S.c]

    # A value that is not a graph is refused by every head; core assertions
    # preserve the invalid shape in their message.
    assert refused(S.graph_vertices(((S.a, (S.b,)),)))
    # A number is refused by the DECLARATION rather than by the head, so it
    # answers the engine's own BadArgType where the others raise; if-error reads
    # both the same way.
    assert list(m.eval(S.graph_closure(7))) == [
        S.Error(S.graph_closure(7), S.BadArgType(1, S.Expression, S.Number)),
    ]
    assert refused(S.graph_add_edges(tasks, ((S.a,),)))

    assert graph_rows(m.fn.graph_union().one()) == []
    assert graph_rows(m.fn.graph_union(tasks).one()) == graph_rows(tasks)
    assert elements(vertices(S.graph_union(tasks, loop, S.graph_of((S.nap,), ())))) == [
        S.a, S.b, S.c, S.coffee, S.dress, S.lunch, S.nap, S.shower, S.wake,
    ]
    graphs = (tasks, loop)
    assert elements(vertices(S.graph_union(*graphs))) == [
        S.a, S.b, S.c, S.coffee, S.dress, S.lunch, S.shower, S.wake,
    ]
    choices = S.superpose((((S.a, S.b),), ((S.a, S.c),)))
    assert [tuple(row) for row in neighbours(S.graph_of((), choices), S.a)] == [
        (S.b,), (S.c,),
    ]

    assert is_graph(S.quote(((S.a, (V.x,)), (S.b, ())))) == [False]
    shared = ((V.x, (V.y,)), (V.y, ()))
    assert is_graph(S.quote(shared)) == [True]
    assert refused(S.graph_neighbours(tasks, V.missing))
    made = graph_of(S.quote((V.x, V.y)), S.quote(((V.x, V.y),))).one()
    assert len(made.vars) == 2 and graph_rows(made) == [
        (made[0][0], [made[1][0]]), (made[1][0], []),
    ]
    closed = m.fn.graph_closure(S.quote(shared)).one()
    assert len(closed.vars) == 2 and graph_rows(closed) == [
        (closed[0][0], [closed[1][0]]), (closed[1][0], []),
    ]
    literal = S.graph_of((), S.quote(((S["+"](1, 2), S.Error(S.data, S.code)),)))
    assert elements(neighbours(literal, S.quote(S["+"](1, 2)))) == [S.Error(S.data, S.code)]
    assert graph_rows(remove_vertices(literal, S.quote((S["+"](1, 2),))).one()) == [
        (S.Error(S.data, S.code), []),
    ]
    error_loop = S.graph_of((), S.quote(((S.Error(S.data, S.code), S.Error(S.data, S.code)),)))
    assert acyclic(error_loop) == [False]
    assert reachable(S.graph_of((), S.quote(((S.Error, S.a), (S.a, S.b)))), S.Error) == [
        (S.Error, S.a, S.b),
    ]

    row = m.match(S["="](S.graph_reachable(V.graph, V.vertex), V.body)).one()
    recipe = S["|->"]((row.graph, row.vertex), row.body)
    walk = m.eval(recipe)[0]
    assert list(m.eval((walk, tasks, S.wake))) == [(S.coffee, S.dress, S.shower, S.wake)]
    row = m.match(S["="](S.graph_reachable(tasks, V.vertex), V.body)).one()
    recipe = S["|->"]((row.vertex,), row.body)
    walk = m.eval(recipe)[0]
    assert list(m.eval((walk, S.shower))) == [(S.dress, S.shower)]

    assert elements(order(S.graph_of((S.alone,), ((S.a, S.z), (S.b, S.c))))) == [
        S.a, S.alone, S.b, S.c, S.z,
    ]
    assert acyclic(S.graph_of((), ((S.a, S.b), (S.b, S.a), (S.b, S.tail)))) == [False]


#: The preceding 34-claim native graph fixture was pinned at 92402 and needed
#: an overrun of 2649 for value crossings. The derived 52-claim fixture runs
#: inside the ordinary ten-percent band, so that overrun is retired.
#: [measured: 8975689 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/25-graph_lib.metta;
#: fixture=52 claims, fresh serial processes after engine/lib QLF purge,
#: MeTTa 8991153, equal stored contents; commit=WORKTREE].
BUDGET = 8975689
