"""Purpose: SQL tables as matchable spaces, the worked SQL instance of the
integration interface. attach() registers a DuckDB connection as a foreign
space: every table becomes a relation, (users $id $name) enumerates rows,
bound positions push down into a WHERE clause so the database does the
filtering, adds insert and removals delete. The engine still unifies every
candidate against the pattern, so pushdown is speed, never trust.
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


def _duckdb():
    try:
        import duckdb
    except ImportError as exc:
        raise PettaError(
            "the duckdb integration needs the duckdb package: pip install duckdb"
        ) from exc
    return duckdb


class DuckDBSpace(SpaceProvider):
    """A DuckDB connection as a space: one relation per table.

    Rows come back as (table col1 col2 ...) atoms with SQL text as grounded
    strings and numbers as numbers. Ground pattern positions become a WHERE
    clause, parameterized, so the filter runs where the data lives.
    """

    def __init__(self, connection: Any, tables: list[str] | None = None) -> None:
        self._conn = connection
        self._tables = tables

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
            if isinstance(arg, Gnd):
                where.append(f'"{column}" = ?')
                parameters.append(decode(arg))
            elif isinstance(arg, Sym):
                # A symbol in a pattern position states the text it names.
                where.append(f'"{column}" = ?')
                parameters.append(arg.name)
        sql = f'select * from "{table}"'
        if where:
            sql += " where " + " and ".join(where)
        for row in self._conn.execute(sql, parameters).fetchall():
            yield Expr([Sym(table), *(Gnd(v) for v in row)])

    def atoms(self) -> Iterator[Atom]:
        for table in self.table_names():
            for row in self._conn.execute(f'select * from "{table}"').fetchall():
                yield Expr([Sym(table), *(Gnd(v) for v in row)])

    # ------------------------------------------------------------------ writes

    def add(self, atom: Atom) -> None:
        table, values = self._row_of(atom, "add")
        marks = ", ".join("?" for _ in values)
        self._conn.execute(f'insert into "{table}" values ({marks})', values)

    def remove(self, atom: Atom) -> bool:
        table, values = self._row_of(atom, "remove")
        columns = self.columns(table)
        where = " and ".join(f'"{c}" = ?' for c in columns)
        before = self._conn.execute(
            f'select count(*) from "{table}" where {where}', values
        ).fetchone()[0]
        self._conn.execute(f'delete from "{table}" where {where}', values)
        return before > 0

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
            if isinstance(arg, Gnd):
                values.append(decode(arg))
            elif isinstance(arg, Sym):
                values.append(arg.name)
            else:
                raise PettaError(f"cannot {verb} {atom}: {arg} is not a value")
        return table, values


def attach(m, name: str, database: Any = ":memory:", tables: list[str] | None = None) -> DuckDBSpace:
    """Register a DuckDB database as a space on this engine.

        space = petta.integrations.duckdb_space.attach(m, "&db", "file.duckdb")
        m.query is not needed: match reaches it from any program,
        m.run('!(match &db (users $id $name) $name)')

    database is a connection, a path, or :memory:.
    """
    duckdb = _duckdb()
    connection = database if hasattr(database, "execute") else duckdb.connect(database)
    provider = DuckDBSpace(connection, tables)
    m.register_space(name, provider)
    return provider
