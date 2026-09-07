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
    test_the_document_validates_against_the_openapi_specification; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - `components.schemas.Atom` admits exactly the tags the wire decoder accepts,
    so a tag added to one is missing from the other loudly
    [tested: test_the_atom_schema_covers_every_wire_tag; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - one arm per term tag, built from the engine's own `(wire-tag ...)` rows
    with the row's own sentence as its description, so a tag the catalog gains
    reaches a served gateway with no edit here
    [tested: test_the_atom_schema_is_one_arm_per_term_tag; commit=7f9c810e5f4a2023ad98de34e848667dd72bc4a7]
  - the bearer scheme appears exactly when the server is configured with a token
    [tested: test_a_token_puts_a_bearer_scheme_in_the_document; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from ._declarations import Declaration, declared
from ._optional import require_module
from ._projection import (
    ATOM_REF,
    ATOM_SCALAR,
    NUMBER_SCALAR,
    argument_types,
    graphql_type,
    json_schema,
    result_type,
)
from ._space_objects import _format_doc_atom
from .atoms import Atom, Expression, Grounded, Symbol, _decode, _encode, parse
from .errors import MettaError
from .vocabularies import WIRE_TAGS, WireClass, WirePayload

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ._space import Space

#: The dialect an OpenAPI 3.1 document's schemas are written in, which the
#: specification names as the default and this document states anyway, because a
#: reader that has to guess is the thing these documents exist to stop.
JSON_SCHEMA_DIALECT: Final = "https://json-schema.org/draft/2020-12/schema"

#: The wire protocol revision the document describes, the same number
#: `GET /health` answers [source: extensions/python/metta/remote.py:_health].
PROTOCOL: Final = 3

#: JSON Schema for one class of wire payload. The engine's `(wire-tag ...)`
#: rows say which class each tag carries and this is the seat's column for it,
#: exactly as `_projection.TypeRow` carries one column per target for a MeTTa
#: type. `terms` is the recursive case; `handle` is the one three-element shape
#: and is spelled at its arm below rather than here.
_PAYLOAD_SCHEMAS: Final[dict[WirePayload, dict[str, Any]]] = {
    WirePayload.text: {"type": "string"},
    WirePayload.number: {"type": "number"},
    WirePayload.boolean: {"anyOf": [{"type": "boolean"}, {"enum": ["true", "false"]}]},
    WirePayload.terms: {"type": "array", "items": {"$ref": ATOM_REF}},
    WirePayload.host: {},
}

#: What a gateway over HTTP cannot carry, said once. The `o` tag's payload is a
#: live host reference, so a JSON body has no spelling for it and the document
#: says so beside the arm rather than leaving a reader to discover it.
_TRANSPORT_NOTES: Final[dict[str, str]] = {
    "o": (
        " -- only an in-process transport carries one: a JSON body cannot hold "
        "it, so a gateway over HTTP never answers this tag"
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
    spells a recursive type. The arms come from the engine's own
    `(wire-tag ...)` rows through `metta.vocabularies.WIRE_TAGS`, so this is
    the grammar as a machine reads it rather than a copy of it; `CODEC.md`
    states the same rows for a person.
    """
    arms = []
    for tag, row in WIRE_TAGS.items():
        if row.kind is not WireClass.term:
            continue
        note = _TRANSPORT_NOTES.get(tag, "")
        if row.payload is WirePayload.handle:
            arms.append({
                "type": "array",
                "prefixItems": [{"const": tag}, {"type": "integer"}, {"type": "string"}],
                "items": False,
                "minItems": 3,
                "maxItems": 3,
                "description": f"{row.means}, and the text it prints as{note}",
            })
            continue
        arms.append(_tagged(tag, _PAYLOAD_SCHEMAS[row.payload], f"{row.means}{note}"))
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
    answer and the reason to declare. `x-metta-unnameable` beside it is where a
    head GraphQL cannot spell goes, with the door that still reaches it, so a
    head omitted from the SDL is named somewhere rather than silently absent.
    """
    catalog = _catalog(spaces)
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
        "x-metta-heads": {
            name: [entry for entry in (_head_entry(row) for row in rows) if entry]
            for name, rows in catalog.rows.items()
        },
        "x-metta-unnameable": catalog.unnameable,
    }


# --------------------------------------------------------------- the GraphQL half

#: GraphQL's own name grammar, which decides which heads reach the SDL
#: [source: https://spec.graphql.org/October2021/#sec-Names].
_GRAPHQL_NAME = re.compile(r"^[_A-Za-z][_0-9A-Za-z]*$")

#: The Query field every schema carries whatever the space declares, and the
#: names a head may therefore not take.
_RESERVED_FIELDS: Final = frozenset({"match"})

#: The remedy a head outside the SDL is published with. The bracket door reaches
#: any head by its exact name, which is the same escape the generated stub gives
#: a name Python cannot spell.
_UNNAMEABLE_REMEDY: Final = (
    "GraphQL names are [_A-Za-z][_0-9A-Za-z]*, so this head has no field of its "
    'own; reach it through match(pattern: "(<head> $x1 ...)")'
)


class _Head(NamedTuple):
    """One declared head as the SDL publishes it."""

    name: str
    space: str
    row_type: str
    arguments: tuple[Atom, ...]
    documentation: str | None


class _Catalog(NamedTuple):
    """Every served space's declarations, read once and shared by both documents.

    Both projections want the same rows, and reading them twice would read the
    engine twice for one request that publishes both.
    """

    rows: dict[str, tuple[Declaration, ...]]
    heads: tuple[_Head, ...]
    unnameable: dict[str, str]


def _row_type_name(head: str) -> str:
    """`users` as `UsersRow`, which is GraphQL's own casing for a type."""
    return f"{head[0].upper()}{head[1:]}Row"


def _catalog(spaces: Mapping[str, Space | Any]) -> _Catalog:
    """Read every served space once, and decide which heads GraphQL can name.

    A head is refused a field for one of three reasons, each named in
    `unnameable` with the remedy: its own name is outside GraphQL's grammar, its
    row type collides with one already taken, or it would shadow the `match`
    field every schema carries. Spaces are read in the order the gateway serves
    them, so which of two colliding heads keeps the field is stable.
    """
    rows = {name: declared(space) for name, space in spaces.items()}
    heads: list[_Head] = []
    unnameable: dict[str, str] = {}
    taken: set[str] = set()
    for space_name, declarations in rows.items():
        for row in declarations:
            arrows = row.arrows
            if not arrows:
                continue
            row_type = _row_type_name(row.name)
            if not _GRAPHQL_NAME.match(row.name) or row.name in _RESERVED_FIELDS:
                unnameable.setdefault(row.name, _UNNAMEABLE_REMEDY)
                continue
            if row.name in taken or row_type in {head.row_type for head in heads}:
                unnameable.setdefault(
                    row.name,
                    f"another served space already publishes {row.name} as "
                    f"{row_type}; reach this one through "
                    f'match(pattern: "({row.name} $x1 ...)", space: "{space_name}")',
                )
                continue
            taken.add(row.name)
            heads.append(
                _Head(
                    row.name,
                    space_name,
                    row_type,
                    argument_types(arrows[0]),
                    _format_doc_atom(row.documentation) if row.documentation else None,
                )
            )
    return _Catalog(rows, tuple(heads), unnameable)


def _sdl_description(text: str | None, indent: str = "") -> list[str]:
    """One SDL block description, or nothing.

    A description is a block string, so the only thing that has to be escaped is
    the closing delimiter itself.
    """
    if not text:
        return []
    body = text.replace('"""', '\\"\\"\\"')
    return [f'{indent}"""', *(f"{indent}{line}".rstrip() for line in body.split("\n")), f'{indent}"""']


def _parameter_descriptions(row: Declaration | None) -> list[str | None]:
    """One `@param` description per argument, from a head's `(@doc ...)` row.

    A `(@param ...)` carries a TYPE and a description and never a name
    [source: engine/metta/runtime.pl, doc_params/5], so the field NAMES stay
    `x1..xn`, which is what the generated stub and `inspect.signature` already
    say, and the description is what the row actually holds.
    """
    if row is None or row.documentation is None:
        return []
    for part in row.documentation.children[2:]:
        if not (isinstance(part, Expression) and part.children):
            continue
        if part.children[0] == Symbol("@params") and len(part.children) > 1:
            block = part.children[1]
            if isinstance(block, Expression):
                return [_doc_text(entry) for entry in block.children]
    return []


def _doc_text(entry: Atom) -> str | None:
    """The description one `(@param (@type T) (@desc "..."))` entry carries."""
    if not isinstance(entry, Expression):
        return None
    for field in entry.children[1:]:
        if isinstance(field, Expression) and field.children[:1] == (Symbol("@desc"),):
            rest = field.children[1:]
            return str(_decode(rest[0])) if rest else None
        if isinstance(field, Grounded):
            return str(_decode(field))
    return None


def graphql_sdl(spaces: Mapping[str, Space | Any]) -> str:
    """The GraphQL schema of a gateway's served spaces, as SDL text.

        print(gateway.graphql_schema())

    `scalar Atom` carries any atom as its canonical MeTTa text and `scalar
    Number` carries a MeTTa number, which no built-in GraphQL scalar can: `Int`
    is 32-bit signed and `Float` is a double. `Query.match` reaches every atom
    of every served space whatever it declares; one field per declared head
    reaches that head's rows typed.

    This is built as TEXT, so a server publishes its schema whether or not
    graphql-core is installed. Only executing a query needs the package.
    """
    catalog = _catalog(spaces)
    by_name = {
        (space_name, row.name): row
        for space_name, rows in catalog.rows.items()
        for row in rows
    }
    lines = [
        *_sdl_description(
            "The spaces this engine serves. Every value crosses as an Atom, "
            "the canonical MeTTa text that `parse` reads back, except where a "
            "head's declared argument type has a scalar of its own."
        ),
        "scalar Atom",
        "",
        *_sdl_description(
            "A MeTTa number, exact at any width. It crosses as a JSON number "
            "where one holds it and as canonical text where none does, because "
            "GraphQL's Int is 32-bit and its Float is a double."
        ),
        "scalar Number",
        "",
    ]
    for head in catalog.heads:
        row = by_name.get((head.space, head.name))
        descriptions = _parameter_descriptions(row)
        lines.extend(_sdl_description(head.documentation))
        lines.append(f"type {head.row_type} {{")
        for position, kind in enumerate(head.arguments, start=1):
            described = descriptions[position - 1] if position <= len(descriptions) else None
            lines.extend(_sdl_description(described, "  "))
            lines.append(f"  x{position}: {graphql_type(kind)}")
        lines.extend(("}", ""))
    lines.append("type Query {")
    lines.extend(_sdl_description(
        "Every candidate for a pattern, written as MeTTa source. The engine "
        "that receives them re-unifies, so this may over-approximate and never "
        "under-approximates.",
        "  ",
    ))
    lines.append("  match(pattern: String!, limit: Int, space: String): [Atom!]!")
    for head in catalog.heads:
        arguments = ", ".join(
            f"x{position}: Atom" for position in range(1, len(head.arguments) + 1)
        )
        arguments = f"{arguments}, space: String" if arguments else "space: String"
        lines.extend(_sdl_description(head.documentation, "  "))
        lines.append(f"  {head.name}({arguments}): [{head.row_type}!]!")
    lines.extend(("}", ""))
    lines.extend((
        "type Mutation {",
        "  add(atom: String!, space: String): Boolean!",
        "  remove(atom: String!, space: String): Boolean!",
        "}",
        "",
    ))
    return "\n".join(lines)


_GRAPHQL_EXTRA: Final = (
    "executing a GraphQL query needs graphql-core, which is not installed; "
    "install pymetta[graphql]. GET /graphql still answers the schema without it"
)


def graphql_value(cell: Atom, kind: str) -> Any:
    """One answer cell as the value its field's GraphQL scalar can carry.

    `Atom` takes the atom itself and its serializer renders the canonical text;
    a built-in scalar takes the Python value behind a Grounded and answers null
    where the cell holds something else, which is `_arrow.values_of`'s rule for
    a column asked for at a kind its cells do not all fit.
    """
    if kind == ATOM_SCALAR:
        return cell
    raw = getattr(cell, "value", None) if isinstance(cell, Grounded) else None
    if kind == NUMBER_SCALAR:
        return raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
    if kind == "String":
        return raw if isinstance(raw, str) else None
    if kind == "Boolean":
        return raw if isinstance(raw, bool) else None
    return None


def _serialize_atom(value: Any) -> str:
    """The `Atom` scalar's output: canonical MeTTa text, which `parse` reads back."""
    return str(value) if isinstance(value, Atom) else str(_encode(value))


def _serialize_number(value: Any) -> Any:
    """The `Number` scalar's output: the JSON number, or text where none holds it.

    A Fraction and an integer past what a JSON consumer's number type holds are
    the two cases; both keep every digit as canonical MeTTa text rather than
    rounding into a double.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _serialize_atom(value)
    return value


def build_graphql_schema(sdl: str) -> Any:
    """The executable schema for one SDL text, with this engine's scalars on it.

    `build_schema` gives a custom scalar the identity serializer, which would
    hand an atom object to a JSON encoder; the two scalars this schema declares
    are given theirs here [source:
    https://github.com/graphql-python/graphql-core, GraphQLScalarType's
    constructor assigning `serialize` and `parse_value` as plain attributes].
    """
    graphql = require_module("graphql", _GRAPHQL_EXTRA)
    schema = graphql.build_schema(sdl)
    for name, serializer in ((ATOM_SCALAR, _serialize_atom), (NUMBER_SCALAR, _serialize_number)):
        scalar = schema.type_map.get(name)
        if scalar is None:
            continue
        # graphql-core 3.2 calls `serialize`; 3.3 renames it `coerce_output_value`
        # and keeps both on the class, so whichever exists is set.
        for attribute in ("serialize", "coerce_output_value"):
            if hasattr(scalar, attribute):
                setattr(scalar, attribute, serializer)
    atom = schema.type_map.get(ATOM_SCALAR)
    if atom is not None:
        atom.parse_value = parse
    return schema


def execute_graphql(
    schema: Any,
    root: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one GraphQL request against a schema and answer the response body.

    The request is GraphQL over HTTP's own shape, `query`, `variables` and
    `operationName` [source: https://graphql.github.io/graphql-over-http/draft/,
    the POST request body], and the answer is its `data` and `errors`.
    """
    graphql = require_module("graphql", _GRAPHQL_EXTRA)
    query = request.get("query")
    if not isinstance(query, str) or not query.strip():
        msg = "a GraphQL request needs a `query` field holding the document text"
        raise MettaError(msg)
    variables = request.get("variables")
    if variables is not None and not isinstance(variables, dict):
        msg = f"GraphQL variables must be an object, got {type(variables).__name__}"
        raise MettaError(msg)
    result = graphql.graphql_sync(
        schema,
        query,
        root_value=dict(root),
        variable_values=variables,
        operation_name=request.get("operationName"),
    )
    answer: dict[str, Any] = {"data": result.data}
    if result.errors:
        answer["errors"] = [error.formatted for error in result.errors]
    return answer


def graphql_heads(spaces: Mapping[str, Space | Any]) -> tuple[_Head, ...]:
    """The heads the SDL publishes, which are the fields a resolver must answer."""
    return _catalog(spaces).heads


#: Every wire tag the document's Atom schema must carry, re-exported so a
#: reader takes the engine's own table rather than a copy here.
__all__ = [
    "WIRE_TAGS",
    "atom_schema",
    "build_graphql_schema",
    "execute_graphql",
    "graphql_heads",
    "graphql_sdl",
    "graphql_value",
    "head_entries",
    "openapi_document",
]
