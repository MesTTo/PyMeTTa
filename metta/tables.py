"""Purpose: derive a whole table-backed space provider from MeTTa bridge
declarations, so the contract is rewrite rules and both directions of
the boundary fall out of matching them. The module is metta.tables
because a subscription bridge is already the standing bridge RULE between two
spaces (metta.subscribe.bridge); the two are the same idea at two
boundaries, a declared correspondence the engine keeps live.

    (bridge (edge $a $b) (row edges (a $a) (b $b)))

One pattern pair relates an atom shape to a table shape. Matched
left-to-right a query becomes WHERE and an add becomes INSERT; matched
right-to-left a row becomes the atom. A provider takes a SCHEMA, any
number of declarations: a schema is a set of rewrite rules the way a
function is a set of equations, so a query answers the union of every
shape it admits, exactly as overlapping equations answer together. The
one place the equation reading is deliberately NOT copied is add: a
ground atom two shapes admit is refused naming both, because storing
it twice would invent an occurrence, and a multiset must not.

This is the bidirectional-transformations literature's third approach,
writing the consistency relation and deriving both transformations
[source: the GRACE report,
gsd.uwaterloo.ca/sites/default/files/GRACE-report-ICMT09.pdf; TRIP2 did
it with Prolog rules, Wadler's views are the in/out pair], and the lens
round-trip laws are what check_space_provider verifies against the
derived claims.

Declarations may live in &metta, ctx-scoped like every other contract
atom: `declare(m, "&crm", "(bridge (edge $a $b) (row edges ...))")`
writes `(bridge &crm (edge $a $b) (row edges ...))` there, MeTTa source
can add the same atom itself, and `TableBridge.from_context(m, "&crm",
connection)` reads every one back, so a program carries its schema as
knowledge and the attach is one line.

Guarantees:
  - tagged atom cells preserve explicit s and p species instead of applying
    process-local engine provenance [tested:
    test_space_handles_are_term_operands_and_round_trip; commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - a database row becomes an atom from its typed cell values; plain text is
    always a symbol, NULL is Grounded(None), and a structured value is one tagged
    TEXT cell carrying the atom wire rather than the source parser [tested:
    test_a_row_value_becomes_an_atom_without_being_reparsed;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a cell MeTTa wrote reads back as the atom it wrote, whatever the driver
    and the image catalog do to the database's own values: _is_atom_cell
    keeps the tag in the text domain, out of reach of a row_factory that
    adapts binary cells, and _ImageCodec answers it before any image
    [tested: test_a_nonground_compound_downgrades_and_removal_still_unifies;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the whole pattern family is filtered exactly where SQL can express
    it: ground positions become comparisons, a repeated variable becomes
    the equality it demands (column to column, or column to the declared
    head literal), and a variable head constrains nothing [tested
    test_the_kit_certifies_the_pushdown_claim]
  - a nonground compound below a column variable downgrades pushdown to
    inexact instead of overclaiming, and removal falls back to
    unification so it still means what remove-atom means everywhere
    [tested test_a_nonground_compound_downgrades_and_removal_still_unifies]
  - writes are refused unless the atom grounds every column, because a
    row of NULLs standing for variables would silently weaken removal
    [tested test_a_nonground_add_is_refused]
  - an atom every shape refuses, or two shapes admit, is refused naming
    the shapes [tested test_an_ambiguous_add_is_refused_naming_both]
  - TableBridge.from_context applies `(image <ctx> <Type> <setting>)` to
    each of the database's own row values before it crosses, keeping opaque
    objects as handles and projecting transparent objects [tested:
    test_an_opaque_blob_column_is_reached_by_a_lazy_path_without_crossing;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - fallback row deletion binds only the removal pattern after public
    ``unify`` becomes symmetric [tested:
    test_a_nonground_compound_downgrades_and_removal_still_unifies;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - table cells preserve portable space references and refuse native handles,
    whose registry identity cannot outlive its process [tested:
    test_table_storage_refuses_native_handles_before_writing,
    test_table_storage_preserves_portable_space_references;
    commit=9fad0bf6670061a26b1a17d3f566613b7d4d080c]
  - add() reads an Arrow stream one record batch at a time and produces the
    atoms the source's own row door would have [tested:
    test_a_duckdb_relation_loads_through_the_arrow_door,
    test_both_inward_doors_build_the_same_atoms; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - a bridge streams its declared columns to any Arrow consumer, and refuses
    when its shapes do not agree on one column list [tested:
    test_a_bridge_streams_its_sqlite_rows,
    test_a_bridge_over_two_relations_refuses_one_schema; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - the stream reads the connection inside the call, so a consumer that reads
    the capsule on its own thread needs a connection that permits it
    [tested: test_a_bridge_streams_its_sqlite_rows; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - `df.metta` is installed for a frame library already imported, without
    importing one [tested: test_the_frame_accessors_install_for_imported_libraries;
    commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - a head registered as a SQL function answers NULL for no answer and
    refuses several [tested: test_a_head_is_a_duckdb_scalar_function,
    test_a_head_is_a_sqlite_scalar_function; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
Decides:
  - declarations are trusted code, not user data: table and column
    names are interpolated into SQL, so a bridge declaration belongs in
    the program the way a schema does
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import inspect
import json
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any, Protocol, cast

from metta import seam
from metta._atoms.designation import SpaceLike
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _encode,
    _is_ground,
    _match,
    ground,
    substitute,
)
from metta._atoms.wire import _atom_from_wire
from metta.convert import auto_image, project
from metta.foreign import SpaceProvider

_ATOM_CELL_PREFIX = "\x00metta-atom-v1\x00"
_NO_GROUNDED_VALUE = object()


def _row_values(row: Any, keys: list[Any]) -> Any:
    """Read a record by values while fixing one stable column order."""
    if not isinstance(row, Mapping):
        return row
    if not keys:
        keys.extend(row.keys())
    elif list(row.keys()) != keys:
        msg = (
            "every record must carry the same keys in the same order; "
            f"expected {keys}, got {list(row.keys())}"
        )
        raise ValueError(msg)
    return row.values()


def add(space: SpaceLike, head: Any, data: Any) -> int:
    """Add a tabular source to a space as ``(head column...)`` facts.

    space may be a context or a space.

    The source may offer rows its own way (``iter_rows()`` for polars,
    ``itertuples()`` for pandas, a mapping of columns, any iterable of rows)
    or speak the Arrow PyCapsule Interface, which is how a DuckDB relation, a
    pyarrow Table, a Parquet reader or an Ibis expression hands over rows
    without a row-at-a-time Python door. A source with both keeps its own:
    the two produce identical atoms, and the row door is the faster of them
    [measured 2026-09-06: 10,000 rows, polars 14.07 ms through iter_rows
    against 14.36 ms through the stream, pandas 20.39 ms against 25.11 ms].

    An Arrow source is written one record batch at a time, so a reader larger
    than memory loads, and the writes are one transaction each; wrap the call
    in ``m.transaction(...)`` to make the whole load one.
    """
    home = space.self
    head_atom = head if isinstance(head, Atom) else Symbol(str(head))
    accessors()
    keys: list[Any] = []
    if hasattr(data, "iter_rows"):
        rows = data.iter_rows()
    elif hasattr(data, "itertuples"):
        rows = data.itertuples(index=False)
    elif isinstance(data, Mapping):
        rows = zip(*data.values(), strict=True)
    elif hasattr(data, "__arrow_c_stream__"):
        return _add_arrow_stream(home, head_atom, data)
    elif isinstance(data, Iterable):
        rows = iter(data)
    else:
        msg = (
            "tables.add reads iter_rows(), itertuples(), a mapping of "
            f"columns, __arrow_c_stream__(), or an iterable of rows; "
            f"{type(data).__name__} offers none"
        )
        raise TypeError(msg)
    facts = [
        Expression([head_atom, *(_encode(value) for value in _row_values(row, keys))])
        for row in rows
    ]
    home.add(*facts)
    return len(facts)


def _add_arrow_stream(space: Any, head_atom: Atom, data: Any) -> int:
    """Write one Arrow stream's record batches as facts, a batch per write."""
    from metta._catalog.arrow import read_batches  # noqa: PLC0415  -- the optional Arrow extra

    _names, batches = read_batches(data)
    written = 0
    for batch in batches:
        facts = [
            Expression([head_atom, *(_encode(value) for value in row)]) for row in batch
        ]
        if facts:
            space.add(*facts)
            written += len(facts)
    return written


def _contains_native_handle(wire: Any) -> bool:
    """Whether one well-formed atom wire contains an h-tagged reference."""
    pending = [wire]
    while pending:
        term = pending.pop()
        if not isinstance(term, (list, tuple)) or not term:
            continue
        if term[0] == "h":
            return True
        if term[0] == "e" and len(term) == 2 and isinstance(term[1], (list, tuple)):
            pending.extend(term[1])
    return False


def _encoded_cell(atom: Atom) -> str:
    """A structured atom in one tagged text cell, never MeTTa source."""
    wire = atom.to_wire()
    # Capability protocols require an explicit persistent token before a live
    # reference may be saved; a registry id alone is not such a token:
    # https://github.com/capnproto/capnproto/blob/3a82de9b39736a2625f03c93b2b7c50642dd5b25/doc/rpc.md#L219-L225
    if _contains_native_handle(wire):
        msg = (
            "a native handle has process-local identity; store a stable value "
            "read through the extension's accessors instead"
        )
        raise ValueError(msg)
    try:
        payload = json.dumps(
            wire,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        msg = (
            f"{atom!r} has no stable table-cell representation; table rows can "
            "carry symbols, primitive grounded values, and expressions made from them"
        )
        raise ValueError(msg) from exc
    return _ATOM_CELL_PREFIX + payload


def _is_atom_cell(value: Any) -> bool:
    """Whether MeTTa wrote this cell itself, or the database holds it.

    The tag stays in the text domain because a driver is free to adapt
    binary values on the way out, as sqlite3's row_factory and psycopg2's
    memoryview both do, and an adapted cell is no longer recognisable as
    MeTTa's own. A NUL cannot occur in text a column legitimately carries,
    so the tag is unambiguous without leaving that domain, and SQLite
    compares a NUL-bearing TEXT cell byte for byte, which is what lets
    remove() delete one by equality.
    """
    return isinstance(value, str) and value.startswith(_ATOM_CELL_PREFIX)


def _atom_from_cell(value: Any) -> Atom:
    """Map one driver value to its atom; text is data, never source code."""
    if _is_atom_cell(value):
        try:
            return _atom_from_wire(json.loads(value[len(_ATOM_CELL_PREFIX) :]))
        except (TypeError, ValueError) as exc:
            msg = "a table cell starts with MeTTa's atom tag but its payload is corrupt"
            raise ValueError(msg) from exc
    if isinstance(value, str):
        return Symbol(value)
    return _encode(value)


def _cell_from_atom(atom: Atom) -> Any:
    """Map an atom to one DB-API parameter that `_atom_from_cell` inverts."""
    if isinstance(atom, Symbol):
        return atom.name
    if isinstance(atom, Grounded):
        value = getattr(atom, "value", _NO_GROUNDED_VALUE)
        if value is _NO_GROUNDED_VALUE:
            return _encoded_cell(atom)
        if value is None or type(value) in (int, float):
            return value
        if type(value) in (bool, str):
            return _encoded_cell(atom)
        msg = (
            f"{atom!r} is an opaque grounded value; a table cell needs a stable "
            "database representation"
        )
        raise ValueError(msg)
    if isinstance(atom, Expression):
        return _encoded_cell(atom)
    msg = f"{atom!r} cannot be stored in one table column"
    raise ValueError(msg)


def _value_constraint(
    where: list[str], arguments: list[Any], column: str, value: Any
) -> None:
    """Append SQL's explicit NULL comparison or a parameter comparison."""
    if value is None:
        where.append(f"{column} IS NULL")
    else:
        where.append(f"{column} = ?")
        arguments.append(value)


class Executes(Protocol):
    """The slice of a DB-API connection the bridge stands on."""

    def execute(self, sql: str, parameters: Any = ..., /) -> Any: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract

    def commit(self) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract

    def rollback(self) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


def _declaration_error(declaration: Any) -> ValueError:
    return ValueError(
        f"a bridge declaration is (bridge <atom-shape> <row-shape>), got {declaration}"
    )


class _Shape:
    """One declaration's derivation: shape atom, table, columns, and the
    constraint reading of any pattern against them.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, declaration: Atom) -> None:
        if not isinstance(declaration, Expression) or len(declaration.children) != 3:
            raise _declaration_error(declaration)
        head, atom_shape, row_shape = declaration.children
        if str(head) != "bridge" or not isinstance(atom_shape, Expression) or not isinstance(row_shape, Expression):
            raise _declaration_error(declaration)
        self.shape = atom_shape
        table, *columns = row_shape.children[1:]
        self.table = str(table)
        self.columns: dict[str, str] = {}
        for pair in columns:
            if not isinstance(pair, Expression) or len(pair.children) != 2:
                msg = f"a row column is (name $var), got {pair}"
                raise ValueError(msg)
            column, variable = pair.children
            if not isinstance(variable, Variable):
                msg = f"a row column binds a variable, got {pair}"
                raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
            self.columns[str(variable)] = str(column)
        for child in atom_shape.children:
            if isinstance(child, Variable) and str(child) not in self.columns:
                msg = f"the atom shape's {child} has no column in {row_shape}"
                raise ValueError(msg)

    def constraints(self, pattern: Atom) -> tuple[list[str], list[Any], bool] | None:
        """WHERE fragments from matching the pattern against this shape.

        Answers (where, arguments, exact), or None when the shapes cannot
        match and no row is a candidate. A pattern variable binds the
        position it first met, a declared literal or a column, and every
        later occurrence becomes the equality the pattern itself demands;
        the kit's repeated-variable folds probe exactly this.
        """
        if not isinstance(pattern, Expression) or len(pattern.children) != len(self.shape.children):
            return None
        where: list[str] = []
        arguments: list[Any] = []
        exact = True
        seen: dict[str, tuple[str, Any]] = {}
        for shaped, given in zip(self.shape.children, pattern.children, strict=True):
            if not isinstance(shaped, Variable):
                constant = shaped
                if isinstance(given, Variable):
                    name = str(given)
                    prior = seen.get(name)
                    if prior is None:
                        seen[name] = ("value", constant)
                    elif prior[0] == "value":
                        if prior[1] != constant:
                            return None
                    else:
                        _value_constraint(
                            where,
                            arguments,
                            prior[1],
                            _cell_from_atom(constant),
                        )
                    continue
                if given != constant:
                    return None
                continue
            column = self.columns[str(shaped)]
            if isinstance(given, Variable):
                name = str(given)
                prior = seen.get(name)
                if prior is None:
                    seen[name] = ("column", column)
                elif prior[0] == "column":
                    where.append(f"{column} = {prior[1]}")
                else:
                    _value_constraint(
                        where,
                        arguments,
                        column,
                        _cell_from_atom(prior[1]),
                    )
                continue
            if isinstance(given, Expression) and not _is_ground(given):
                exact = False
                continue
            _value_constraint(
                where,
                arguments,
                column,
                _cell_from_atom(given),
            )
        return where, arguments, exact

    def column_names(self) -> list[str]:
        """The table columns this shape selects, in the atom shape's order."""
        return [
            self.columns[str(child)]
            for child in self.shape.children
            if isinstance(child, Variable)
        ]

    def column_list(self) -> str:
        return ", ".join(self.column_names())

    def values(self, atom: Expression) -> list[Any]:
        return [
            _cell_from_atom(given)
            for shaped, given in zip(self.shape.children, atom.children, strict=True)
            if isinstance(shaped, Variable)
        ]

    def atom(self, cell_atom: Callable[[Any], Atom], row: Any) -> Atom:
        values = iter(row)
        bindings = {
            child.name: cell_atom(next(values))
            for child in self.shape.children
            if isinstance(child, Variable)
        }
        return substitute(self.shape, bindings)


class _ImageCodec:
    """Turn DB-API cells into atoms under one attached context's catalog."""

    def __init__(self, settings: dict[str, str] | None) -> None:
        self._settings = settings or {}
        invalid = set(self._settings.values()) - {
            "opaque",
            "transparent",
            "auto",
        }
        if invalid:
            msg = (
                "an image setting is opaque, transparent, or auto, not "
                f"{sorted(invalid)!r}"
            )
            raise ValueError(msg)

    def __call__(self, value: Any) -> Atom:
        if _is_atom_cell(value):
            # An image declares how one of the DATABASE's values crosses, and
            # this cell is MeTTa's own atom in transit, so the tag outranks
            # the catalog: not even a catch-all image may turn a stored atom
            # into a handle and lose the round trip that add() promised.
            return _atom_from_cell(value)
        setting = self._settings.get(type(value).__name__)
        if setting is None:
            setting = self._settings.get("_")
        if setting is None:
            # No image declaration: the P2.4 contract holds, a row value
            # becomes its atom directly and is never re-parsed as text.
            return _atom_from_cell(value)
        if setting == "auto":
            setting = auto_image(value)
        if setting == "opaque":
            return ground(value)
        return project(value).atom


class TableBridge(SpaceProvider):
    """Every provider operation derived from the declarations; nothing in
    here is specific to any table.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        parse: Callable[[str], Atom],
        connection: Executes,
        declarations: Atom | str | Iterable[Atom | str],
        *,
        images: dict[str, str] | None = None,
    ) -> None:
        self._cell_atom = _ImageCodec(images)
        self.connection = connection
        self.executed: list[str] = []
        if isinstance(declarations, (str, Atom)):
            declarations = [declarations]
        self._shapes = [
            _Shape(parse(declared) if isinstance(declared, str) else declared)
            for declared in declarations
        ]
        if not self._shapes:
            msg = "a table bridge needs at least one declaration"
            raise ValueError(msg)

    @classmethod
    def from_context(
        cls,
        m: SpaceLike,
        name: str,
        connection: Executes,
    ) -> TableBridge:
        """The provider for every `(bridge <name> <shape> <row>)` atom in
        &metta, so a schema declared from MeTTa source, or by declare()
        below, becomes a provider in one line.

        m may be a context or a space.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        home = m.self
        (group,) = home.run(
            f"!(collapse (match &metta (bridge {name} $shape $row)"
            f" (bridge $shape $row)))"
        )
        declarations = list(group[0])
        if not declarations:
            msg = f"&metta declares no (bridge {name} ...) schema"
            raise ValueError(msg)
        (image_group,) = home.run(
            f"!(collapse (match &metta (image {name} $type $setting)"
            f" ($type $setting)))"
        )
        images: dict[str, str] = {}
        for pair in image_group[0]:
            if not isinstance(pair, Expression) or len(pair.children) != 2:
                continue
            type_name, setting = map(str, pair.children)
            prior = images.setdefault(type_name, setting)
            if prior != setting:
                msg = (
                    f"{name} declares conflicting images for {type_name}: "
                    f"{prior} and {setting}"
                )
                raise ValueError(msg)
        return cls(home.parse, connection, declarations, images=images)

    # -- the provider surface, all of it derived -----------------------------

    def atoms(self) -> Iterator[Atom]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return (
            shape.atom(self._cell_atom, row)
            for shape in self._shapes
            for row in self._select(shape, [], [])
        )

    def match(self, pattern: Atom, *, limit: int | None = None) -> Iterator[Atom]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        def answers() -> Iterator[Atom]:
            for shape, (where, arguments, _exact) in self._admitting(pattern):
                for row in self._select(shape, where, arguments, limit):
                    yield shape.atom(self._cell_atom, row)

        return answers()

    def pushdown(self, pattern: Atom) -> str:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        admitting = self._admitting(pattern)
        if not admitting:
            return "exact"  # no shape admits it, and nothing is yielded
        return "exact" if all(exact for _s, (_w, _a, exact) in admitting) else "inexact"

    def add(self, atom: Atom) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        fitting = [
            shape
            for shape, _derived in self._admitting(atom)
            if _is_ground(atom)
        ]
        if not fitting:
            msg = (
                f"no declared shape admits {atom} as a ground row; the schema is "
                f"{[str(shape.shape) for shape in self._shapes]}"
            )
            raise ValueError(
                msg
            )
        if len(fitting) > 1:
            msg = (
                f"{atom} is ambiguous: shapes "
                f"{[str(shape.shape) for shape in fitting]} all admit it, and "
                f"storing one atom twice would invent an occurrence"
            )
            raise ValueError(
                msg
            )
        shape = fitting[0]
        holes = ", ".join("?" for _ in shape.columns)
        self.connection.execute(
            f"INSERT INTO {shape.table} ({shape.column_list()})"  # noqa: S608 - identifiers from the trusted declaration  # nosec B608
            f" VALUES ({holes})",
            shape.values(cast(Expression, atom)),
        )

    def remove(self, pattern: Atom) -> bool:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        removed = False
        for shape, (where, arguments, exact) in self._admitting(pattern):
            if exact:
                sql = f"DELETE FROM {shape.table}"  # noqa: S608 - identifiers from the trusted declaration  # nosec B608
                if where:
                    sql += " WHERE " + " AND ".join(where)
                cursor = self.connection.execute(sql, arguments)
                removed = bool(getattr(cursor, "rowcount", 0) > 0) or removed
                continue
            # The one shape SQL cannot filter: match, keep what truly
            # unifies, and delete those exact rows, so removal still means
            # what remove-atom means everywhere.
            doomed = [
                shape.values(atom)
                for row in self._select(shape, where, arguments)
                for atom in (shape.atom(self._cell_atom, row),)
                if isinstance(atom, Expression) and _match(pattern, atom) is not None
            ]
            for values in doomed:
                clauses: list[str] = []
                delete_args: list[Any] = []
                for column, value in zip(
                    shape.columns.values(), values, strict=True
                ):
                    _value_constraint(clauses, delete_args, column, value)
                self.connection.execute(
                    f"DELETE FROM {shape.table} WHERE {' AND '.join(clauses)}",  # noqa: S608 - identifiers from the trusted declaration  # nosec B608
                    delete_args,
                )
            removed = bool(doomed) or removed
        return removed

    def clear(self) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        for table in {shape.table for shape in self._shapes}:
            self.connection.execute(f"DELETE FROM {table}")  # noqa: S608 - identifier from the trusted declaration  # nosec B608

    # -- the rows as an Arrow stream -----------------------------------------

    def _projection(self):
        """Every declared shape's rows as one typed projection.

        The declaration fixes the columns and their order, which is what makes
        one schema possible at all; the Arrow type of each is derived from the
        cells, the same rule every other projection follows, because a bridge
        declaration says which column a variable binds and not what SQL type
        it has. Shapes are read through the provider's own cursor and its
        image catalog, so the stream carries exactly the values `atoms()`
        would have built atoms from.
        """
        from metta._catalog.arrow import Projection  # noqa: PLC0415  -- the one projection

        names = self._shapes[0].column_names()
        for shape in self._shapes[1:]:
            if shape.column_names() != names:
                msg = (
                    f"one Arrow stream carries one schema, and this bridge "
                    f"declares columns {names} for {self._shapes[0].table} and "
                    f"{shape.column_names()} for {shape.table}; stream one "
                    f"relation per bridge, or read atoms() for the union"
                )
                raise ValueError(msg)
        rows = [
            tuple(self._cell_atom(cell) for cell in row)
            for shape in self._shapes
            for row in self._select(shape, [], [])
        ]
        return Projection.of(names, rows)

    def __arrow_c_schema__(self):
        """The declared columns as an "arrow_schema" PyCapsule."""
        from metta._catalog.arrow import (  # noqa: PLC0415 -- the optional Arrow extra
            schema_capsule,
        )

        return schema_capsule(self._projection())

    def __arrow_c_stream__(self, requested_schema=None):
        """This bridge's rows as an "arrow_array_stream" PyCapsule.

            pl.DataFrame(bridge)
            duckdb.sql("select * from bridge")

        The provider declares the capability by having the method, which is
        how the rest of the ecosystem declares one, so a SQL-backed space
        reaches a frame or a query engine without the caller materialising
        atoms.

        The rows are read through the connection INSIDE this call, and a
        consumer may make the call from its own thread: DuckDB's replacement
        scan reads the capsule on a worker. A driver whose connection is
        thread-affine therefore has to permit that. sqlite3's default refuses
        with "SQLite objects created in a thread can only be used in that same
        thread", and `sqlite3.connect(path, check_same_thread=False)` is its
        opt-in; polars and pyarrow read on the calling thread and need
        neither.
        """
        from metta._catalog.arrow import (  # noqa: PLC0415 -- the optional Arrow extra
            stream_capsule,
        )

        return stream_capsule(self._projection(), requested_schema)

    def begin(self) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self.connection.execute("BEGIN")

    def commit(self) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self.connection.commit()

    def rollback(self) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self.connection.rollback()

    # -- shared derivation helpers -------------------------------------------

    def _admitting(self, pattern: Atom) -> list[tuple[_Shape, tuple[list[str], list[str], bool]]]:
        admitting = []
        for shape in self._shapes:
            derived = shape.constraints(pattern)
            if derived is not None:
                admitting.append((shape, derived))
        return admitting

    def _select(
        self,
        shape: _Shape,
        where: list[str],
        arguments: list[Any],
        limit: int | None = None,
    ) -> list[Any]:
        sql = f"SELECT {shape.column_list()} FROM {shape.table}"  # nosec B608 - identifiers from the trusted declaration  # noqa: S608 - identifiers from the trusted declaration  # nosec B608
        if where:
            sql += " WHERE " + " AND ".join(where)
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        self.executed.append(sql)
        return list(self.connection.execute(sql, arguments))


def declare(m: SpaceLike, name: str, declaration: Atom | str) -> Atom:
    """Write one ctx-scoped bridge declaration into &metta, where explain
    and any program can read the schema, and from_context will.

    m may be a context or a space.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    home = m.self
    parsed = home.parse(declaration) if isinstance(declaration, str) else declaration
    if not isinstance(parsed, Expression):
        raise _declaration_error(parsed)
    _Shape(parsed)  # validated before it is stored, the declaration discipline
    _, atom_shape, row_shape = parsed.children
    stored = home.parse(f"(bridge {name} {atom_shape} {row_shape})")
    with home.bind(decl=stored):
        home.run("!(add-atom &metta decl)")
    return stored


# -- the frame libraries' own doors ------------------------------------------

#: `df.metta`, spelled the way each library spells an extension: pandas'
#: registered accessor and polars' registered namespace are the same idea, so
#: one class serves every registered frame library and the row says how that
#: library installs it.
_ACCESSOR = "metta"
_ACCESSED: set[str] = set()


class _FrameDoor:
    """`df.metta`: this library's face on any registered frame library's frame."""

    __slots__ = ("_frame",)

    def __init__(self, frame: Any) -> None:
        """Hold the frame this accessor was reached through."""
        self._frame = frame

    def into(self, space: Any, head: Any) -> int:
        """Add this frame to a space as ``(head column...)`` facts.

        ``df.metta.into(m, "row")`` is ``metta.tables.add(m, "row", df)``, and
        says so: the accessor is the frame library's spelling of the same
        door, not a second mechanism.
        """
        return add(space, head, self._frame)


def accessors() -> tuple[str, ...]:
    """Install the metta accessor for every registered frame library already imported.

    Answers the libraries that now carry it, so a program can ask.

    Registration never imports a frame library. `import metta.tables` costs
    15 ms and `import pandas` costs 531 ms [measured 2026-09-06,
    time.perf_counter around each import in a fresh interpreter], so a module
    that registered by importing would charge every tables user for a library
    the program may never touch. It installs for whichever registered module
    is in `sys.modules`, every door in this module calls it first, and a
    program that imports a frame library afterwards and touches nothing else
    here calls this by name. Idempotent, because a library warns when an
    accessor name is replaced.

    Which libraries these are is the `frame` point's rows, not a list here:
    each row says which module it is and how that library spells an accessor,
    so a third one installs `df.metta` by registering
    (`metta.seam.frame.register(...)`, or the `metta.extensions` entry point).
    """
    for row in seam.frame.table().values():
        module = sys.modules.get(row.module)
        if module is not None and row.name not in _ACCESSED:
            row.accessor(module, _ACCESSOR, _FrameDoor)
            _ACCESSED.add(row.name)
    return tuple(sorted(_ACCESSED))


# -- a head as a SQL function


def _sql_answer(answers: Any) -> Any:
    """One SQL cell from a head's answers.

    No answer is SQL NULL, which is how SQL spells absence. Several answers
    refuse: a scalar function has one result per row and picking one would
    drop the rest silently. An atom that is not a primitive crosses as its
    canonical MeTTa text, the same rule the Arrow projection follows.
    """
    answer = answers.one(default=None)
    return str(answer) if isinstance(answer, Atom) else answer


def sql_function(connection: Any, head: Any, name: str | None = None) -> str:
    """Register a MeTTa head as a scalar SQL function, and answer its SQL name.

        m.run("(: dbl (-> Number Number))  (= (dbl $x) (* 2 $x))")
        tables.sql_function(connection, m.fn.dbl)
        connection.sql("select dbl(age) from people")

    The head is the callable from a space's `fn` namespace, which already
    carries its own name, its arity and its arrow, so nothing about the
    function is restated here; `name=` is the escape for a SQL identifier the
    head's own name cannot be.

    WHICH engines are known is the `sql` point's rows, and the first row that
    claims the connection declares the function its own way: sqlite3 wants the
    arity and no types, DuckDB wants the types and reads them from the head's
    DECLARED arrow, refusing by name when there is none (an arrow
    `inspect.signature` merely infers is a proposal, not a promise). A third
    engine registers rather than being added here. A row that produces no
    answer is SQL NULL and one that produces several refuses, because a scalar
    function has one result per row; a SQL NULL argument reaches the head as
    `Grounded(None)` and MeTTa decides what it means.
    """
    accessors()
    if not callable(head):
        msg = (
            f"sql_function registers a callable head, as m.fn.dbl; "
            f"{type(head).__name__} is not callable"
        )
        raise TypeError(msg)
    sql_name = name if name is not None else str(getattr(head, "__name__", head))
    claim = seam.sql.claim(connection)
    if claim is None:
        raise TypeError(
            seam.sql.refusal(f"a connection of type {type(connection).__name__}")
        )

    def call(*arguments: Any) -> Any:
        return _sql_answer(head(*arguments))

    call.__name__ = sql_name
    claim.row.define(connection, sql_name, call, head, inspect.signature(head))
    return sql_name


# The common order is a frame library first and this module second, so the
# import registers what is already there and no door has to be called to make
# `df.metta` appear. The other order is what `accessors()` is public for.
accessors()
