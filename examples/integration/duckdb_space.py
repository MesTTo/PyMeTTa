"""Purpose: a database as a space, built HERE, on the public integration
interface alone, because that is the point: tables are relations, match
pushes bound positions down as a WHERE clause, writes insert and delete,
and one match joins SQL rows with native facts. The engine keeps
unification, so pushdown is speed, never trust. SQL NULL crosses as the
symbol NULL both ways, non-primitive scalars (dates, decimals) cross as
their ISO text so value semantics survive the boundary, and comparisons
use IS NOT DISTINCT FROM so a NULL binding matches NULLs. The provider
below is the whole worked SQL instance, not an import.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: pushdown for inequalities once patterns can carry
    them; today equality on ground positions is what a pattern states.
"""

from collections.abc import Iterator
from typing import Any

from _common import check, done, skip

try:
    import duckdb
except ImportError:
    skip("duckdb is not installed")

from petta import Expression, MeTTa, S, V
from petta.atoms import Atom, Expr, Gnd, Sym, Var, decode
from petta.errors import PettaError
from petta.foreign import SpaceProvider

# SQL NULL as an atom: the symbol NULL, SQL's own name for it. A string
# "NULL" stays a string; only the symbol means the absent value.
NULL = Sym("NULL")


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
        for column, arg in zip(columns, pattern.args, strict=True):
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

    def pushdown(self, pattern: Atom) -> str:
        """Exact when the WHERE clause covers everything the pattern constrains.

        A ground position becomes an IS NOT DISTINCT FROM, so the query
        answers it. A symbol position deliberately does not, because rows
        carry text as grounded strings and a symbol never matches one: that
        pattern is answered by a query that ignores the symbol, and the
        engine's unification is what filters it out.

        So the claim is about the WHOLE pattern, not the indexed column. A
        provider filtering on one position while the pattern constrains
        another is inexact however good that one filter is, and saying
        otherwise loses answers, which is what check_space_provider catches.
        """
        if not (
            isinstance(pattern, Expr)
            and pattern.children
            and isinstance(pattern.head, Sym)
        ):
            return "inexact"
        table = pattern.head.name
        if table not in self.table_names() or len(pattern.args) != len(
            self.columns(table)
        ):
            return "inexact"
        unfiltered = (
            arg
            for arg in pattern.args
            if not isinstance(arg, Gnd)
            and not (isinstance(arg, Sym) and arg == NULL)
            and not isinstance(arg, Var)
        )
        return "inexact" if next(unfiltered, None) is not None else "exact"

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
        """One row, because a space is a multiset and removal subtracts from
        it: two identical rows need two removals. `delete ... where` has no
        LIMIT in SQL, so the row is picked by `rowid` first and deleted by
        that key, which also makes the pick and the delete report the same
        fact instead of a count probe standing in front of a sweep."""
        table, values = self._row_of(atom, "remove")
        columns = self.columns(table)
        where = " and ".join(
            f"{_identifier(c)} IS NOT DISTINCT FROM ?" for c in columns
        )
        picked = self._conn.execute(
            f"select rowid from {_identifier(table)} where {where} limit 1", values
        ).fetchone()
        if picked is None:
            return False
        self._conn.execute(
            f"delete from {_identifier(table)} where rowid = ?", [picked[0]]
        )
        return True

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
    """Register a DuckDB database as a space on this engine. database is a
    connection, a path, or :memory:. A path or :memory: opens a connection
    the space owns and close() closes; a passed connection stays the
    caller's."""
    if hasattr(database, "execute"):
        provider = DuckDBSpace(database, tables)
    else:
        provider = DuckDBSpace(duckdb.connect(database), tables)
        provider._owns_connection = True
    m.register_space(provider, name)
    return provider


def demo() -> None:
    """The worked run, kept behind a function so the provider above can be
    IMPORTED. A module that connects and queries at import time cannot be
    pointed at by a test, and petta.testing.SpaceComplianceSuite is pointed at
    DuckDBSpace in bindings/python/tests/test_compliance_duckdb.py."""
    m = MeTTa().new_space()
    conn = duckdb.connect(":memory:")
    conn.execute("create table users (id integer, name text)")
    conn.execute("insert into users values (1, 'Ada'), (2, 'Bob'), (3, 'Cy')")
    conn.execute("create table vips (id integer)")
    conn.execute("insert into vips values (1), (3)")
    provider = attach(m, "&crm", conn)

    check("enumerate", m.run("!(collapse (match &crm (users $id $n) $n))"),
          [[Expression(("Ada", "Bob", "Cy"))]])
    check("pushdown filter", m.run("!(match &crm (users 2 $n) $n)"), [["Bob"]])

    # The filter genuinely ran in SQL: a spy connection sees the WHERE clause.
    seen = []
    original = provider._conn


    class Spy:
        def execute(self, sql, *a):
            seen.append(sql)
            return original.execute(sql, *a)


    provider._conn = Spy()
    m.run("!(match &crm (users 2 $n) $n)")
    provider._conn = original
    check("the WHERE ran where the data lives",
          any("where" in s.lower() and "id" in s.lower() for s in seen), True)

    # Provider-level match answers atoms directly.
    check("provider-level match", list(provider.match(S.users(2, V.n))),
          [Expression((S.users, 2, "Bob"))])

    # One match joins SQL tables with each other and with native facts.
    m.run("(nickname 1 the-countess)")
    (group,) = m.run(
        "!(collapse (match &crm (, (vips $id) (users $id $n)) "
        "(match (context-space) (nickname $id $nick) ($n $nick))))"
    )
    check("SQL joined with native facts", group, [Expression((Expression(("Ada", S["the-countess"])),))])

    # Writes: add-atom inserts, remove-atom deletes, from running MeTTa.
    m.run('!(add-atom &crm (users 4 "Dee"))')
    check("insert landed in SQL",
          conn.execute("select name from users where id = 4").fetchone()[0], "Dee")
    m.run('!(remove-atom &crm (users 4 "Dee"))')
    check("delete landed in SQL",
          conn.execute("select count(*) from users where id = 4").fetchone()[0], 0)

    # NULL and dates: the NULL symbol both ways, ISO text for scalar types,
    # a NULL binding finding exactly the NULL row, clear() keeping the schema.
    conn.execute("create table logs (day DATE, note TEXT)")
    conn.execute("insert into logs values (DATE '2026-08-13', 'shipped'), (NULL, 'undated')")
    rows = m.run("!(collapse (match &crm (logs $d $n) ($d $n)))")
    listed = {str(pair) for pair in rows[0][0]}
    check("a date crosses as its ISO text", '("2026-08-13" "shipped")' in listed, True)
    check("NULL crosses as the NULL symbol", '(NULL "undated")' in listed, True)
    check("a NULL binding finds the NULL row",
          m.run("!(match &crm (logs NULL $n) $n)"), [["undated"]])
    check("a date binding finds the dated row",
          m.run('!(match &crm (logs "2026-08-13" $n) $n)'), [["shipped"]])
    provider.clear()
    check("clear empties, schema stays",
          m.run("!(collapse (match &crm (logs $d $n) x))"), [[Expression(())]])

    m.unregister_space("&crm")
    done("duckdb_space")


if __name__ == "__main__":
    demo()
