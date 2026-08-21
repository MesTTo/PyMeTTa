"""Purpose: derive a whole table-backed space provider from MeTTa bridge
declarations, so the contract is rewrite rules and both directions of
the boundary fall out of matching them. The module is petta.tables
because petta.bridge is already the standing bridge RULE between two
spaces (petta.subscribe.bridge); the two are the same idea at two
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

Declarations may live in &petta, ctx-scoped like every other contract
atom: `declare(m, "&crm", "(bridge (edge $a $b) (row edges ...))")`
writes `(bridge &crm (edge $a $b) (row edges ...))` there, MeTTa source
can add the same atom itself, and `TableBridge.from_context(m, "&crm",
connection)` reads every one back, so a program carries its schema as
knowledge and the attach is one line.

Guarantees:
  - a database row becomes an atom from its typed cell values; plain text is
    always a symbol, NULL is Gnd(None), and structured values use the tagged
    atom wire rather than the source parser [tested:
    test_a_row_value_becomes_an_atom_without_being_reparsed;
    commit=09c5ca4528bc3763e94155d5cb00e9e0a662cc95]
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

import json
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Protocol, cast

from .atoms import (
    Atom,
    Expr,
    Gnd,
    Sym,
    Var,
    atom_from_wire,
    encode,
    is_ground,
    unify,
)
from .foreign import SpaceProvider

_ATOM_CELL_PREFIX = b"\x00petta-atom-v1\x00"


def _encoded_cell(atom: Atom) -> bytes:
    """A structured atom in a DB-API scalar, without passing through text."""
    try:
        payload = json.dumps(
            atom.to_wire(),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        msg = (
            f"{atom!r} has no stable table-cell representation; table rows can "
            "carry symbols, primitive grounded values, and expressions made from them"
        )
        raise ValueError(msg) from exc
    return _ATOM_CELL_PREFIX + payload


def _atom_from_cell(value: Any) -> Atom:
    """Map one driver value to its atom; text is data, never source code."""
    binary = bytes(value) if isinstance(value, (bytearray, memoryview)) else value
    if isinstance(binary, bytes) and binary.startswith(_ATOM_CELL_PREFIX):
        try:
            wire = json.loads(binary[len(_ATOM_CELL_PREFIX) :].decode("utf-8"))
            return atom_from_wire(wire)
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            msg = "a table cell starts with PeTTa's atom tag but its payload is corrupt"
            raise ValueError(msg) from exc
    if isinstance(value, str):
        return Sym(value)
    return encode(value)


def _cell_from_atom(atom: Atom) -> Any:
    """Map an atom to one DB-API parameter that `_atom_from_cell` inverts."""
    if isinstance(atom, Sym):
        return atom.name
    if isinstance(atom, Gnd):
        value = atom.value
        if value is None or type(value) in (int, float):
            return value
        if type(value) in (bool, str):
            return _encoded_cell(atom)
        msg = (
            f"{atom!r} is an opaque grounded value; a table cell needs a stable "
            "database representation"
        )
        raise ValueError(msg)
    if isinstance(atom, Expr):
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
        if not isinstance(declaration, Expr) or len(declaration.children) != 3:
            raise _declaration_error(declaration)
        head, atom_shape, row_shape = declaration.children
        if str(head) != "bridge" or not isinstance(atom_shape, Expr) or not isinstance(row_shape, Expr):
            raise _declaration_error(declaration)
        self.shape = atom_shape
        table, *columns = row_shape.children[1:]
        self.table = str(table)
        self.columns: dict[str, str] = {}
        for pair in columns:
            if not isinstance(pair, Expr) or len(pair.children) != 2:
                msg = f"a row column is (name $var), got {pair}"
                raise ValueError(msg)
            column, variable = pair.children
            if not isinstance(variable, Var):
                msg = f"a row column binds a variable, got {pair}"
                raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
            self.columns[str(variable)] = str(column)
        for child in atom_shape.children:
            if isinstance(child, Var) and str(child) not in self.columns:
                msg = f"the atom shape's {child} has no column in {row_shape}"
                raise ValueError(msg)

    def constraints(self, pattern: Atom) -> tuple[list[str], list[Any], bool] | None:  # noqa: C901  -- constraints keeps the table constraint compiler together so its branches share one state
        """WHERE fragments from matching the pattern against this shape.

        Answers (where, arguments, exact), or None when the shapes cannot
        match and no row is a candidate. A pattern variable binds the
        position it first met, a declared literal or a column, and every
        later occurrence becomes the equality the pattern itself demands;
        the kit's repeated-variable folds probe exactly this.
        """
        if not isinstance(pattern, Expr) or len(pattern.children) != len(self.shape.children):
            return None
        where: list[str] = []
        arguments: list[Any] = []
        exact = True
        seen: dict[str, tuple[str, Any]] = {}
        for shaped, given in zip(self.shape.children, pattern.children, strict=True):
            if not isinstance(shaped, Var):
                constant = shaped
                if isinstance(given, Var):
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
            if isinstance(given, Var):
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
            if isinstance(given, Expr) and not is_ground(given):
                exact = False
                continue
            _value_constraint(
                where,
                arguments,
                column,
                _cell_from_atom(given),
            )
        return where, arguments, exact

    def column_list(self) -> str:
        return ", ".join(
            self.columns[str(child)]
            for child in self.shape.children
            if isinstance(child, Var)
        )

    def values(self, atom: Expr) -> list[Any]:
        return [
            _cell_from_atom(given)
            for shaped, given in zip(self.shape.children, atom.children, strict=True)
            if isinstance(shaped, Var)
        ]

    def atom(self, row: Any) -> Atom:
        values = iter(row)
        children = [
            _atom_from_cell(next(values)) if isinstance(child, Var) else child
            for child in self.shape.children
        ]
        return Expr(children)


class TableBridge(SpaceProvider):
    """Every provider operation derived from the declarations; nothing in
    here is specific to any table.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        parse: Callable[[str], Atom],
        connection: Executes,
        declarations: Atom | str | Iterable[Atom | str],
    ) -> None:
        self._parse = parse
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
        m: Any,
        name: str,
        connection: Executes,
    ) -> TableBridge:
        """The provider for every `(bridge <name> <shape> <row>)` atom in
        &petta, so a schema declared from MeTTa source, or by declare()
        below, becomes a provider in one line.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        (group,) = m.run(
            f"!(collapse (match &petta (bridge {name} $shape $row)"
            f" (bridge $shape $row)))"
        )
        declarations = list(group[0])
        if not declarations:
            msg = f"&petta declares no (bridge {name} ...) schema"
            raise ValueError(msg)
        return cls(m.parse, connection, declarations)

    # -- the provider surface, all of it derived -----------------------------

    def atoms(self) -> Iterator[Atom]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return (
            shape.atom(row)
            for shape in self._shapes
            for row in self._select(shape, [], [])
        )

    def match(self, pattern: Atom, *, limit: int | None = None) -> Iterator[Atom]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        def answers() -> Iterator[Atom]:
            for shape, (where, arguments, _exact) in self._admitting(pattern):
                for row in self._select(shape, where, arguments, limit):
                    yield shape.atom(row)

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
            if is_ground(atom)
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
            shape.values(cast(Expr, atom)),
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
                for atom in (shape.atom(row),)
                if isinstance(atom, Expr) and unify(pattern, atom) is not None
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
        sql = f"SELECT {shape.column_list()} FROM {shape.table}"  # noqa: S608  # nosec B608 - identifiers from the trusted declaration
        if where:
            sql += " WHERE " + " AND ".join(where)
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        self.executed.append(sql)
        return list(self.connection.execute(sql, arguments))


def declare(m: Any, name: str, declaration: Atom | str) -> Atom:
    """Write one ctx-scoped bridge declaration into &petta, where explain
    and any program can read the schema, and from_context will.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    parsed = m.parse(declaration) if isinstance(declaration, str) else declaration
    if not isinstance(parsed, Expr):
        raise _declaration_error(parsed)
    _Shape(parsed)  # validated before it is stored, the declare_* discipline
    _, atom_shape, row_shape = parsed.children
    stored = m.parse(f"(bridge {name} {atom_shape} {row_shape})")
    m.run("!(add-atom &petta decl)", using={"decl": stored})
    return stored
