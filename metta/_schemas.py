"""Purpose: the served space as the two schema documents a deployment already reads.

A gateway serves spaces over one small HTTP protocol, and the two things a
consumer asks a service for before it speaks to it are an OpenAPI document and,
where the data is a graph, a GraphQL schema. Both are PROJECTIONS of what the
served space already says about itself -- its `(: name type)` rows -- through the
one type table in `_projection.py`, so neither is a second place where the shape
of this wire is written down.

The reading is O(declarations) and not O(atoms): `_declarations.declared` takes
the `:` rows through the engine's own index rather than walking the store, which
is what lets a schema be derived per request with no cache to go stale
[measured 2026-09-07: 232, 230 and 230 inferences at 200, 2,000 and 20,000 atoms
against the walk's 3,911, 34,511 and 340,525;
docs/journal/2026-09-07-one-schema-four-projections.md].

Assumes:
  - each served space answers `match` and `eval`, which is what `declared` needs
Guarantees:
  - the document is OpenAPI 3.1.1: `openapi`, `info` and `paths` present, one
    path per gateway door, every operation carrying a request and a response
    schema [source: https://spec.openapis.org/oas/v3.1.1, sections 4.8.1.1,
    4.8.2.1 and 4.8.10.1; tested: test_the_openapi_document_is_structurally_whole,
    test_the_document_validates_against_the_openapi_specification; commit=WORKTREE]
  - `components.schemas.Atom` admits exactly the tags the wire decoder accepts,
    so a tag added to one is missing from the other loudly
    [tested: test_the_atom_schema_covers_every_wire_tag; commit=WORKTREE]
  - the bearer scheme appears exactly when the server is configured with a token
    [tested: test_a_token_puts_a_bearer_scheme_in_the_document; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from ._declarations import declared
from ._projection import (
    ATOM_REF,
    WIRE_TAGS,
    argument_types,
    json_schema,
    result_type,
)
from ._space_objects import _format_doc_atom

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ._declarations import Declaration
    from ._space import Space

#: The dialect an OpenAPI 3.1 document's schemas are written in, which the
#: specification names as the default and this document states anyway, because a
#: reader that has to guess is the thing these documents exist to stop.
JSON_SCHEMA_DIALECT: Final = "https://json-schema.org/draft/2020-12/schema"

#: The wire protocol revision the document describes, the same number
#: `GET /health` answers [source: extensions/python/metta/remote.py:_health].
PROTOCOL: Final = 3

#: One entry per wire tag: the JSON Schema for its payload, and the sentence the
#: document says about it. `e` is the recursive case and `h` is the one
#: three-element shape [source: extensions/python/metta/_atom_wire.py,
#: _leaf_from_wire/2 and _from_wire/1; commit=WORKTREE].
_TAG_PAYLOADS: Final[dict[str, tuple[dict[str, Any], str]]] = {
    "s": ({"type": "string"}, "a symbol, spelled as the program spells it"),
    "g": ({"type": "string"}, "a string value"),
    "n": ({"type": "number"}, "a number, exact at any width the JSON carries"),
    "b": (
        {"anyOf": [{"type": "boolean"}, {"enum": ["true", "false"]}]},
        "a boolean, as JSON's own or as the two words the engine writes",
    ),
    "v": ({"type": "string"}, "a variable, named without its leading $"),
    "e": (
        {"type": "array", "items": {"$ref": ATOM_REF}},
        "an expression, its children in order",
    ),
    "p": ({"type": "string"}, "a space, named as the engine's registry names it"),
    "o": (
        {},
        "a host object, which only an in-process transport carries: a JSON body "
        "cannot hold one, so a gateway over HTTP never answers this tag",
    ),
}


def _tagged(tag: str, payload: dict[str, Any], description: str) -> dict[str, Any]:
    """One wire shape as a JSON Schema tuple: the tag, then its payload."""
    return {
        "type": "array",
        "prefixItems": [{"const": tag}, payload],
        "items": False,
        "minItems": 2,
        "maxItems": 2,
        "description": description,
    }


def atom_schema() -> dict[str, Any]:
    """The recursive schema for one atom on the wire.

    An atom is a tagged JSON array, so the schema is a `oneOf` over the tags and
    the `e` arm points back at this schema by reference, which is how JSON Schema
    spells a recursive type. `CODEC.md` is the grammar's own authority; this is
    that grammar as a machine reads it.
    """
    arms = [
        _tagged(tag, payload, description)
        for tag, (payload, description) in _TAG_PAYLOADS.items()
    ]
    arms.append({
        "type": "array",
        "prefixItems": [{"const": "h"}, {"type": "integer"}, {"type": "string"}],
        "items": False,
        "minItems": 3,
        "maxItems": 3,
        "description": "a native handle, its identity and the text it prints as",
    })
    return {
        "title": "Atom",
        "description": (
            "One atom as the tagged array the wire carries. The CORE PROFILE a "
            "gateway must speak is s, v, n, g and e; the rest are what this "
            "engine also accepts."
        ),
        "oneOf": arms,
    }


def _components(*, secured: bool) -> dict[str, Any]:
    """Every schema the paths reference, and the security scheme when there is one."""
    atoms = {"type": "array", "items": {"$ref": ATOM_REF}}
    space = {
        "type": "string",
        "description": "which served space answers; the default space when absent",
    }
    cursor = {
        "type": ["string", "null"],
        "description": "the continuation, and null once the stream has ended",
    }
    idempotency = {
        "type": "object",
        "description": (
            "the replay key a mutation negotiates through GET /health, so a "
            "lost reply can be retried without repeating the write"
        ),
        "properties": {
            "key": {"type": "string", "minLength": 1, "maxLength": 255},
            "scope": {"type": "string"},
            "expires": {"type": "number"},
        },
        "required": ["key", "scope", "expires"],
    }
    schemas: dict[str, Any] = {
        "Atom": atom_schema(),
        "Atoms": {
            "type": "object",
            "properties": {"atoms": atoms},
            "required": ["atoms"],
        },
        "Answer": {
            "type": "object",
            "properties": {"atoms": atoms, "cursor": cursor},
            "required": ["atoms", "cursor"],
        },
        "Error": {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "outcome": {
                    "enum": ["unknown"],
                    "description": (
                        "present when a mutation may have been applied; the "
                        "client retries through its idempotency key"
                    ),
                },
            },
            "required": ["error"],
        },
        "Health": {
            "type": "object",
            "properties": {
                "ok": {"const": True},
                "atoms": {"type": "integer", "minimum": 0},
                "protocol": {"type": "integer", "minimum": 1},
                "bound": {"type": "boolean"},
                "capabilities": {"type": "array", "items": {"type": "string"}},
                "idempotency": idempotency,
            },
            "required": ["ok", "atoms"],
        },
        "MatchRequest": {
            "type": "object",
            "properties": {
                "space": space,
                "pattern": {"$ref": ATOM_REF},
                "bound": {"type": "integer", "minimum": 0},
            },
            "required": ["pattern"],
        },
        "AskRequest": {
            "type": "object",
            "properties": {
                "space": space,
                "pattern": {"$ref": ATOM_REF},
                "batch": {"type": "integer", "minimum": 1},
                "bound": {"type": "integer", "minimum": 0},
            },
            "required": ["pattern"],
        },
        "NextRequest": {
            "type": "object",
            "properties": {
                "cursor": {"type": "string"},
                "batch": {"type": "integer", "minimum": 1},
            },
            "required": ["cursor"],
        },
        "StopRequest": {
            "type": "object",
            "properties": {"cursor": {"type": "string"}},
            "required": ["cursor"],
        },
        "Stopped": {
            "type": "object",
            "properties": {"stopped": {"type": "boolean"}},
            "required": ["stopped"],
        },
        "SpaceRequest": {
            "type": "object",
            "properties": {"space": space},
        },
        "AddRequest": {
            "type": "object",
            "properties": {
                "space": space,
                "atom": {"$ref": ATOM_REF},
                "idempotency": idempotency,
            },
            "required": ["atom"],
        },
        "Added": {
            "type": "object",
            "properties": {"added": {"const": True}},
            "required": ["added"],
        },
        "AddManyRequest": {
            "type": "object",
            "properties": {
                "space": space,
                "atoms": atoms,
                "idempotency": idempotency,
            },
            "required": ["atoms"],
        },
        "AddedCount": {
            "type": "object",
            "properties": {"added": {"type": "integer", "minimum": 0}},
            "required": ["added"],
        },
        "RemoveRequest": {
            "type": "object",
            "properties": {
                "space": space,
                "atom": {"$ref": ATOM_REF},
                "idempotency": idempotency,
            },
            "required": ["atom"],
        },
        "Removed": {
            "type": "object",
            "properties": {"removed": {"type": "boolean"}},
            "required": ["removed"],
        },
    }
    components: dict[str, Any] = {"schemas": schemas}
    if secured:
        components["securitySchemes"] = {"bearer": {"type": "http", "scheme": "bearer"}}
    return components


#: One row per POST operation: the door's own name, the request schema, the
#: response schema, and the sentence the document says about it. The
#: `operationId` IS the door's name, so a reader who has the Python surface and
#: a reader who has the document are naming the same thing.
_OPERATIONS: Final[tuple[tuple[str, str, str, str], ...]] = (
    (
        "match",
        "MatchRequest",
        "Atoms",
        "Every candidate for a pattern in one reply; the eager door, which "
        "computes the whole answer set before anything crosses.",
    ),
    (
        "ask",
        "AskRequest",
        "Answer",
        "Open an answer stream and take its first chunk. The reply's cursor is "
        "the continuation and doubles as the more-flag.",
    ),
    (
        "next",
        "NextRequest",
        "Answer",
        "The next chunk of an open stream. A short chunk ends it.",
    ),
    (
        "stop",
        "StopRequest",
        "Stopped",
        "Release a stream early, and say whether there was one to release.",
    ),
    (
        "atoms",
        "SpaceRequest",
        "Atoms",
        "Every atom the named space holds, duplicates included.",
    ),
    ("add", "AddRequest", "Added", "Store one atom in the named space."),
    (
        "add_many",
        "AddManyRequest",
        "AddedCount",
        "Store a batch in one request. A batch is a transport optimisation and "
        "never a semantic one.",
    ),
    (
        "remove",
        "RemoveRequest",
        "Removed",
        "Remove ONE stored atom unifying with this one. Two copies need two "
        "removals.",
    ),
)


def _json_body(schema: str) -> dict[str, Any]:
    return {"content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}}}


def _responses(schema: str, *, secured: bool) -> dict[str, Any]:
    answers: dict[str, Any] = {
        "200": {"description": "the operation's answer", **_json_body(schema)},
        "400": {
            "description": "the engine refused the operation, and says why",
            **_json_body("Error"),
        },
    }
    if secured:
        answers["401"] = {
            "description": "the credential or the authorization hook refused",
            **_json_body("Error"),
        }
    return answers


def _paths(*, secured: bool) -> dict[str, Any]:
    paths: dict[str, Any] = {
        f"/{name}": {
            "post": {
                "operationId": name,
                "summary": summary,
                "requestBody": {"required": True, **_json_body(request)},
                "responses": _responses(response, secured=secured),
            }
        }
        for name, request, response, summary in _OPERATIONS
    }
    paths["/health"] = {
        "get": {
            "operationId": "health",
            "summary": "The wire contract naming its own revision before anyone speaks it.",
            "responses": _responses("Health", secured=secured),
        }
    }
    paths["/openapi.json"] = {
        "get": {
            "operationId": "openapi",
            "summary": "This document, projected from the served spaces' own declarations.",
            "responses": {
                "200": {
                    "description": "the OpenAPI document",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                }
            },
        }
    }
    return paths


def _head_entry(row: Declaration) -> dict[str, Any] | None:
    """One declared head as the document's own account of it, or None.

    A head declared as something other than an arrow -- `(: Point Type)`,
    `(: pi Number)` -- is a type or a value rather than a callable shape, and has
    no argument list to publish.
    """
    arrows = row.arrows
    if not arrows:
        return None
    arrow = arrows[0]
    entry: dict[str, Any] = {
        "name": row.name,
        "arrow": str(arrow),
        "arguments": [json_schema(kind) for kind in argument_types(arrow)],
        "result": json_schema(result_type(arrow)),
    }
    if row.documentation is not None:
        entry["description"] = _format_doc_atom(row.documentation)
    return entry


def head_entries(space: Space | Any) -> list[dict[str, Any]]:
    """Every declared arrow of one space, as the document publishes it."""
    entries = (_head_entry(row) for row in declared(space))
    return [entry for entry in entries if entry is not None]


def openapi_document(
    spaces: Mapping[str, Space | Any],
    *,
    secured: bool = False,
) -> dict[str, Any]:
    """The OpenAPI 3.1.1 document for a gateway serving these spaces.

        document = gateway.openapi()

    `x-metta-heads` is the extension that makes the document about THIS server
    rather than about the protocol: one entry per space, listing the arrows it
    declares with each argument's and the result's schema from the projection.
    A space that declares nothing publishes an empty list, which is the honest
    answer and the reason to declare.
    """
    return {
        "openapi": "3.1.1",
        "jsonSchemaDialect": JSON_SCHEMA_DIALECT,
        "info": {
            "title": "MeTTa remote space protocol",
            "version": f"{PROTOCOL}.0.0",
            "summary": "One engine's spaces, matched and written over HTTP.",
            "description": (
                "Every operation answers for the space the request names. The "
                "attaching engine keeps unification for itself and re-unifies "
                "every candidate, so match may over-approximate and may never "
                "under-approximate."
            ),
        },
        "paths": _paths(secured=secured),
        "components": _components(secured=secured),
        **({"security": [{"bearer": []}]} if secured else {}),
        "x-metta-heads": {name: head_entries(space) for name, space in spaces.items()},
    }


#: Every wire tag the document's Atom schema must carry, re-exported so a test
#: reads it from the projection rather than from a copy here.
__all__ = ["WIRE_TAGS", "atom_schema", "head_entries", "openapi_document"]
