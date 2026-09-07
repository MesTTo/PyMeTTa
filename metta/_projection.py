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

The rows are `_type_annotations.py`'s forward table read backwards, so a type
that gains a Python spelling gains the other three in the same edit
[source: extensions/python/metta/_type_annotations.py:_TYPE_NAMES,
_METATYPE_NAMES; commit=6c4d1f2b23e2b6b9d54c7ff88ba30ee5f1c6ba59].

Assumes:
  - the caller has already reduced a type ATOM to this table's key where it can:
    an arrow, a `(Literal ...)` and a type variable are the caller's own reading
    (`_stubs.py` renders all three) and reach the fallback column here
Guarantees:
  - a type outside the table projects to the Atom column of every target, which
    every value can be spelled in: canonical MeTTa text for Arrow, the recursive
    `Atom` schema for JSON, the `Atom` scalar for GraphQL
    [tested: test_every_row_projects_into_all_four_targets; commit=WORKTREE]
  - `Number` takes a GraphQL scalar of its own rather than `Float`, because
    GraphQL's `Int` is 32-bit and its `Float` is a double while MeTTa's `Number`
    is exact at any width, the reason Hasura and PostGraphile give Postgres
    `bigint` and `numeric` custom scalars
    [tested: test_number_is_a_scalar_of_its_own; commit=WORKTREE]
  - `column_types` answers one declared type per query column, `%Undefined%`
    where the served space declares nothing, so a projection's schema is the
    space's own promise rather than a guess from the first rows
    [tested: test_column_types_read_the_declared_arrow,
    test_an_undeclared_head_leaves_every_column_undefined; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NamedTuple

from ._arrow import BOOL, FLOAT64, TEXT, UTF8
from .atoms import Atom, Expression, Symbol, Variable

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

#: Where an OpenAPI document keeps the recursive atom schema, and what every
#: type outside the three scalar rows points at.
ATOM_REF: Final = "#/components/schemas/Atom"

#: The GraphQL scalar every atom is spelled with, and the one `Number` needs
#: because no built-in scalar carries a MeTTa number exactly.
ATOM_SCALAR: Final = "Atom"
NUMBER_SCALAR: Final = "Number"

#: The name of the MeTTa type a projection uses when nothing declares one.
UNDEFINED: Final = "%Undefined%"

#: Every tag the wire decoder accepts, in the order the decoder tries them, so
#: an OpenAPI document's `Atom` schema and the decoder cannot drift
#: [source: extensions/python/metta/_atom_wire.py:_leaf_from_wire, _from_wire;
#: commit=WORKTREE].
WIRE_TAGS: Final = ("s", "g", "n", "b", "v", "e", "p", "o", "h")


class TypeRow(NamedTuple):
    """One MeTTa type, spelled for each target that has to carry its values.

    `json` is the JSON Schema `type` keyword's value, or None for a type whose
    values cross as whole atoms and whose schema is therefore the recursive
    `Atom` reference. `arrow` is one of `_arrow`'s kind constants.
    """

    metta: str
    python: str
    json: str | None
    graphql: str
    arrow: str


#: The table. One row per MeTTa type, one column per target.
TABLE: Final[dict[str, TypeRow]] = {
    row.metta: row
    for row in (
        TypeRow(UNDEFINED, "Any", None, ATOM_SCALAR, TEXT),
        # float64 rather than int64: a declared Number column holds integers and
        # floats alike and float64 is the one Arrow type covering both. The
        # `atom` column beside it carries the exact value as canonical text, so
        # the widening loses nothing from the stream.
        TypeRow("Number", "int | float", "number", NUMBER_SCALAR, FLOAT64),
        TypeRow("String", "str", "string", "String", UTF8),
        TypeRow("Bool", "bool", "boolean", "Boolean", BOOL),
        TypeRow("NoneType", "None", "null", ATOM_SCALAR, TEXT),
        TypeRow("SpaceType", "Space", None, ATOM_SCALAR, TEXT),
        TypeRow("Atom", "Atom", None, ATOM_SCALAR, TEXT),
        TypeRow("Symbol", "Symbol", None, ATOM_SCALAR, TEXT),
        TypeRow("Variable", "Variable", None, ATOM_SCALAR, TEXT),
        TypeRow("Expression", "Expression", None, ATOM_SCALAR, TEXT),
        TypeRow("Grounded", "Grounded", None, ATOM_SCALAR, TEXT),
    )
}

#: The Python column alone, which is what a stub renders from.
PYTHON: Final[dict[str, str]] = {name: row.python for name, row in TABLE.items()}


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


def arrows_of(rows: Iterable) -> dict[str, Expression]:
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
    columns: Sequence[str],
    arrows: Mapping[str, Expression],
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


def _walk(atom: Atom, arrows: Mapping[str, Expression], found: dict[str, Atom]) -> None:
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
