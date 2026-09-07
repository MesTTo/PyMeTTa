"""Purpose: prove the inward Arrow door, the bridge's stream and the SQL doors.

The inward Arrow door on tables.add, the bridge's own outward stream, the frame
libraries' accessor, and a MeTTa head registered as a SQL scalar function.

Guarantees:
  - a DuckDB relation, a pyarrow table and a Parquet-shaped reader load as
    facts through the stream, and a source with its own row door produces the
    same atoms either way [tested: this module; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - a SQL-backed space streams its declared columns to any Arrow consumer
    [tested: test_a_bridge_streams_its_sqlite_rows; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sqlite3

import pytest

from metta import S, V, tables
from metta.tables import TableBridge

pytest.importorskip("nanoarrow")


@pytest.fixture()
def m(metta):
    """One disposable space per scenario."""
    with metta._new_space() as space:
        yield space


@pytest.fixture()
def edges():
    """A two-column SQLite table with two rows, readable from any thread.

    DuckDB's replacement scan reads the capsule on a worker thread, and the
    bridge reads the connection inside that call, so sqlite3's default
    thread affinity refuses intermittently: it depends on which thread
    DuckDB picks for the scan.
    """
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute("create table edges (a text, b text)")
    connection.executemany("insert into edges values (?, ?)", [("x", "y"), ("y", "z")])
    return connection


def test_a_duckdb_relation_loads_through_the_arrow_door(m):
    """A relation has no iter_rows and no itertuples; the stream is its door."""
    duckdb = pytest.importorskip("duckdb")

    relation = duckdb.sql(
        "select 1 as a, 'x' as b union all select 2, 'y' union all select 2, 'y'"
    )
    assert tables.add(m, "drow", relation) == 3
    rows = m.match(S.drow(V.a, V.b)).to_dicts()
    assert sorted(map(str, rows)) == [
        "{'a': 1, 'b': 'x'}",
        "{'a': 2, 'b': 'y'}",
        "{'a': 2, 'b': 'y'}",
    ]


def test_a_pyarrow_table_loads_through_the_arrow_door(m):
    """The same door reads a materialised Arrow table."""
    pa = pytest.importorskip("pyarrow")

    assert tables.add(m, S.arow, pa.table({"a": [9, 10], "b": ["k", None]})) == 2
    assert m.match(S.arow(V.a, V.b)).to_dicts() == [
        {"a": 9, "b": "k"},
        {"a": 10, "b": None},
    ]


def test_a_multi_batch_stream_writes_every_batch(m):
    """A reader that hands over several batches loses none of them."""
    pa = pytest.importorskip("pyarrow")

    schema = pa.schema([("n", pa.int64())])
    batches = [pa.record_batch({"n": [index]}, schema=schema) for index in range(5)]
    reader = pa.RecordBatchReader.from_batches(schema, batches)
    assert tables.add(m, "brow", reader) == 5
    assert len(m.match(S.brow(V.n))) == 5


def test_both_inward_doors_build_the_same_atoms(metta):
    """A frame's own row door and its Arrow stream are one answer.

    tables.add prefers the row door because it measured faster; this is what
    makes that a free choice rather than a second set of atoms.
    """
    polars = pytest.importorskip("polars")
    pa = pytest.importorskip("pyarrow")

    frame = polars.DataFrame({"a": [1, 2, 2], "b": ["x", "y", "y"]})
    with metta._new_space() as own, metta._new_space() as through_arrow:
        assert tables.add(own, "prow", frame) == 3
        assert tables.add(through_arrow, "prow", pa.table(frame)) == 3
        assert own.match(S.prow(V.a, V.b)).to_dicts() == [
            {"a": 1, "b": "x"},
            {"a": 2, "b": "y"},
            {"a": 2, "b": "y"},
        ]
        assert own.match(S.prow(V.a, V.b)).to_dicts() == (
            through_arrow.match(S.prow(V.a, V.b)).to_dicts()
        )


def test_the_inward_door_names_the_extra_without_nanoarrow(m):
    """A stream-only source refuses by name rather than by falling back."""
    duckdb = pytest.importorskip("duckdb")
    from tests.ch04_spaces_and_matching.test_arrow_doors import hidden

    relation = duckdb.sql("select 1 as a")
    with hidden("nanoarrow"), pytest.raises(ImportError, match=r"pymetta\[arrow\]"):
        tables.add(m, "nrow", relation)


def test_a_bridge_streams_its_sqlite_rows(m, edges):
    """The provider declares the capability by having the method.

    polars reads the capsule on this thread; DuckDB reads it on a worker,
    which is why the fixture's connection permits cross-thread use.
    """
    polars = pytest.importorskip("polars")
    duckdb = pytest.importorskip("duckdb")

    bridge = TableBridge(
        m.parse, edges, "(bridge (edge $a $b) (row edges (a $a) (b $b)))"
    )
    frame = polars.DataFrame(bridge)
    assert frame.columns == ["a", "b"]
    assert frame.rows() == [("x", "y"), ("y", "z")]
    assert duckdb.sql("select b from bridge where a = 'x'").fetchall() == [("y",)]


def test_a_bridge_stream_types_its_columns_from_the_cells(m):
    """A numeric SQLite column is int64 in the stream, not text."""
    pa = pytest.importorskip("pyarrow")

    connection = sqlite3.connect(":memory:")
    connection.execute("create table scores (who text, points integer)")
    connection.executemany(
        "insert into scores values (?, ?)", [("ada", 3), ("bob", 5)]
    )
    bridge = TableBridge(
        m.parse, connection, "(bridge (score $w $p) (row scores (who $w) (points $p)))"
    )
    table = pa.table(bridge)
    assert table.schema.field("points").type == pa.int64()
    assert table.column("points").to_pylist() == [3, 5]


def test_a_bridge_over_two_relations_refuses_one_schema(m, edges):
    """One stream carries one schema; two column lists say so out loud."""
    edges.execute("create table nodes (n text)")
    bridge = TableBridge(
        m.parse,
        edges,
        [
            "(bridge (edge $a $b) (row edges (a $a) (b $b)))",
            "(bridge (node $n) (row nodes (n $n)))",
        ],
    )
    with pytest.raises(ValueError, match="one Arrow stream carries one schema"):
        bridge.__arrow_c_stream__()


def test_the_frame_accessors_install_for_imported_libraries(m):
    """`df.metta.into` is tables.add wearing each library's own spelling."""
    polars = pytest.importorskip("polars")
    pandas = pytest.importorskip("pandas")

    assert set(tables.accessors()) >= {"pandas", "polars"}
    assert tables.accessors() == tables.accessors()  # idempotent

    polars.DataFrame({"a": [1], "b": ["x"]}).metta.into(m, "prow")
    pandas.DataFrame({"a": [2], "b": ["y"]}).metta.into(m, head=S.prow)
    assert m.match(S.prow(V.a, V.b)).to_dicts() == [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
    ]


def test_a_head_is_a_duckdb_scalar_function(m):
    """The head carries its name, arity and arrow, so nothing is restated."""
    duckdb = pytest.importorskip("duckdb")

    m.run("(: dbl (-> Number Number))\n(= (dbl $x) (* 2 $x))")
    connection = duckdb.connect(":memory:")
    assert tables.sql_function(connection, m.fn.dbl) == "dbl"
    assert connection.sql("select dbl(21)").fetchall() == [(42.0,)]

    connection.execute("create table t (n double)")
    connection.execute("insert into t values (1), (2), (3)")
    assert connection.sql("select sum(dbl(n)) from t").fetchall() == [(12.0,)]


def test_a_duckdb_registration_needs_the_arrow(m):
    """DuckDB cannot infer types, and the refusal names the declaration."""
    duckdb = pytest.importorskip("duckdb")

    m.run("(= (undeclared $x) $x)")
    connection = duckdb.connect(":memory:")
    with pytest.raises(TypeError, match=r"declare the head's arrow"):
        tables.sql_function(connection, m.fn.undeclared)


def test_a_head_is_a_sqlite_scalar_function(m):
    """sqlite3 wants the arity alone, so an undeclared head registers too."""
    m.run("(: shout (-> String String))\n(= (shout $s) $s)")
    m.run("(= (undeclared $x) $x)")
    connection = sqlite3.connect(":memory:")
    assert tables.sql_function(connection, m.fn.shout, "shout_it") == "shout_it"
    assert connection.execute("select shout_it('hi')").fetchall() == [("hi",)]
    tables.sql_function(connection, m.fn.undeclared)
    assert connection.execute("select undeclared(4)").fetchall() == [(4,)]


def test_a_sql_function_answers_null_for_no_answer_and_refuses_several(m):
    """A scalar function has one result per row, and says so both ways."""
    m.run("(: only-one (-> Number Number))\n(= (only-one 1) 10)")
    m.run("(: both (-> Number Number))\n(= (both $x) 1)\n(= (both $x) 2)")
    connection = sqlite3.connect(":memory:")
    tables.sql_function(connection, m.fn["only-one"], "only_one")
    tables.sql_function(connection, m.fn.both)
    assert connection.execute("select only_one(1)").fetchall() == [(10,)]
    assert connection.execute("select only_one(2)").fetchall() == [(None,)]
    with pytest.raises(sqlite3.Error):
        connection.execute("select both(1)").fetchall()


def test_sql_function_refuses_a_connection_no_engine_claims(m):
    """An unclaimed connection is told the door, not guessed at.

    Which engines are known is the `sql` point's rows, so the refusal names
    them and the registration a third engine would make, rather than pushing a
    stranger's connection down whichever branch happens to be last.
    """
    m.run("(: dbl2 (-> Number Number))\n(= (dbl2 $x) (* 2 $x))")
    with pytest.raises(TypeError, match=r"no sql registration handles.*sqlite3") as raised:
        tables.sql_function(object(), m.fn.dbl2)
    assert "claims=..., define=..." in str(raised.value)
