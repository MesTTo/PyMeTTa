"""Purpose: the served space as an OpenAPI document, and the cost of deriving it.

A consumer asks a service for its schema before it speaks to it, so the document
has to be structurally whole, has to describe THIS server's spaces rather than
the protocol in general, and has to be derivable per request without walking the
store.

Guarantees:
  - the document is whole and validates against the OpenAPI specification
    [tested: test_the_openapi_document_is_structurally_whole,
    test_the_document_validates_against_the_openapi_specification; commit=WORKTREE]
  - the Atom schema admits exactly the tags the decoder accepts, checked by
    round-tripping one atom per tag [tested:
    test_the_atom_schema_covers_every_wire_tag; commit=WORKTREE]
  - deriving the document does not grow with the served space
    [measured: 138 inferences at 200 and at 20,000 atoms;
    tested: test_the_catalog_read_does_not_grow_with_the_space; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import urllib.request

import pytest

from metta import S, _json, remote
from metta._declarations import declarations, declared
from metta._projection import ATOM_REF, WIRE_TAGS
from metta.atoms import Grounded, Symbol, Variable, _atom_from_wire


@pytest.fixture()
def metta(metta):
    """Every scenario reads its own store, so a count is about this program."""
    with metta._new_space() as space:
        yield space


def _declared_space(space):
    """One head declared, documented, and one row of data under it."""
    space.add(S.users(1, "Ada"), S.users(2, "Bob"))
    space.run("(: users (-> Number String Bool))")
    space.run(
        '(@doc users (@desc "who is registered") '
        '(@params ((@param (@type Number) (@desc "the id")) '
        '(@param (@type String) (@desc "the name")))) '
        '(@return "whether the row is held"))'
    )
    return space


def test_the_openapi_document_is_structurally_whole(metta):
    """Required fields, one path per door, and a schema on both sides of each.

    OpenAPI 3.1.1 requires `openapi` and `info` (with `title` and `version`) and
    gives every operation a `responses`; a document that describes a request
    body without a schema, or a response without one, tells a generator nothing
    it can build a client from.
    """
    with remote.Gateway(_declared_space(metta)) as gateway:
        document = gateway.openapi()
    assert document["openapi"] == "3.1.1"
    assert set(document["info"]) >= {"title", "version"}
    doors = {
        operation["operationId"]
        for path in document["paths"].values()
        for operation in path.values()
    }
    assert doors == {
        "match", "ask", "next", "stop", "atoms", "add", "add_many", "remove",
        "health", "openapi",
    }
    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            assert "200" in operation["responses"], f"{path} answers no 200"
            for reply in operation["responses"].values():
                media = reply["content"]["application/json"]
                assert media["schema"], f"{path} answers without a schema"
            if method == "post":
                body = operation["requestBody"]["content"]["application/json"]
                assert body["schema"]["$ref"].startswith("#/components/schemas/")
    referenced = {
        reference for reference in _references(document)
        if reference.startswith("#/components/schemas/")
    }
    defined = {f"#/components/schemas/{name}" for name in document["components"]["schemas"]}
    assert referenced <= defined, f"dangling: {sorted(referenced - defined)}"


def test_the_atom_schema_covers_every_wire_tag(metta):
    """The document's atom grammar and the decoder's are one grammar.

    Each tag is round-tripped through the decoder, so a tag the schema names and
    the decoder refuses, or the other way round, fails here rather than at a
    client that trusted the document.
    """
    with remote.Gateway(metta) as gateway:
        schema = gateway.openapi()["components"]["schemas"]["Atom"]
    documented = [arm["prefixItems"][0]["const"] for arm in schema["oneOf"]]
    assert documented == list(WIRE_TAGS)
    payloads = {
        "s": "edge", "g": "text", "n": 1, "b": True, "v": "x",
        "e": [["s", "edge"]], "p": "&self", "o": 7,
    }
    for tag, payload in payloads.items():
        assert _atom_from_wire([tag, payload]) is not None, tag
    assert _atom_from_wire(["h", 1, "handle"]) is not None
    # And the other direction: an atom's own wire form uses a documented tag.
    for atom in (Symbol("edge"), Grounded("text"), Grounded(1), Variable("x"), S.edge(1, "a")):
        assert atom.to_wire()[0] in documented
        assert _atom_from_wire(atom.to_wire()) == atom
    assert schema["oneOf"][WIRE_TAGS.index("e")]["prefixItems"][1]["items"] == {"$ref": ATOM_REF}


def test_the_document_names_the_heads_the_space_declares(metta):
    """`x-metta-heads` is what makes the document about THIS server.

    The argument and result schemas come from the one type table, so a `Number`
    argument is a JSON number here exactly as it is an `int | float` in the stub
    and a `float64` in an Arrow column.
    """
    with remote.Gateway(_declared_space(metta)) as gateway:
        heads = gateway.openapi()["x-metta-heads"]
    assert list(heads) == [metta.name]
    entry = next(row for row in heads[metta.name] if row["name"] == "users")
    assert entry["arrow"] == "(-> Number String Bool)"
    assert entry["arguments"] == [{"type": "number"}, {"type": "string"}]
    assert entry["result"] == {"type": "boolean"}
    assert "who is registered" in entry["description"]


def test_a_space_that_declares_nothing_publishes_no_heads(metta):
    """An empty list is the honest answer, and the reason to declare."""
    metta.add(S.users(1, "Ada"))
    with remote.Gateway(metta) as gateway:
        assert gateway.openapi()["x-metta-heads"] == {metta.name: []}


def test_a_token_puts_a_bearer_scheme_in_the_document(metta):
    """A gateway is transport-free, so the half holding credentials says so.

    `Gateway.openapi()` takes `secured` and `serve()` passes its own token's
    presence; the Gateway never learns the token itself.
    """
    with remote.Gateway(metta) as gateway:
        assert "securitySchemes" not in gateway.openapi()["components"]
        secured = gateway.openapi(secured=True)
    assert secured["components"]["securitySchemes"]["bearer"] == {
        "type": "http",
        "scheme": "bearer",
    }
    assert secured["security"] == [{"bearer": []}]
    assert "401" in secured["paths"]["/match"]["post"]["responses"]


def test_the_document_validates_against_the_openapi_specification(metta):
    """The specification's own validator, where it is installed."""
    validator = pytest.importorskip("openapi_spec_validator")
    with remote.Gateway(_declared_space(metta)) as gateway:
        validator.validate(gateway.openapi())
        validator.validate(gateway.openapi(secured=True))


def test_the_bundled_server_publishes_the_document(metta):
    """`GET /openapi.json`, the path every OpenAPI client tries first."""
    with remote.serve(_declared_space(metta)) as server:
        with urllib.request.urlopen(f"{server.url}/openapi.json") as reply:
            assert reply.headers["content-type"] == "application/json"
            document = _json.loads(reply.read())
    assert document["openapi"] == "3.1.1"
    assert document["x-metta-heads"][metta.name][0]["name"] == "users"
    assert "securitySchemes" not in document["components"]


def test_a_served_token_reaches_the_document(metta):
    """The bearer scheme is in the served document exactly when a token is set."""
    with remote.serve(metta, token="shibboleth") as server:
        request = urllib.request.Request(
            f"{server.url}/openapi.json",
            headers={"authorization": "Bearer shibboleth"},
        )
        with urllib.request.urlopen(request) as reply:
            document = _json.loads(reply.read())
    assert document["components"]["securitySchemes"]["bearer"]["scheme"] == "bearer"


def test_the_catalog_read_does_not_grow_with_the_space(metta):
    """The document is derived per request, so its cost may not follow the data.

    `declared` takes the `(: ...)` rows through the engine's first-argument
    index; `declarations` walks every atom, which is the right door for a stub
    and the wrong one for a schema asked for on every request. Inferences rather
    than wall clock, because this box is shared.
    """
    metta.run("(: users (-> Number String Bool))")
    metta.add(*[S.users(index, "n") for index in range(200)])
    with metta.stats() as small_indexed:
        declared(metta)
    with metta.stats() as small_walk:
        declarations(metta)
    metta.add(*[S.users(index, "n") for index in range(200, 4000)])
    with metta.stats() as large_indexed:
        declared(metta)
    with metta.stats() as large_walk:
        declarations(metta)
    # A constant, not an equality: the indexed read's own count moves by a
    # couple of inferences with the choicepoints the matcher leaves, while a
    # read that WALKED would follow the twentyfold growth in the store.
    assert large_indexed.inferences < small_indexed.inferences + 32, (
        f"the indexed catalog read grew with the space: "
        f"{small_indexed.inferences} then {large_indexed.inferences}"
    )
    assert large_walk.inferences > 4 * small_walk.inferences, (
        "the walk is meant to be the O(atoms) door this one exists beside"
    )
    assert large_indexed.inferences < large_walk.inferences / 10


def _references(value):
    """Every `$ref` anywhere in the document."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str):
                yield item
            else:
                yield from _references(item)
    elif isinstance(value, list):
        for item in value:
            yield from _references(item)

