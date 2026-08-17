"""Purpose: the standard-library SQL instance of the bridge: one MeTTa
declaration relates (edge $a $b) to a SQLite table, petta.tables derives
every provider operation from it, and the contract in &petta says how
far to trust each one.

    (bridge (edge $a $b) (row edges (a $a) (b $b)))

The declaration is the converter, both directions, the way a MeTTa
equation is: a query becomes WHERE, an add becomes INSERT, a row becomes
the atom. petta/tables.py holds the derivation and its guarantees; this
file is only the SQLite glue and the contract:

  (context <name> closed-world)          negation may consult the table
  (annotations <name> bag)               SQL bag semantics, said plainly
  (handles <name> (edge $x $y) Exact)    the derived filtering IS the
                                         answer set, licensing LIMIT
  (handles <name> (edge $x $x) Exact)    repetition derives WHERE a = b,
                                         so the diagonal is exact too
  (writes <name> transactional)          (transaction ...) delegates to
                                         BEGIN/COMMIT/ROLLBACK

Declared Exact is trusted: the engine hands the bound down and a whole
join can be claimed without re-derivation. The unification the engine
still performs per answer is how bindings ENTER the local program, not
a verification pass; for an Exact shape it never rejects.
[tested: python/tests/test_sqlite_space.py]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sqlite3

from _common import check, done

from petta import tables
from petta.tables import TableBridge


def attach_sqlite(m, name: str, database: str = ":memory:") -> TableBridge:
    """Declare the schema in &petta, then read it back into a provider:
    the declaration is knowledge first, so explain and any program can
    query it, and MeTTa source that added its own (bridge ...) atoms has
    already declared a schema this attach will honour."""
    connection = sqlite3.connect(database, check_same_thread=False)
    connection.execute("CREATE TABLE IF NOT EXISTS edges (a TEXT, b TEXT)")
    tables.declare(m, name, "(bridge (edge $a $b) (row edges (a $a) (b $b)))")
    provider = TableBridge.from_context(m, name, connection)
    m.register_space(provider, name)
    m.declare_context(name, "closed-world")
    m.declare_annotations(name, "bag")
    m.declare_handles(name, "(edge $x $y)", "Exact")
    m.declare_handles(name, "(edge $x $x)", "Exact")
    m.declare_writes(name, "transactional")
    return provider


def demo() -> None:
    """The worked run: rows answer MeTTa, the diagonal is exact, and the
    licensed bound reaches the SQL as LIMIT."""
    import petta

    m = petta.MeTTa().fresh_space()
    provider = attach_sqlite(m, "&crm")
    m.run("!(add-atom &crm (edge a b))")
    m.run("!(add-atom &crm (edge b b))")
    m.run("!(add-atom &crm (edge b c))")
    (group,) = m.run("!(collapse (match &crm (edge $x $y) ($x $y)))")
    check("rows answer MeTTa", sorted(str(a) for a in group[0]),
          ["(a b)", "(b b)", "(b c)"])
    (group,) = m.run("!(collapse (match &crm (edge $x $x) $x))")
    check("the diagonal derives WHERE a = b", [str(a) for a in group[0]], ["b"])
    m.run("!(collapse (take 1 (match &crm (edge $x $y) (edge $x $y))))")
    check("the bound reached the SQL",
          any("LIMIT 1" in sql for sql in provider.executed))
    done("sqlite_space")


if __name__ == "__main__":
    demo()
