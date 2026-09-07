"""Purpose: the served space as a GraphQL schema, and what executing one costs.

A GraphQL consumer asks for a schema and then sends queries against it, so the
SDL has to parse, its fields have to answer what the wire operations answer, and
a head GraphQL cannot name has to be findable rather than silently absent.

Guarantees:
  - the SDL parses with graphql-core and a `match` query answers what
    `Gateway("match")` answers for the same pattern [tested:
    test_the_schema_parses, test_a_match_query_answers_what_the_wire_answers;
    commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - the schema is served without graphql-core installed and only executing needs
    it [tested: test_the_schema_is_text_and_needs_no_graphql_package,
    test_executing_without_graphql_core_refuses_with_the_extra; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - a head outside GraphQL's name grammar is published under
    `x-metta-unnameable` with its remedy rather than dropped [tested:
    test_a_head_graphql_cannot_name_is_published_not_dropped; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import urllib.request

import pytest

from metta import S, V, _json, remote
from metta._schemas import _GRAPHQL_EXTRA, graphql_sdl
from metta.atoms import _atom_from_wire
from metta.errors import MettaError


@pytest.fixture()
def metta(metta):
    """Every scenario reads and writes its own store."""
    with metta._new_space() as space:
        yield space


@pytest.fixture()
def registry(metta):
    """One declared and documented head, two heads GraphQL cannot name."""
    metta.add(S.users(1, "Ada"), S.users(2, "Bob"))
    metta.run("(: users (-> Number String Bool))")
    metta.run(
        '(@doc users (@desc "who is registered") '
        '(@params ((@param (@type Number) (@desc "the id")) '
        '(@param (@type String) (@desc "the name")))) '
        '(@return "whether the row is held"))'
    )
    metta.run("(: prime? (-> Number Bool))")
    metta.run("(: car-atom (-> Expression Atom))")
    return metta


def test_the_schema_parses(registry):
    """graphql-core reads the SDL this builds, which is the whole promise of it."""
    graphql = pytest.importorskip("graphql")
    with remote.Gateway(registry) as gateway:
        sdl = gateway.graphql_schema()
    schema = graphql.build_schema(sdl)
    assert set(schema.query_type.fields) == {"match", "users"}
    assert set(schema.mutation_type.fields) == {"add", "remove"}
    row = schema.type_map["UsersRow"]
    assert [str(field.type) for field in row.fields.values()] == ["Number", "String"]
    assert row.fields["x1"].description == "the id"
    assert "who is registered" in row.description
    # The scalars a MeTTa value needs, and no others invented.
    scalars = {
        name
        for name, kind in schema.type_map.items()
        if type(kind) is graphql.GraphQLScalarType and not name.startswith("__")
    }
    assert {"Atom", "Number"} <= scalars


def test_the_schema_is_text_and_needs_no_graphql_package(registry, monkeypatch):
    """A server publishes its schema whether or not it can execute a query.

    The SDL is built here as text, so `GET /graphql` answers on an installation
    that has no GraphQL package at all; that is what makes the schema a
    description of the server rather than a feature of one dependency.
    """
    monkeypatch.setattr("metta._optional.import_module", _no_graphql)
    with remote.Gateway(registry) as gateway:
        assert "type Query {" in gateway.graphql_schema()


def test_executing_without_graphql_core_refuses_with_the_extra(registry, monkeypatch):
    """The refusal names the package and the extra that installs it."""
    monkeypatch.setattr("metta._optional.import_module", _no_graphql)
    with remote.Gateway(registry) as gateway, pytest.raises(ImportError) as refusal:
        gateway.graphql({"query": "{ users { x1 } }"})
    assert "pymetta[graphql]" in str(refusal.value)
    assert _GRAPHQL_EXTRA == str(refusal.value)


def test_a_declared_head_answers_typed_rows(registry):
    """A declared `Number` is a JSON number and a declared `String` is a string.

    This is what the type table buys a GraphQL consumer: the row's fields are
    the head's own declared types, not the canonical text every atom falls back
    to.
    """
    pytest.importorskip("graphql")
    with remote.Gateway(registry) as gateway:
        answer = gateway.graphql({"query": "{ users { x1 x2 } }"})
    assert answer == {"data": {"users": [{"x1": 1, "x2": "Ada"}, {"x1": 2, "x2": "Bob"}]}}


def test_an_argument_fixes_a_position_and_comes_back_in_the_row(registry):
    """A supplied argument is a term, and the row is still as wide as the head."""
    pytest.importorskip("graphql")
    with remote.Gateway(registry) as gateway:
        answer = gateway.graphql({"query": '{ users(x1: "2") { x1 x2 } }'})
    assert answer == {"data": {"users": [{"x1": 2, "x2": "Bob"}]}}


def test_a_match_query_answers_what_the_wire_answers(registry):
    """One answer set, two spellings: `Query.match` and `POST /match`.

    The resolver takes the atoms `/match` puts on the wire rather than a second
    query of its own, so the two cannot answer different sets.
    """
    pytest.importorskip("graphql")
    pattern = S.users(V.a, V.b)
    with remote.Gateway(registry) as gateway:
        through_graphql = gateway.graphql(
            {"query": '{ match(pattern: "(users $a $b)") }'}
        )
        through_wire = gateway("match", {"pattern": pattern.to_wire()})
    assert through_graphql["data"]["match"] == [
        str(_atom_from_wire(wire)) for wire in through_wire["atoms"]
    ]


def test_a_bound_travels_as_the_limit_argument(registry):
    """`limit` is the wire's `bound`, honoured exactly by this server."""
    pytest.importorskip("graphql")
    with remote.Gateway(registry) as gateway:
        answer = gateway.graphql(
            {"query": '{ match(pattern: "(users $a $b)", limit: 1) }'}
        )
    assert len(answer["data"]["match"]) == 1


def test_the_mutations_write_through(registry):
    """`add` and `remove` are the wire's own mutations under GraphQL's word."""
    pytest.importorskip("graphql")
    with remote.Gateway(registry) as gateway:
        assert gateway.graphql(
            {"query": 'mutation { add(atom: "(users 3 \\"Cid\\")") }'}
        ) == {"data": {"add": True}}
        assert S.users(3, "Cid") in list(registry.atoms())
        assert gateway.graphql(
            {"query": 'mutation { remove(atom: "(users 3 \\"Cid\\")") }'}
        ) == {"data": {"remove": True}}
    assert S.users(3, "Cid") not in list(registry.atoms())


def test_a_head_graphql_cannot_name_is_published_not_dropped(registry):
    """`prime?` and `car-atom` have no GraphQL field, and the document says so.

    A head omitted with no record of it is the failure this avoids: the OpenAPI
    document names each one with the door that still reaches it, which is the
    same bracket escape a generated Python stub gives a name Python cannot
    spell.
    """
    with remote.Gateway(registry) as gateway:
        sdl = gateway.graphql_schema()
        unnameable = gateway.openapi()["x-metta-unnameable"]
    assert "prime?" not in sdl
    assert "car-atom" not in sdl
    assert set(unnameable) == {"prime?", "car-atom"}
    for remedy in unnameable.values():
        assert "match(pattern:" in remedy


def test_a_head_that_would_shadow_match_is_unnameable(metta):
    """`match` is the field every schema carries, so a head cannot take it."""
    metta.run("(: match (-> Number Number))")
    with remote.Gateway(metta) as gateway:
        assert "match" in gateway.openapi()["x-metta-unnameable"]
        assert "MatchRow" not in gateway.graphql_schema()


def test_an_undeclared_space_publishes_match_alone(metta):
    """No declaration is no field; `match` still reaches every atom."""
    pytest.importorskip("graphql")
    metta.add(S.users(1, "Ada"))
    with remote.Gateway(metta) as gateway:
        sdl = gateway.graphql_schema()
        answer = gateway.graphql({"query": '{ match(pattern: "(users $a $b)") }'})
    assert "type Query {" in sdl
    assert "users(" not in sdl
    assert answer["data"]["match"] == ['(users 1 "Ada")']


def test_a_bad_query_answers_graphqls_own_error(registry):
    """A query error is data in the response, which is GraphQL's own contract."""
    pytest.importorskip("graphql")
    with remote.Gateway(registry) as gateway:
        answer = gateway.graphql({"query": "{ nope }"})
    assert answer["data"] is None
    assert "Cannot query field 'nope'" in answer["errors"][0]["message"]


def test_a_request_without_a_query_refuses_by_name(registry):
    """The refusal names the field, not a KeyError."""
    with remote.Gateway(registry) as gateway, pytest.raises(MettaError) as refusal:
        gateway.graphql({"variables": {}})
    assert "`query` field" in str(refusal.value)


def test_the_bundled_server_serves_the_schema_and_executes(registry):
    """`GET /graphql` is the schema and `POST /graphql` runs a query."""
    pytest.importorskip("graphql")
    with remote.serve(registry) as server:
        with urllib.request.urlopen(f"{server.url}/graphql") as reply:
            assert reply.headers["content-type"] == "text/plain; charset=utf-8"
            sdl = reply.read().decode()
        request = urllib.request.Request(
            f"{server.url}/graphql",
            data=_json.dumps({"query": "{ users { x1 x2 } }"}),
            headers={"content-type": "application/json"},
        )
        with urllib.request.urlopen(request) as reply:
            answer = _json.loads(reply.read())
    assert "type UsersRow {" in sdl
    assert answer["data"]["users"] == [{"x1": 1, "x2": "Ada"}, {"x1": 2, "x2": "Bob"}]


def test_deriving_the_schema_does_not_grow_with_the_space(registry):
    """The SDL is derived per request, so its cost may not follow the data."""
    with registry.stats() as small:
        graphql_sdl({registry.name: registry})
    registry.add(*[S.users(index, "n") for index in range(4000)])
    with registry.stats() as large:
        graphql_sdl({registry.name: registry})
    assert large.inferences < small.inferences + 32, (
        f"schema derivation grew with the space: "
        f"{small.inferences} then {large.inferences}"
    )


def _no_graphql(name, *arguments, **options):
    """importlib.import_module with graphql-core taken out of the installation."""
    import importlib

    if name == "graphql":
        absent = "No module named 'graphql'"
        raise ModuleNotFoundError(absent, name=name)
    return importlib.import_module(name, *arguments, **options)
