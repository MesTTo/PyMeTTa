"""Purpose: directed graphs as expressions, from Python.

A graph is a tuple of (Vertex Neighbours) pairs, so the example's two `bind!`
forms are ordinary Python names holding what `graph-of` answered. Where the
example NESTS one call inside another it is written here as the built call it is,
`S.graph_transpose(tasks)` rather than `transpose(tasks).one()`: draining the
inner answer would copy a whole graph into the host and pass it back, which is
the crossing the three-lane model prices per value. `rows` reads a graph or an
edge relation as a list of tuples, which is how a (Vertex Neighbours) pair and a
(From To) edge both read.

Guarantees: the same claims as 25-graph_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/25-graph_lib.metta; commit=a5738e9390f2941d8f1c3207b5a28310a22e1f14].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib
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

    # A value that is not a graph is refused by every head, and the message says
    # what the shape is and which head builds one.
    assert refused(S.graph_vertices(((S.a, (S.b,)),)))
    # A number is refused by the DECLARATION rather than by the head, so it
    # answers the engine's own BadArgType where the others raise; if-error reads
    # both the same way.
    assert list(m.eval(S.graph_closure(7))) == [
        S.Error(S.graph_closure(7), S.BadArgType(1, S.Expression, S.Number)),
    ]
    assert refused(S.graph_add_edges(tasks, ((S.a,),)))


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 34 claims cover the fifteen heads, the two
#: orderings and the refusals; the example pays 81,614 inferences for the same
#: work [measured 2026-09-12: 92465 inferences, minimum of three serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/25-graph_lib.metta;
#: fixture=lib_graph at its functional commit, artifacts purged before the run;
#: commit=a5738e9390f2941d8f1c3207b5a28310a22e1f14].
#: RE-PINNED 2026-09-12, 92465 to 92402 (-63), the graph refusals now name the
#: evaluation that reaches a vertex written as a function call, which is two
#: fewer clauses reached on the refusal paths the example exercises [measured
#: 2026-09-12: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 92402

#: OVERRUN 2026-09-12, 2649: the example's `bind!` keeps its graph inside the
#: engine, where a Python name holds the VALUE and hands it back across the
#: boundary on each of the sixteen calls that take it; a five-row graph is a
#: nested expression, so each crossing converts it whole. Writing the nested
#: calls as built terms took the distance from 5,991 to this, which is what is
#: left of the value crossings: measured 92402 against a ceiling of 89753.4
#: [measured 2026-09-12: min-of-3 serial fresh processes, the same command as
#: the budget above, once with `transpose(tasks).one()` and once with
#: `S.graph_transpose(tasks)`; commit=WORKTREE].
OVERRUN = 2649
