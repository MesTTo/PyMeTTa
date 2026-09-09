"""Purpose: one MeTTa type table, one column per target, read by every projection.

A MeTTa type is spelled four other ways here: as the Python annotation a `.pyi`
carries, as a JSON Schema fragment an OpenAPI document carries, as a GraphQL SDL
type name, and as the Arrow kind a record batch's column carries. Each surface
used to answer that question for itself, which is how two of them came to
disagree, so the question is asked once here and each surface takes a column.

    %Undefined%         Any                 $ref Atom       Atom       text
    Number              int | float         number          Number     float64
    String              str                 string          String     utf8
    Bool                bool                boolean         Boolean    bool
    NoneType            None                null            Atom       text
    SpaceType           Space               $ref Atom       Atom       text
    Atom Symbol         the atom classes    $ref Atom       Atom       text
    Variable Expression
    Grounded

A fifth column names the `metta.testing` strategy that draws values of each
type, so `cases()` over a typed signature reads the same table every other
projection does. Three rows draw nothing: `Bool`, `NoneType` and `SpaceType`
have no strategy of their own, and a signature naming one is told so there.

The rows are `_type_annotations.py`'s forward table read backwards, so a type
that gains a Python spelling gains the other three in the same edit
[source: extensions/python/metta/_catalog/annotations.py:77,
_METATYPE_NAMES; commit=WORKTREE].

Assumes:
  - the caller has already reduced a type ATOM to this table's key where it can:
    an arrow, a `(Literal ...)` and a type variable are the caller's own reading
    (`_stubs.py` renders all three) and reach the fallback column here
Guarantees:
  - host argument delivery comes from the type table's delivery column;
    optional atom alternatives retain atoms, while callbacks and containers
    remain host values [tested:
    test_argument_delivery_follows_the_outer_projected_type,
    test_argument_delivery_reads_the_shared_projection_table; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - WIRE_TAGS is the engine's own `(wire-tag ...)` rows filtered to the term
    class, in the catalog's order, so this and the OpenAPI `Atom` schema read
    one grammar rather than two tuples
    [tested: test_the_wire_tag_table_is_the_engines_own; commit=7f9c810e5f4a2023ad98de34e848667dd72bc4a7]
  - a type outside the table projects to the Atom column of every target, which
    every value can be spelled in: canonical MeTTa text for Arrow, the recursive
    `Atom` schema for JSON, the `Atom` scalar for GraphQL
    [tested: test_every_row_projects_into_all_four_targets; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - `Number` takes a GraphQL scalar of its own rather than `Float`, because
    GraphQL's `Int` is 32-bit and its `Float` is a double while MeTTa's `Number`
    is exact at any width, the reason Hasura and PostGraphile give Postgres
    `bigint` and `numeric` custom scalars
    [tested: test_number_is_a_scalar_of_its_own; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - `column_types` answers one declared type per query column, `%Undefined%`
    where the served space declares nothing, so a projection's schema is the
    space's own promise rather than a guess from the first rows
    [tested: test_column_types_read_the_declared_arrow,
    test_an_undeclared_head_leaves_every_column_undefined; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import ast
from typing import Final, NamedTuple

from metta._atoms.factories import Atom, Expression, Symbol, Variable
from metta._catalog.arrow import BOOL, FLOAT64, TEXT, UTF8
from metta.vocabularies import WIRE_TAGS as _WIRE_TAGS
from metta.vocabularies import ArgumentDelivery, WireClass

#: Where an OpenAPI document keeps the recursive atom schema, and what every
#: type outside the three scalar rows points at.
ATOM_REF: Final = "#/components/schemas/Atom"

#: The GraphQL scalar every atom is spelled with, and the one `Number` needs
#: because no built-in scalar carries a MeTTa number exactly.
ATOM_SCALAR: Final = "Atom"
NUMBER_SCALAR: Final = "Number"

#: The name of the MeTTa type a projection uses when nothing declares one.
UNDEFINED: Final = "%Undefined%"

#: Every tag that is part of an ATOM, in the catalog's own order, which is the
#: order the decoder tries them in. Read from the engine's `(wire-tag ...)`
#: rows rather than written out, so an OpenAPI document's `Atom` schema, the
#: shim's decoder and this cannot drift; the frame and reply tags are in the
#: same table and deliberately not here, because neither nests inside an atom.
WIRE_TAGS: Final = tuple(
    tag for tag, row in _WIRE_TAGS.items() if row.kind is WireClass.term
)


class TypeRow(NamedTuple):
    """One MeTTa type, spelled for each target that has to carry its values.

    `json` is the JSON Schema `type` keyword's value, or None for a type whose
    values cross as whole atoms and whose schema is therefore the recursive
    `Atom` reference. `arrow` is one of `_arrow`'s kind constants.

    `strategy` is the fifth target: the name of the `metta.testing` factory
    that DRAWS values of this type, or None for a type nothing draws. It is a
    name rather than the factory because this module is the base layer and the
    strategies need Hypothesis, exactly as `python` is the annotation's source
    text rather than the class; `metta.testing` resolves it against itself and
    a name that does not resolve is a refusal there.
    """

    metta: str
    python: str
    json: str | None
    graphql: str
    arrow: str
    strategy: str | None = None
    delivery: ArgumentDelivery = ArgumentDelivery.values


#: The table. One row per MeTTa type, one column per target.
TABLE: Final[dict[str, TypeRow]] = {
    row.metta: row
    for row in (
        TypeRow(UNDEFINED, "Any", None, ATOM_SCALAR, TEXT, "ground_atoms"),
        # float64 rather than int64: a declared Number column holds integers and
        # floats alike and float64 is the one Arrow type covering both. The
        # `atom` column beside it carries the exact value as canonical text, so
        # the widening loses nothing from the stream.
        TypeRow("Number", "int | float", "number", NUMBER_SCALAR, FLOAT64, "numbers"),
        TypeRow("String", "str", "string", "String", UTF8, "texts"),
        TypeRow("Bool", "bool", "boolean", "Boolean", BOOL),
        TypeRow("NoneType", "None", "null", ATOM_SCALAR, TEXT),
        TypeRow("SpaceType", "Space", None, ATOM_SCALAR, TEXT, delivery=ArgumentDelivery.atoms),
        TypeRow("Atom", "Atom", None, ATOM_SCALAR, TEXT, "atoms", ArgumentDelivery.atoms),
        TypeRow("Symbol", "Symbol", None, ATOM_SCALAR, TEXT, "symbols", ArgumentDelivery.atoms),
        TypeRow("Variable", "Variable", None, ATOM_SCALAR, TEXT, "variables", ArgumentDelivery.atoms),
        TypeRow("Expression", "Expression", None, ATOM_SCALAR, TEXT, "expressions", ArgumentDelivery.atoms),
        TypeRow("Grounded", "Grounded", None, ATOM_SCALAR, TEXT, "grounded", ArgumentDelivery.atoms),
    )
}

#: The Python column alone, which is what a stub renders from.
PYTHON: Final[dict[str, str]] = {name: row.python for name, row in TABLE.items()}

#: The strategy column alone, which is what `metta.testing` resolves against
#: its own module. A row that draws nothing is absent rather than None, so a
#: consumer's membership test IS the question "can this type be drawn".
STRATEGIES: Final[dict[str, str]] = {
    name: row.strategy for name, row in TABLE.items() if row.strategy
}


def row_for(atom: Atom) -> TypeRow:
    """The table row one MeTTa type atom projects through.

    A type this table does not name -- an imported type, a container, an arrow
    in a value position -- takes the `%Undefined%` row, whose every column is
    the Atom column: a value of it crosses whole rather than as a scalar.
    """
    if isinstance(atom, Symbol):
        return TABLE.get(str(atom), TABLE[UNDEFINED])
    return TABLE[UNDEFINED]


def json_schema(atom: Atom) -> dict[str, str]:
    """One MeTTa type as the JSON Schema 2020-12 fragment naming its values.

    The three scalar rows carry their own keyword; everything else is a
    reference to the recursive `Atom` schema an OpenAPI document defines once.
    """
    row = row_for(atom)
    return {"type": row.json} if row.json is not None else {"$ref": ATOM_REF}


def graphql_type(atom: Atom) -> str:
    """One MeTTa type as the GraphQL SDL type a field carrying it declares."""
    return row_for(atom).graphql


def arrow_kind(atom: Atom) -> str:
    """One MeTTa type as the `_arrow` kind a column carrying it is produced at."""
    return row_for(atom).arrow


def arrows_of(rows: _collections_abc.Iterable) -> dict[str, Expression]:
    """The first declared arrow of each head, by name, from declaration rows.

    A head declared twice is an overload family and the projections here take
    its FIRST arrow, which is the one the space wrote first: a JSON Schema
    argument list, a GraphQL field and an Arrow column each have one shape, and
    picking the first is the same choice `inspect.signature` makes for the
    engine function.
    """
    arrows: dict[str, Expression] = {}
    for row in rows:
        declared = row.arrows
        if declared and row.name not in arrows:
            arrows[row.name] = declared[0]
    return arrows


def argument_types(arrow: Expression) -> tuple[Atom, ...]:
    """The argument types of `(-> A B R)`, which is every child but the result."""
    parts = arrow.children[1:]
    return tuple(parts[:-1]) if parts else ()


def result_type(arrow: Expression) -> Atom:
    """The result type of `(-> A B R)`, or `%Undefined%` for the bare arrow."""
    parts = arrow.children[1:]
    return parts[-1] if parts else Symbol(UNDEFINED)


def column_types(
    pattern: Atom,
    columns: _collections_abc.Sequence[str],
    arrows: _collections_abc.Mapping[str, Expression],
) -> tuple[Atom, ...]:
    """One declared MeTTa type per query column, in the columns' own order.

        column_types(S.users(V.id, V.name), ("id", "name"), {"users": arrow})

    A variable sitting at argument position i of a head the space declares takes
    that arrow's i-th argument type; every other column is `%Undefined%`, which
    projects to the Atom column of each target. Nested expressions are walked,
    so `(edge $a (weight $w))` types `$w` from `weight`'s own arrow.

    This is what fixes an Arrow stream's schema before its first batch: the
    space's declaration is a promise about every row, where a kind derived from
    the rows already seen can be contradicted by the next chunk.
    """
    found: dict[str, Atom] = {}
    _walk(pattern, arrows, found)
    undefined = Symbol(UNDEFINED)
    return tuple(found.get(name, undefined) for name in columns)


def _walk(atom: Atom, arrows: _collections_abc.Mapping[str, Expression], found: dict[str, Atom]) -> None:
    """Record the declared type of every variable this term puts in an argument."""
    if not isinstance(atom, Expression) or not atom.children:
        return
    head, *arguments = atom.children
    declared: tuple[Atom, ...] = ()
    if isinstance(head, Symbol):
        arrow = arrows.get(str(head))
        if arrow is not None:
            types = argument_types(arrow)
            # An arrow of another arity says nothing about THIS call's positions,
            # so it types none of them rather than typing a prefix of them.
            declared = types if len(types) == len(arguments) else ()
    for position, argument in enumerate(arguments):
        if isinstance(argument, Variable):
            if declared and argument.name != "_":
                found.setdefault(argument.name, declared[position])
        else:
            _walk(argument, arrows, found)


def host_type(annotation: str, module: str) -> Atom:
    """Project a host annotation through this table and explicit host types.

    Scalar and atom names use TABLE. Containers, unions, literals and named
    host classes retain their structure and declaring scope instead of
    claiming that an unknown host class is an ordinary MeTTa Atom.
    """
    from metta._atoms.factories import Grounded  # noqa: PLC0415  -- string literal values

    def project(node: ast.AST) -> Atom:
        if isinstance(node, ast.Constant):
            if node.value is None:
                return Symbol("NoneType")
            if node.value is Ellipsis:
                return Symbol("...")
            if isinstance(node.value, str):
                return project(ast.parse(node.value, mode="eval").body)
            return Grounded(node.value)
        if isinstance(node, ast.Name):
            for row in TABLE.values():
                if node.id == row.python or node.id in row.python.split(" | "):
                    return Symbol(row.metta)
            return Expression([Symbol("host-type"), Symbol(module), Symbol(node.id)])
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return Expression([Symbol("host-union"), Expression([project(node.left), project(node.right)])])
        if isinstance(node, ast.Subscript):
            items = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            if isinstance(node.value, ast.Name) and node.value.id == "Literal":
                values = [Grounded(item.value) if isinstance(item, ast.Constant) else project(item) for item in items]
                return Expression([Symbol("host-literal"), Expression(values)])
            return Expression([Symbol("host-apply"), project(node.value), Expression([project(item) for item in items])])
        if isinstance(node, (ast.List, ast.Tuple)):
            return Expression([project(item) for item in node.elts])
        if isinstance(node, ast.Attribute):
            return Expression([Symbol("host-type"), Symbol(module), Symbol(ast.unparse(node))])
        message = f"unsupported Python door type expression: {ast.unparse(node)}"
        raise TypeError(message)

    return project(ast.parse(annotation, mode="eval").body)


def host_delivery(type_atom: Atom) -> ArgumentDelivery:
    """Read the outer argument's delivery from its projected type.

    Optional atom alternatives retain atom delivery. A callback or container
    remains a host value even when its parameters mention atoms. This follows
    the union and Annotated rules used by _ops._receives_atom.
    """
    alternatives = None
    if isinstance(type_atom, Expression) and type_atom.children:
        if type_atom.head == Symbol("host-union"):
            alternatives = type_atom.children[1].children
        elif type_atom.head == Symbol("host-apply"):
            constructor, parameters = type_atom.children[1:]
            if isinstance(constructor, Expression) and constructor.head == Symbol("host-type"):
                name = str(constructor.children[-1]).rpartition(".")[2]
                if name == "Annotated":
                    return host_delivery(parameters.children[0])
                # policy-inventory-exempt: mechanism-internal; reason=typing's two spellings of a union of alternatives, beside the PEP 604 form the host-union head already carries; evidence=extensions/python/metta/_catalog/types.py:host_delivery
                if name in {"Optional", "Union"}:
                    alternatives = parameters.children
    if alternatives is not None:
        members = [member for member in alternatives if member != Symbol("NoneType")]
        return (ArgumentDelivery.atoms if members and all(
            host_delivery(member) is ArgumentDelivery.atoms for member in members
        ) else ArgumentDelivery.values)
    return row_for(type_atom).delivery

# Resolve annotations after definitions so peer imports can finish.
import collections.abc as _collections_abc  # noqa: E402 -- deferred annotation bindings
