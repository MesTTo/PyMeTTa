"""Purpose: hold the one type table to every target it projects into.

A MeTTa type is spelled four other ways, and the whole reason `_projection.py`
exists is that the four cannot be allowed to disagree. These scenarios are the
questions each column has to answer, asked of the table rather than of any one
surface, plus the two rules that decide the awkward rows.

Guarantees:
  - every row projects into all four targets, so a row added without a column
    fails here rather than at a consumer [tested:
    test_every_row_projects_into_all_four_targets; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - the Python column IS the stub's scalar table, so the two cannot drift
    [tested: test_the_stub_reads_the_tables_python_column; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from metta import S, V
from metta._atoms.factories import Expression, Symbol
from metta._catalog.arrow import BOOL, FLOAT64, TEXT, UTF8
from metta._catalog.types import (
    ATOM_REF,
    ATOM_SCALAR,
    NUMBER_SCALAR,
    PYTHON,
    TABLE,
    UNDEFINED,
    arrow_kind,
    arrows_of,
    column_types,
    graphql_type,
    json_schema,
    row_for,
)


def test_every_row_projects_into_all_four_targets():
    """A row with a missing column is a target that cannot carry that type.

    The table is the one place the four surfaces agree, so a row is complete or
    it is a hole one of them will fall into at a consumer's request instead of
    here.
    """
    kinds = {BOOL, FLOAT64, TEXT, UTF8}
    for name, row in TABLE.items():
        assert row.metta == name, f"{name} is filed under another name"
        assert row.python, f"{name} has no Python spelling"
        assert row.graphql, f"{name} has no GraphQL spelling"
        assert row.arrow in kinds, f"{name} projects to a kind Arrow does not have"
        assert row.json is None or isinstance(row.json, str)


def test_a_type_outside_the_table_takes_the_atom_column():
    """Every value can be spelled as an atom, so an unknown type is not a hole.

    An imported type, a container type and an arrow in a value position are all
    types this table does not name, and each still has to reach a JSON Schema, a
    GraphQL field and an Arrow column.
    """
    for atom in (S.Point, S.List(S.Number), Expression([Symbol("->"), S.Number, S.Number])):
        assert row_for(atom).metta == UNDEFINED
        assert json_schema(atom) == {"$ref": ATOM_REF}
        assert graphql_type(atom) == ATOM_SCALAR
        assert arrow_kind(atom) == TEXT


def test_number_is_a_scalar_of_its_own():
    """GraphQL's built-in numbers cannot carry a MeTTa Number.

    `Int` is 32-bit signed and `Float` is an IEEE-754 double, while MeTTa's
    numbers are exact at any width; a custom scalar is what Hasura and
    PostGraphile give Postgres bigint and numeric for the same reason.
    """
    assert graphql_type(S.Number) == NUMBER_SCALAR
    assert graphql_type(S.String) == "String"
    assert graphql_type(S.Bool) == "Boolean"
    assert json_schema(S.Number) == {"type": "number"}


def test_the_stub_reads_the_tables_python_column():
    """One table, two readers: the stub renderer takes its scalars from here."""
    import metta._declare.stubs as _stubs

    assert _stubs._SCALARS is PYTHON
    assert PYTHON["Number"] == "int | float"


def test_column_types_read_the_declared_arrow():
    """A pattern's variables take their types from the head the space declares."""
    arrows = arrows_of(
        [
            _declaration("users", "(-> Number String Bool)"),
            _declaration("weight", "(-> Number Number)"),
        ]
    )
    types = column_types(S.users(V.id, V.name), ("id", "name"), arrows)
    assert [str(kind) for kind in types] == ["Number", "String"]


def test_a_variable_inside_a_nested_call_takes_that_calls_own_type():
    """`(edge $a (weight $w))` types `$w` from `weight`, not from `edge`."""
    arrows = arrows_of(
        [
            _declaration("edge", "(-> Number Number Bool)"),
            _declaration("weight", "(-> Number Number)"),
        ]
    )
    types = column_types(S.edge(V.a, S.weight(V.w)), ("a", "w"), arrows)
    assert [str(kind) for kind in types] == ["Number", "Number"]


def test_an_undeclared_head_leaves_every_column_undefined():
    """No declaration is no promise, and the projection says so rather than guessing."""
    types = column_types(S.nothing(V.a, V.b), ("a", "b"), {})
    assert [str(kind) for kind in types] == [UNDEFINED, UNDEFINED]
    assert arrow_kind(types[0]) == TEXT


def test_an_arrow_of_another_arity_types_no_position():
    """A two-argument declaration says nothing about a three-argument call.

    Typing a prefix would put the second column's type on a call whose shape the
    declaration does not describe, which is a guess wearing a promise's clothes.
    """
    arrows = arrows_of([_declaration("users", "(-> Number String Bool)")])
    types = column_types(S.users(V.a, V.b, V.c, V.d), ("a", "b", "c", "d"), arrows)
    assert {str(kind) for kind in types} == {UNDEFINED}


def _declaration(name, arrow):
    """One declaration row, as `_declarations` answers it."""
    from metta._atoms.factories import parse
    from metta._catalog.declarations import Declaration

    return Declaration(name=name, types=(parse(arrow),))
