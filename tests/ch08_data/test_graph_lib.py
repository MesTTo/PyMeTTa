"""Purpose: compare graph equations with independent finite Python graph models.

Guarantees: generated edge sets exercise construction, edits, paths and topology;
literal vertices, shared variables and reflected equations cross the Python door.
[tested: test_graph_lib.py; commit=WORKTREE].
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import S, V, lib
from metta._errors.errors import MettaError


@pytest.fixture(scope="module")
def graphs(metta):
    """Import the public graph library and its collection basis."""
    metta += lib.graph
    return metta


VERTICES = st.sets(st.integers(0, 4), max_size=5)
EDGES = st.lists(st.tuples(st.integers(0, 4), st.integers(0, 4)), max_size=10)


def graph_model(vertices, edges):
    """Canonical adjacency rows include every endpoint and isolated vertex."""
    all_vertices = set(vertices) | {vertex for edge in edges for vertex in edge}
    return tuple((vertex, tuple(sorted({target for source, target in edges if source == vertex})))
                 for vertex in sorted(all_vertices))


def reachable_model(edges, origin):
    """A worklist visits exactly the endpoints of nonempty paths."""
    pending = [target for source, target in edges if source == origin]
    reached = set()
    while pending:
        vertex = pending.pop()
        if vertex not in reached:
            reached.add(vertex)
            pending.extend(target for source, target in edges if source == vertex)
    return reached


@settings(max_examples=80, deadline=None)
@given(VERTICES, EDGES)
def test_graph_paths_and_topology(graphs, vertices, edges):
    """A worklist model and edge precedence independently check the path recipe."""
    graph = graphs.fn.graph_of(tuple(sorted(vertices)), tuple(edges)).one()
    expected = graph_model(vertices, edges)
    assert graph == expected
    all_vertices = {vertex for vertex, _ in expected}
    assert graphs.fn.graph_is(graph) == [True]
    assert graphs.fn.graph_edges(graph) == [tuple(sorted(set(edges)))]
    paths = {vertex: reachable_model(edges, vertex) for vertex in all_vertices}
    closure = tuple((vertex, tuple(sorted(paths[vertex]))) for vertex in sorted(all_vertices))
    assert graphs.fn.graph_closure(graph) == [closure]
    for vertex in all_vertices:
        assert graphs.fn.graph_reachable(graph, vertex) == [tuple(sorted(paths[vertex] | {vertex}))]
    cyclic = any(vertex in paths[vertex] for vertex in all_vertices)
    assert graphs.fn.graph_is_acyclic(graph) == [not cyclic]
    if cyclic:
        with pytest.raises(MettaError, match="cyclic-graph"):
            graphs.fn.graph_topological_order(graph).one()
    else:
        order = [int(vertex) for vertex in graphs.fn.graph_topological_order(graph).one()]
        assert set(order) == all_vertices and len(order) == len(all_vertices)
        positions = {vertex: index for index, vertex in enumerate(order)}
        assert all(positions[source] < positions[target] for source, target in edges)


@settings(max_examples=80, deadline=None)
@given(VERTICES, EDGES, VERTICES, EDGES)
def test_graph_edits_and_transpose(graphs, vertices, edges, changed_vertices, changed_edges):
    """Set edits model incident-edge removal, retained endpoints and duplicate edges."""
    graph = graphs.fn.graph_of(tuple(sorted(vertices)), tuple(edges)).one()
    all_vertices = {vertex for vertex, _ in graph_model(vertices, edges)}
    assert graphs.fn.graph_add_vertices(graph, tuple(sorted(changed_vertices))) == [
        graph_model(all_vertices | changed_vertices, edges)]
    remaining = [(a, b) for a, b in edges if a not in changed_vertices and b not in changed_vertices]
    assert graphs.fn.graph_remove_vertices(graph, tuple(sorted(changed_vertices))) == [
        graph_model(all_vertices - changed_vertices, remaining)]
    assert graphs.fn.graph_add_edges(graph, tuple(changed_edges)) == [
        graph_model(all_vertices, edges + changed_edges)]
    assert graphs.fn.graph_remove_edges(graph, tuple(changed_edges)) == [
        graph_model(all_vertices, set(edges) - set(changed_edges))]
    assert graphs.fn.graph_transpose(graph) == [
        graph_model(all_vertices, [(b, a) for a, b in edges])]
    other = graphs.fn.graph_of(tuple(sorted(changed_vertices)), tuple(changed_edges)).one()
    assert graphs.fn.graph_union(graph, other, graph) == [
        graph_model(all_vertices | changed_vertices, edges + changed_edges)]
    assert graph == graph_model(vertices, edges)


def test_graph_identity_and_literal_vertices(graphs):
    """Variables retain sharing and runnable syntax remains literal data."""
    shared = ((V.x, (V.y,)), (V.y, ()))
    assert graphs.fn.graph_is(S.quote(shared)) == [True]
    assert graphs.fn.graph_is(S.quote(((S.a, (V.fresh,)), (S.b, ())))) == [False]
    graph = graphs.fn.graph_of(S.quote((V.x, V.y)), S.quote(((V.x, V.y),))).one()
    assert len(graph.vars) == 2
    assert graph[0][1][0] == graph[1][0]
    closed = graphs.fn.graph_closure(S.quote(shared)).one()
    assert len(closed.vars) == 2 and closed[0][1][0] == closed[1][0]
    with pytest.raises(MettaError, match="unknown-vertex"):
        graphs.fn.graph_neighbours(((S.a, ()),), V.fresh).one()
    literal = S["+"](1, 2)
    error = S.Error(S.data, S.code)
    data = graphs.fn.graph_of((), S.quote(((literal, error),))).one()
    assert graphs.fn.graph_neighbours(S.quote(data), S.quote(literal)) == [(error,)]
    assert graphs.fn.graph_remove_vertices(S.quote(data), S.quote((literal,))) == [((error, ()),)]
    assert graphs.fn.graph_is_acyclic(S.graph_of((), S.quote(((error, error),)))) == [False]
    scalar = graphs.fn.graph_of((), S.quote(((S.Error, S.a), (S.a, S.b)))).one()
    assert graphs.fn.graph_reachable(scalar, S.Error) == [(S.Error, S.a, S.b)]


def test_graph_numeric_kinds_and_foreign_vertices(graphs):
    """Identity distinguishes numeric kinds and preserves native object vertices."""
    graph = graphs.fn.graph_of((1, 1.0), ((1, 1.0),)).one()
    assert len(graph) == 2
    assert graphs.fn.graph_neighbours(graph, 1) == [(1.0,)]
    assert graphs.fn.graph_neighbours(graph, 1.0) == [()]
    source, target = object(), object()
    objects = graphs.fn.graph_of((), ((source, target),)).one()
    assert graphs.fn.graph_neighbours(objects, source) == [(target,)]


def test_graph_union_arity_and_layers(graphs):
    """Zero, one and many graph arguments share the same public operation."""
    graph = graphs.fn.graph_of((S.a,), ()).one()
    assert graphs.fn.graph_union() == [()]
    assert graphs.fn.graph_union(graph) == [graph]
    assert graphs.fn.graph_union(*(graph for _ in range(24))) == [graph]
    layers = graphs.fn.graph_of((S.alone,), ((S.a, S.z), (S.b, S.c))).one()
    assert graphs.fn.graph_topological_order(layers) == [(S.a, S.alone, S.b, S.c, S.z)]


def test_graph_recipes_and_alternatives(graphs):
    """Matching reconstructs a graph-specific function and answers remain separate."""
    row = graphs.match(S["="](S.graph_reachable(((S.a, (S.b,)), (S.b, ())), V.vertex),
                              V.body)).one()
    walk = graphs.eval(S["|->"]((row.vertex,), row.body))[0]
    assert list(graphs.eval((walk, S.a))) == [(S.a, S.b)]
    choices = S.superpose((((S.a, S.b),), ((S.a, S.c),)))
    assert graphs.fn.graph_neighbours(S.graph_of((), choices), S.a) == [(S.b,), (S.c,)]


@pytest.mark.parametrize("call", [
    S.graph_vertices(((S.a, (S.b,)),)), S.graph_closure(((S.b, ()), (S.a, ()))),
    S.graph_of((), ((S.a,),)), S.graph_add_edges((), ((S.a, S.b, S.c),)),
    S.graph_remove_edges((), ((S.a,),)), S.graph_is_acyclic(((S.a, (S.a, S.a)),)),
    S.graph_union((), ((S.a, (S.b,)),)),
])
def test_graph_invalid_shapes(graphs, call):
    """Every public composition refuses malformed graphs and edge rows."""
    with pytest.raises(MettaError):
        graphs.eval(call)
