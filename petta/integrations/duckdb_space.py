"""Purpose: SQL tables as matchable spaces, the worked SQL instance of the
integration interface. attach() registers a DuckDB connection as a foreign
space: every table becomes a relation, (users $id $name) enumerates rows,
bound positions push down into a WHERE clause so the database does the
filtering, adds insert and removals delete. The engine still unifies every
candidate against the pattern, so pushdown is speed, never trust. SQL NULL
crosses as the symbol NULL both ways, non-primitive scalars (dates,
decimals) cross as their ISO text so value semantics survive the boundary,
and comparisons use IS NOT DISTINCT FROM so a NULL binding matches NULLs.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: pushdown for inequalities once patterns can carry
    them; today equality on ground positions is what a pattern states.
"""

from __future__ import annotations

from typing import Any, Iterator

from petta.atoms import Atom, Expr, Gnd, Sym, decode
from petta.errors import PettaError
from petta.foreign import SpaceProvider

__all__ = ["DuckDBSpace", "attach"]

# SQL NULL as an atom: the symbol NULL, SQL's own name for it. A string
# "NULL" stays a string; only the symbol means the absent value.
NULL = Sym("NULL")


def _duckdb():
    try:
        import duckdb
    except ImportError as exc:
        raise PettaError(
            "the duckdb integration needs the duckdb package: pip install duckdb"
        ) from exc
    return duckdb


def _identifier(name: str) -> str:
    """A quoted SQL identifier, embedded quotes doubled."""
    return '"' + name.replace('"', '""') + '"'


def _to_atom_value(value: Any) -> Atom:
    """One SQL scalar as an atom: NULL as the NULL symbol, primitives as
    themselves, and everything else (dates, decimals, timestamps) as its
    ISO text, so equal values stay equal across the boundary."""
    if value is None:
        return NULL
    if isinstance(value, (bool, int, float, str)):
        return Gnd(value)
    return Gnd(str(value))


def _to_sql_value(atom: Atom) -> Any:
    """One pattern or row position as a SQL parameter; None for NULL."""
    if isinstance(atom, Sym):
        return None if atom == NULL else atom.name
    return decode(atom)


class DuckDBSpace(SpaceProvider):
    """A DuckDB connection as a space: one relation per table.

    Rows come back as (table col1 col2 ...) atoms with SQL text as grounded
    strings, numbers as numbers, NULL as the NULL symbol, and other scalar
    types as their ISO text. Ground pattern positions become a WHERE clause
    using IS NOT DISTINCT FROM, parameterized, so the filter runs where the
    data lives and a NULL binding finds NULLs.
    """

    def __init__(self, connection: Any, tables: list[str] | None = None) -> None:
        self._conn = connection
        self._tables = tables
        self._owns_connection = False

    # ------------------------------------------------------------- inspection

    def table_names(self) -> list[str]:
        if self._tables is not None:
            return list(self._tables)
        rows = self._conn.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'main' order by table_name"
        ).fetchall()
        return [r[0] for r in rows]

    def columns(self, table: str) -> list[str]:
        rows = self._conn.execute(
            "select column_name from information_schema.columns "
            "where table_name = ? order by ordinal_position",
            [table],
        ).fetchall()
        if not rows:
            raise PettaError(f"no table {table!r} in this DuckDB space")
        return [r[0] for r in rows]

    # ---------------------------------------------------------------- matching

    def match(self, pattern: Atom) -> Iterator[Atom]:
        if not (isinstance(pattern, Expr) and pattern.children and isinstance(pattern.head, Sym)):
            # A shapeless pattern falls back to full enumeration; the engine
            # unifies, so this stays correct.
            yield from self.atoms()
            return
        table = pattern.head.name
        if table not in self.table_names():
            return
        columns = self.columns(table)
        if len(pattern.args) != len(columns):
            return
        where, parameters = [], []
        for column, arg in zip(columns, pattern.args):
            if isinstance(arg, Gnd) or (isinstance(arg, Sym) and arg == NULL):
                # A ground position states its value; IS NOT DISTINCT FROM
                # is SQL equality that also finds NULL when NULL is asked.
                where.append(f"{_identifier(column)} IS NOT DISTINCT FROM ?")
                parameters.append(_to_sql_value(arg))
            # A non-NULL symbol stays out of the pushdown: rows carry text
            # as grounded strings, so a symbol never matches one and the
            # engine's unification is the answer, consistently.
        sql = f"select * from {_identifier(table)}"
        if where:
            sql += " where " + " and ".join(where)
        for row in self._conn.execute(sql, parameters).fetchall():
            yield Expr([Sym(table), *(_to_atom_value(v) for v in row)])

    def atoms(self) -> Iterator[Atom]:
        for table in self.table_names():
            for row in self._conn.execute(
                f"select * from {_identifier(table)}"
            ).fetchall():
                yield Expr([Sym(table), *(_to_atom_value(v) for v in row)])

    # ------------------------------------------------------------------ writes

    def add(self, atom: Atom) -> None:
        table, values = self._row_of(atom, "add")
        marks = ", ".join("?" for _ in values)
        self._conn.execute(
            f"insert into {_identifier(table)} values ({marks})", values
        )

    def remove(self, atom: Atom) -> bool:
        table, values = self._row_of(atom, "remove")
        columns = self.columns(table)
        where = " and ".join(
            f"{_identifier(c)} IS NOT DISTINCT FROM ?" for c in columns
        )
        before = self._conn.execute(
            f"select count(*) from {_identifier(table)} where {where}", values
        ).fetchone()[0]
        self._conn.execute(
            f"delete from {_identifier(table)} where {where}", values
        )
        return before > 0

    def clear(self) -> None:
        """Every row of every table this space serves; the schema stays."""
        for table in self.table_names():
            self._conn.execute(f"delete from {_identifier(table)}")

    def close(self) -> None:
        """Close the connection if this space opened it; a caller's own
        connection stays the caller's to close."""
        if self._owns_connection:
            self._conn.close()

    def _row_of(self, atom: Atom, verb: str) -> tuple[str, list[Any]]:
        if not (isinstance(atom, Expr) and atom.children and isinstance(atom.head, Sym)):
            raise PettaError(f"cannot {verb} {atom}: a row is (table values...)")
        table = atom.head.name
        columns = self.columns(table)
        if len(atom.args) != len(columns):
            raise PettaError(
                f"cannot {verb} {atom}: {table} has columns {columns}"
            )
        values = []
        for arg in atom.args:
            if isinstance(arg, (Gnd, Sym)):
                values.append(_to_sql_value(arg))
            else:
                raise PettaError(f"cannot {verb} {atom}: {arg} is not a value")
        return table, values


def attach(m, name: str, database: Any = ":memory:", tables: list[str] | None = None) -> DuckDBSpace:
    """Register a DuckDB database as a space on this engine.

        space = petta.integrations.duckdb_space.attach(m, "&db", "file.duckdb")
        m.query is not needed: match reaches it from any program,
        m.run('!(match &db (users $id $name) $name)')

    database is a connection, a path, or :memory:. A path or :memory: opens
    a connection the space owns and close() closes; a passed connection
    stays the caller's.
    """
    duckdb = _duckdb()
    if hasattr(database, "execute"):
        provider = DuckDBSpace(database, tables)
    else:
        provider = DuckDBSpace(duckdb.connect(database), tables)
        provider._owns_connection = True
    m.register_space(name, provider)
    return provider
