"""Purpose: a database as a space: tables are relations, match pushes bound
positions down as a WHERE clause, writes insert and delete, and one match
joins SQL rows with native facts. The engine keeps unification, so pushdown
is speed, never trust.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done, skip

try:
    import duckdb
except ImportError:
    skip("duckdb is not installed")

from petta import MeTTa, expr, S

from petta.integrations.duckdb_space import attach

m = MeTTa().fresh_space()
conn = duckdb.connect(":memory:")
conn.execute("create table users (id integer, name text)")
conn.execute("insert into users values (1, 'Ada'), (2, 'Bob'), (3, 'Cy')")
attach(m, "&crm", conn)

check("enumerate", m.run("!(collapse (match &crm (users $id $n) $n))"),
      [[expr("Ada", "Bob", "Cy")]])
check("pushdown filter", m.run("!(match &crm (users 2 $n) $n)"), [["Bob"]])

m.run('!(add-atom &crm (users 4 "Dee"))')
check("insert landed in SQL",
      conn.execute("select name from users where id = 4").fetchone()[0], "Dee")

m.run("(vip 1)\n(vip 4)")
(group,) = m.run(
    "!(collapse (match (context-space) (vip $id)"
    " (match &crm (users $id $n) $n)))"
)
check("SQL joined with native facts", group, [expr("Ada", "Dee")])
done("04_sql_is_a_space")
