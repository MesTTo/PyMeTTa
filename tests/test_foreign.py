"""Purpose: spaces implemented in Python: matching, enumeration, writes,
conjunctions, and mixing with native spaces, through a dict-backed provider
and through DuckDB with SQL pushdown.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import EngineError, S, V, expr
from petta.foreign import SpaceProvider


class ListSpace(SpaceProvider):
    """The simplest honest provider: a Python list of atoms."""

    def __init__(self, atoms=()):
        self.stored = list(atoms)
        self.match_calls = 0

    def match(self, pattern):
        self.match_calls += 1
        return iter(self.stored)

    def atoms(self):
        return iter(self.stored)

    def add(self, atom):
        self.stored.append(atom)

    def remove(self, atom):
        if atom in self.stored:
            self.stored[:] = [a for a in self.stored if a != atom]
            return True
        return False


@pytest.fixture()
def listspace(metta):
    provider = ListSpace([S.edge(S.a, S.b), S.edge(S.b, S.c), S.other(1)])
    name = f"&list{id(provider) % 10000}"
    metta.register_space(name, provider)
    yield name, provider, metta
    metta.unregister_space(name)


def test_match_reaches_the_provider(listspace):
    name, provider, m = listspace
    r = m.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
    assert r == [[expr(expr(S.a, S.b), expr(S.b, S.c))]]
    assert provider.match_calls >= 1


def test_engine_unifies_over_approximate_candidates(listspace):
    # The provider returns everything; the pattern still selects correctly,
    # because unification is the engine's.
    name, provider, m = listspace
    assert m.run(f"!(match {name} (edge a $y) $y)") == [[S.b]]


def test_conjunction_routes_through_the_provider(listspace):
    name, provider, m = listspace
    r = m.run(f"!(collapse (match {name} (, (edge $x $y) (edge $y $z)) ($x $z)))")
    assert r == [[expr(expr(S.a, S.c))]]


def test_python_query_api_over_foreign_space(listspace):
    name, provider, m = listspace
    rows = m.space(name).query(S.edge(V.x, V.y), S.edge(V.y, V.z))
    assert [(r.x, r.z) for r in rows] == [(S.a, S.c)]


def test_writes_reach_the_provider(listspace):
    name, provider, m = listspace
    m.run(f"!(add-atom {name} (edge c d))")
    assert S.edge(S.c, S.d) in provider.stored
    m.run(f"!(remove-atom {name} (other 1))")
    assert S.other(1) not in provider.stored


def test_get_atoms_enumerates(listspace):
    name, provider, m = listspace
    space = m.space(name)
    assert len(space.atoms()) == 3
    assert space.count() == 3


def test_mixed_native_and_foreign_join(listspace):
    name, provider, m = listspace
    native = m.fresh_space()
    native.add(S.blessed(S.a))
    r = native.run(
        f"!(collapse (match {name} (edge $x $y) "
        f"(match (context-space) (blessed $x) ($x reaches $y))))"
    )
    assert r == [[expr(expr(S.a, S.reaches, S.b))]]


def test_read_only_provider_errors_loudly(metta):
    class ReadOnly(SpaceProvider):
        def atoms(self):
            return iter([S.fact(1)])

    name = "&readonly1"
    metta.register_space(name, ReadOnly())
    try:
        with pytest.raises(EngineError) as excinfo:
            metta.run(f"!(add-atom {name} (fact 2))")
        assert "read-only" in str(excinfo.value)
    finally:
        metta.unregister_space(name)


# ---------------------------------------------------------------------- SQL


duckdb = pytest.importorskip("duckdb")

from petta.integrations.duckdb_space import DuckDBSpace, attach  # noqa: E402


@pytest.fixture()
def db(metta):
    connection = duckdb.connect(":memory:")
    connection.execute("create table users (id integer, name text)")
    connection.execute("insert into users values (1, 'Ada'), (2, 'Bob'), (3, 'Cy')")
    connection.execute("create table vips (id integer)")
    connection.execute("insert into vips values (1), (3)")
    provider = attach(metta, "&db", connection)
    yield metta, connection, provider
    metta.unregister_space("&db")


def test_sql_rows_match_from_metta_source(db):
    m, _conn, _provider = db
    r = m.run('!(collapse (match &db (users $id $name) $name))')
    (group,) = r
    assert group == [expr("Ada", "Bob", "Cy")]


def test_ground_positions_push_down_to_where(db):
    m, conn, provider = db
    # Correctness of the filtered answer:
    assert m.run("!(match &db (users 2 $name) $name)") == [["Bob"]]
    # And the filter genuinely ran in SQL: a spy connection sees the WHERE.
    seen = []
    original = provider._conn

    class Spy:
        def execute(self, sql, *a):
            seen.append(sql)
            return original.execute(sql, *a)

    provider._conn = Spy()
    try:
        m.run("!(match &db (users 2 $name) $name)")
    finally:
        provider._conn = original
    assert any("where" in s.lower() and "id" in s.lower() for s in seen)


def test_sql_join_with_native_facts(db):
    m, _conn, _provider = db
    native = m.fresh_space()
    native.run("(nickname 1 the-countess)")
    r = native.run(
        "!(collapse (match &db (, (vips $id) (users $id $name)) "
        "(match (context-space) (nickname $id $nick) ($name $nick))))"
    )
    (group,) = r
    assert group == [expr(expr("Ada", S["the-countess"]))]


def test_sql_insert_and_delete_from_metta(db):
    m, conn, _provider = db
    m.run('!(add-atom &db (users 4 "Dee"))')
    assert conn.execute("select name from users where id = 4").fetchone()[0] == "Dee"
    m.run('!(remove-atom &db (users 4 "Dee"))')
    assert conn.execute("select count(*) from users where id = 4").fetchone()[0] == 0


def test_provider_level_match_yields_atoms(db):
    _m, conn, provider = db
    got = list(provider.match(S.users(2, V.n)))
    assert got == [expr(S.users, 2, "Bob")]


def test_duckdb_null_and_dates_cross_with_value_semantics(metta):
    """SQL NULL is the NULL symbol both ways, a NULL binding finds NULLs
    (IS NOT DISTINCT FROM), non-primitive scalars cross as ISO text, and
    clear() empties every table while the schema stays."""
    duckdb = pytest.importorskip("duckdb")
    from petta.integrations.duckdb_space import NULL, attach

    conn = duckdb.connect(":memory:")
    conn.execute("create table logs (day DATE, note TEXT)")
    conn.execute("insert into logs values (DATE '2026-08-13', 'shipped'), (NULL, 'undated')")
    space = attach(metta, "&logs", conn)
    try:
        rows = metta.run("!(collapse (match &logs (logs $d $n) ($d $n)))")
        listed = {str(pair) for pair in rows[0][0]}
        assert '("2026-08-13" "shipped")' in listed
        assert '(NULL "undated")' in listed
        # A NULL binding pushes down and matches exactly the NULL row.
        hit = metta.run('!(match &logs (logs NULL $n) $n)')
        assert hit == [["undated"]]
        # A date binding by its ISO text finds the dated row.
        hit = metta.run('!(match &logs (logs "2026-08-13" $n) $n)')
        assert hit == [["shipped"]]
        space.clear()
        assert metta.run("!(collapse (match &logs (logs $d $n) x))") == [[expr()]]
    finally:
        metta.unregister_space("&logs")
        conn.close()


def test_provider_collision_is_refused(metta):
    class Empty(SpaceProvider):
        def atoms(self):
            return iter(())

    first = Empty()
    metta.register_space("&col", first)
    try:
        with pytest.raises(ValueError):
            metta.register_space("&col", Empty())
        # The same provider again is idempotent, not a collision.
        metta.register_space("&col", first)
    finally:
        metta.unregister_space("&col")
