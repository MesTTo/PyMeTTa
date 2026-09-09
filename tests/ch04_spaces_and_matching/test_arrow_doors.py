"""Purpose: prove the Arrow doors, the projection, the array face and the hint.

The Arrow C Data doors on Rows and Answers, the typed projection behind them,
the column's array face, and the non-draining length hint.

Every consumer is guarded by importorskip, and the producer's own dependency,
nanoarrow, is guarded once at module level: without it the doors are expected
to refuse rather than to work, and one scenario proves exactly that by hiding
the module from the import system.
Guarantees:
  - pyarrow, DuckDB, pandas 3 and polars read Rows and Answers with no glue
    [tested: this module; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - the projection's kinds, nulls, canonical text and batch layout are the
    ones the module's contract states [tested: this module; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import operator
import sys
from contextlib import contextmanager

import metta_nanoarrow  # noqa: F401  -- the arrow row that builds the capsules
import metta_numpy  # noqa: F401  -- the array row Column.__array__ reads
import metta_pandas  # noqa: F401  -- the frame row to_df() reads
import metta_polars  # noqa: F401  -- the frame row to_pl() reads
import pytest
from hypothesis import given
from hypothesis import strategies as st

import metta._catalog.arrow as _arrow
from metta import S, V, equation
from metta._atoms.factories import Atom, G, Grounded
from metta._spaces.results import Answers, Column, Rows

nanoarrow = pytest.importorskip("nanoarrow")


@contextmanager
def hidden(name):
    """Make one importable module unimportable for the block.

    A finder ahead of every other one raises the same ModuleNotFoundError the
    absent module would, which is what `optional_module` classifies, so the
    doors take the path a machine without the extra takes.
    """

    class Blocker:
        def find_spec(self, fullname, _path=None, _target=None):
            if fullname == name or fullname.startswith(f"{name}."):
                msg = f"{name} is hidden for this scenario"
                raise ModuleNotFoundError(msg, name=fullname)

    blocker = Blocker()
    saved = {
        key: module
        for key, module in sys.modules.items()
        if key == name or key.startswith(f"{name}.")
    }
    for key in saved:
        del sys.modules[key]
    sys.meta_path.insert(0, blocker)
    try:
        yield
    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(saved)


@pytest.fixture()
def people(metta):
    """Five typed columns over two answers, from a real query."""
    with metta._new_space() as space:
        space.run(
            '(person Ada 36 1.75 True "hi")\n'
            '(person Bob 41 1.80 False "yo")'
        )
        yield space.match(
            S.person(V.name, V.age, V.height, V.member, V.note), into=Rows
        )


def _schema_fields(source):
    schema = nanoarrow.c_schema(source.__arrow_c_schema__())
    return [(child.name, child.format) for child in schema.children]


def test_the_schema_types_every_column_from_its_wire_kinds(people):
    """The five wire kinds become int64, double, bool and utf8 by column."""
    assert _schema_fields(people) == [
        ("name", "u"),
        ("age", "l"),
        ("height", "g"),
        ("member", "b"),
        ("note", "u"),
    ]


def test_pyarrow_reads_the_rows_capsule_directly(people):
    """pa.table(rows) needs no conversion call and no pyarrow on our side."""
    pa = pytest.importorskip("pyarrow")

    table = pa.table(people)
    assert table.column_names == ["name", "age", "height", "member", "note"]
    assert table.num_rows == 2
    assert table.column("age").to_pylist() == [36, 41]
    assert table.column("name").to_pylist() == ["Ada", "Bob"]
    assert table.column("member").to_pylist() == [True, False]


def test_a_duckdb_replacement_scan_finds_the_rows_by_name(people):
    """`rows` in the caller's scope is a table DuckDB can select from."""
    duckdb = pytest.importorskip("duckdb")

    rows = people  # noqa: F841  -- DuckDB's replacement scan reads the caller's frame
    assert duckdb.sql(
        "select name, age from rows where age > 36"
    ).fetchall() == [("Bob", 41)]


def test_pandas_reads_the_rows_capsule_through_from_arrow(people):
    """The pandas 3 door, DataFrame.from_arrow, takes the rows themselves."""
    pandas = pytest.importorskip("pandas")
    if not hasattr(pandas.DataFrame, "from_arrow"):
        pytest.skip("pandas below 3 has no DataFrame.from_arrow")

    frame = pandas.DataFrame.from_arrow(people)
    assert list(frame.columns) == ["name", "age", "height", "member", "note"]
    assert frame["age"].tolist() == [36, 41]


def test_polars_scans_the_rows_lazily(people):
    """scan_arrow_c_stream builds a LazyFrame over the same stream."""
    polars = pytest.importorskip("polars")

    frame = polars.scan_arrow_c_stream(people).collect()
    assert frame.columns == ["name", "age", "height", "member", "note"]
    assert frame["age"].to_list() == [36, 41]


def test_to_pl_and_the_capsule_answer_the_same_frame(people):
    """Three spellings of one stream agree, and to_pl is one of them.

    `pl.DataFrame(rows)` is NOT one of them: polars' constructor tests for a
    sequence before it looks for the capsule, and Rows is a sequence, so
    `rows.arrow()` is the same data wearing only the Arrow protocol.
    """
    polars = pytest.importorskip("polars")

    through_view = polars.DataFrame(people.arrow())
    assert through_view.equals(people.to_pl())
    assert through_view.equals(polars.scan_arrow_c_stream(people).collect())
    assert through_view["height"].to_list() == [1.75, 1.8]
    assert through_view.dtypes == [
        polars.String,
        polars.Int64,
        polars.Float64,
        polars.Boolean,
        polars.String,
    ]


def test_to_pl_answers_the_same_frame_without_the_arrow_extra(people):
    """The fallback column path is the capsule path's answer, exactly.

    Both read the one projection, so a machine without nanoarrow gets the
    same values and the same types rather than a second set of answers.
    """
    pytest.importorskip("polars")

    through_capsule = people.to_pl()
    with hidden("nanoarrow"):
        through_columns = people.to_pl()
    assert through_columns.equals(through_capsule)
    assert through_columns.dtypes == through_capsule.dtypes


def test_the_arrow_doors_name_the_extra_when_nanoarrow_is_absent(people):
    """A capsule door refuses by naming pymetta[arrow], never by degrading."""
    with hidden("nanoarrow"):
        with pytest.raises(ImportError, match=r"pymetta\[arrow\]"):
            people.__arrow_c_schema__()
        with pytest.raises(ImportError, match=r"pymetta\[arrow\]"):
            people.__arrow_c_stream__()


def test_a_mixed_column_crosses_as_canonical_metta_text():
    """One column of several kinds is utf8 MeTTa text, each cell's own."""
    pa = pytest.importorskip("pyarrow")

    rows = Rows(
        ("cell",),
        [(S.Ada,), (G(3),), (G("hi"),), (V.open,), (S.pair(G(1), G(2)),)],
    )
    assert _schema_fields(rows) == [("cell", "u")]
    assert pa.table(rows).column("cell").to_pylist() == [
        "Ada",
        "3",
        '"hi"',
        "$open",
        "(pair 1 2)",
    ]


def test_an_out_of_range_integer_column_crosses_as_text():
    """A Python int wider than int64 is text, never wrapped or rounded."""
    pa = pytest.importorskip("pyarrow")

    big = 2**63
    rows = Rows(("n",), [(G(1),), (G(big),)])
    assert _schema_fields(rows) == [("n", "u")]
    assert pa.table(rows).column("n").to_pylist() == ["1", str(big)]


def test_nulls_cross_as_arrow_nulls():
    """Grounded(None) is Arrow null, and an all-null column stays utf8."""
    pa = pytest.importorskip("pyarrow")

    rows = Rows(("n", "blank"), [(G(1), G(None)), (G(None), G(None))])
    assert _schema_fields(rows) == [("n", "l"), ("blank", "u")]
    table = pa.table(rows)
    assert table.column("n").to_pylist() == [1, None]
    assert table.column("blank").to_pylist() == [None, None]


def test_an_integer_and_float_column_widens_to_double():
    """The one mixed pair that stays numeric is int with float."""
    pa = pytest.importorskip("pyarrow")

    rows = Rows(("x",), [(G(1),), (G(2.5),)])
    assert _schema_fields(rows) == [("x", "g")]
    assert pa.table(rows).column("x").to_pylist() == [1.0, 2.5]


def test_empty_rows_stream_their_columns_with_no_batches():
    """No rows still means a schema, which is what a consumer needs."""
    pa = pytest.importorskip("pyarrow")

    rows = Rows(("a", "b"), [])
    assert _schema_fields(rows) == [("a", "u"), ("b", "u")]
    table = pa.table(rows)
    assert table.num_rows == 0
    assert table.column_names == ["a", "b"]


def test_zero_column_rows_keep_their_row_count():
    """A struct with no fields still carries its length."""
    pa = pytest.importorskip("pyarrow")

    table = pa.table(Rows((), [(), (), ()]))
    assert (table.num_rows, table.num_columns) == (3, 0)


def test_the_stream_batches_double_to_the_chunk_cap():
    """Batches follow the engine cursor's policy: 1, 2, 4, ... capped at 64."""
    pa = pytest.importorskip("pyarrow")

    rows = Rows(("n",), [(G(index),) for index in range(200)])
    lengths = [batch.num_rows for batch in pa.table(rows).to_batches()]
    assert lengths == [1, 2, 4, 8, 16, 32, 64, 64, 9]
    assert sum(lengths) == 200


def test_a_requested_schema_is_honoured_or_ignored():
    """Best effort: a producible request is met, another is ignored."""
    pa = pytest.importorskip("pyarrow")

    rows = Rows(("n",), [(G(1),), (G(2),)])
    as_text = nanoarrow.c_schema(
        nanoarrow.struct([nanoarrow.Schema(nanoarrow.string(), name="n")])
    )
    honoured = pa.RecordBatchReader._import_from_c_capsule(
        rows.__arrow_c_stream__(as_text.__arrow_c_schema__())
    ).read_all()
    assert honoured.column("n").to_pylist() == ["1", "2"]

    text_rows = Rows(("n",), [(S.a,), (S.b,)])
    as_int = nanoarrow.c_schema(
        nanoarrow.struct([nanoarrow.Schema(nanoarrow.int64(), name="n")])
    )
    ignored = pa.RecordBatchReader._import_from_c_capsule(
        text_rows.__arrow_c_stream__(as_int.__arrow_c_schema__())
    ).read_all()
    assert ignored.column("n").to_pylist() == ["a", "b"]


def test_answers_stream_their_binding_rows(metta):
    """The lazy face reaches the same stream through its eager rows."""
    pa = pytest.importorskip("pyarrow")

    with metta._new_space() as space:
        space.run("(score ada 3)\n(score bob 5)")
        answers = space.match(S.score(V.who, V.points))
        table = pa.table(answers)
    assert table.column_names == ["who", "points"]
    assert table.column("points").to_pylist() == [3, 5]


def test_term_answers_refuse_the_arrow_doors(metta):
    """Evaluation answers are not bindings, and the stream says so."""
    with metta._new_space() as space:
        space += equation(S.h(V.p, V.q)).to(S.g(V.p))
        space += S.h(S.one, S.two)
        for door in (Answers.__arrow_c_stream__, Answers.__arrow_c_schema__):
            with pytest.raises(TypeError, match="table face needs caller bindings"):
                door(space.answers(S.h(V.x, V.y)))


def test_a_numeric_column_becomes_a_typed_numpy_array(people):
    """np.asarray(rows["age"]) decodes rather than boxing the atoms."""
    numpy = pytest.importorskip("numpy")

    ages = people["age"]
    assert isinstance(ages, Column)
    assert ages.name == "age"
    assert list(ages) == [G(36), G(41)]

    array = numpy.asarray(ages)
    assert array.dtype == numpy.dtype("int64")
    assert array.tolist() == [36, 41]
    assert numpy.asarray(people.height).dtype == numpy.dtype("float64")
    assert numpy.asarray(people["name"]).tolist() == ["Ada", "Bob"]
    assert numpy.asarray(ages, dtype="float64").tolist() == [36.0, 41.0]


def test_a_column_slice_is_still_a_column(people):
    """A window of a column keeps the name and the array face."""
    numpy = pytest.importorskip("numpy")

    window = people["age"][:1]
    assert isinstance(window, Column)
    assert window.name == "age"
    assert numpy.asarray(window).dtype == numpy.dtype("int64")
    assert people["age"][0] == G(36)


def test_a_column_with_nulls_leaves_its_dtype_to_numpy():
    """No fixed-width dtype holds absence, so NumPy decides."""
    numpy = pytest.importorskip("numpy")

    array = numpy.asarray(Rows(("n",), [(G(1),), (G(None),)])["n"])
    assert array.tolist() == [1, None]


def test_asking_a_column_for_a_view_refuses(people):
    """copy=False cannot be satisfied by a door that decodes."""
    numpy = pytest.importorskip("numpy")

    with pytest.raises(ValueError, match="copy=False"):
        numpy.asarray(people["age"], copy=False)


def test_length_hint_never_pulls_and_len_counts():
    """The hint answers only what is already known; len is the door that works."""
    pulled = []

    def source():
        for value in range(4):
            pulled.append(value)
            yield value

    answers = Answers(source())
    assert answers.__length_hint__() is NotImplemented
    assert pulled == []
    # operator.length_hint tries __len__ first, which is the counting door.
    assert operator.length_hint(answers) == 4
    assert pulled == [0, 1, 2, 3]
    assert answers.__length_hint__() == 4


#: Every shape a query answer's cell can take, including the ones that decide
#: a column's kind on their own: a null, an integer wider than int64, and an
#: opaque Python object with no primitive reading.
_CELLS = st.one_of(
    st.builds(G, st.integers(min_value=-(2**63), max_value=2**63 - 1)),
    st.builds(G, st.integers(min_value=2**63, max_value=2**70)),
    st.builds(G, st.floats(allow_nan=False, allow_infinity=False)),
    st.builds(G, st.booleans()),
    st.builds(G, st.text(max_size=8)),
    st.builds(G, st.none()),
    st.integers(min_value=-5, max_value=5),
    st.text(max_size=4),
    st.none(),
    st.sampled_from([S.Ada, S.b, V.open, S.pair(G(1), G(2)), G(object())]),
)


def _model_kind(cells):
    """The column-kind rule, spelled out here rather than imported.

    A differential is only worth running against an independent statement of
    the rule, so this is the contract read off the module's docstring: nulls
    decide nothing, one kind wins, int with float widens, anything else mixed
    is text, and an empty or all-null column is text.
    """
    seen = set()
    for cell in cells:
        raw = cell.value if isinstance(cell, Grounded) else cell
        if isinstance(cell, Atom) and not isinstance(cell, Grounded):
            seen.add("text")
        elif raw is None:
            continue
        elif isinstance(raw, bool):
            seen.add("bool")
        elif isinstance(raw, int) and -(2**63) <= raw <= 2**63 - 1:
            seen.add("int64")
        elif isinstance(raw, float):
            seen.add("float64")
        elif isinstance(raw, str):
            seen.add("utf8")
        else:
            seen.add("text")
    if not seen:
        return "text"
    if len(seen) == 1:
        return next(iter(seen))
    if seen <= {"int64", "float64"}:
        return "float64"
    return "text"


@given(st.lists(_CELLS, max_size=12))
def test_the_fused_pass_answers_what_two_passes_answered(cells):
    """One walk of a column derives the same kind and the same values.

    `resolve` folds the kind scan and the value render into one pass, which
    was measured as half the projection's cost; this holds it to what the
    two-pass reading answered, over every cell shape a column can hold.
    """
    kind, values = _arrow.resolve(cells)
    assert kind == _model_kind(cells)
    assert values == _arrow.values_of(cells, kind)
