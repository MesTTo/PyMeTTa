"""Purpose: the Rows container's sequence, copy, pickle, DataFrame, and
notebook interop surface, including named dependency refusals.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import copy
import importlib.util
import operator
import pickle

import pytest

from petta import Rows, S, V
from petta.results import _row_class


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def test_rows_to_pl_builds_the_polars_frame(m):
    pytest.importorskip("polars")

    m.add_table("score", [("ada", 3), ("bob", 5)])
    rows = m.query(S.score(V.who, V.points))
    frame = rows.to_pl()
    assert frame.columns == ["who", "points"]
    assert frame["points"].to_list() == [3, 5]
    assert frame["who"].to_list() == ["ada", "bob"]


def test_rows_to_df_builds_or_names_the_need(m):
    m.add_table("score", [("ada", 3)])
    rows = m.query(S.score(V.who, V.points))
    if importlib.util.find_spec("pandas") is None:
        with pytest.raises(ImportError, match="pandas"):
            rows.to_df()
    else:
        assert rows.to_df()["points"].tolist() == [3]


def test_rows_render_as_an_html_table():
    rows = Rows(("who", "points"), [("<ada>", 3)])
    page = rows._repr_html_()
    assert "<th>who</th>" in page and "<th>points</th>" in page
    assert "&lt;ada&gt;" in page  # cells escape; markup cannot leak through
    assert "<td>3</td>" in page


def test_rows_html_tail_is_an_explicit_count():
    rows = Rows(("n",), [(i,) for i in range(150)])
    page = rows._repr_html_()
    assert page.count("<tr>") == 1 + 100 + 1  # header, hundred rows, the tail
    assert "50 more rows" in page


def test_rows_repr_is_bounded_and_recursive():
    rows = Rows(("n", "text"), [(i, "x" * 500) for i in range(50_000)])
    rendered = repr(rows)
    assert len(rendered) < 20_000
    assert "49900 more rows" in rendered
    assert "xxxxxxxx" in rendered

    recursive = Rows(("nested",), [])
    recursive.append((recursive,))
    assert "..." in repr(recursive)


def test_rows_reject_duplicate_columns_and_wrong_row_widths():
    with pytest.raises(ValueError, match=r"duplicate.*x"):
        Rows(("x", "x"), [(1, 2)])
    with pytest.raises(ValueError, match="row 0 has 1 values for 2 columns"):
        Rows(("x", "y"), [(1,)])
    with pytest.raises(ValueError, match="row 0 has 2 values for 1 columns"):
        Rows(("x",), [(1, 2)])


def test_row_classes_are_reused_and_bounded():
    _row_class.cache_clear()
    left = Rows(("name",), [("Ada",)])
    right = Rows(("name",), [("Bob",)])
    assert type(left[0]) is type(right[0])

    for index in range(300):
        Rows((f"column_{index}",), [(index,)])
    assert _row_class.cache_info().currsize == 256


def test_rows_sequence_operations_preserve_columns():
    rows = Rows(("name", "score"), [("Ada", 3), ("Bob", 5)])
    for derived in (
        rows[:1],
        rows.copy(),
        operator.add(rows, [("Cid", 8)]),
        operator.add([("Cid", 8)], rows),
        rows * 2,
        2 * rows,
    ):
        assert isinstance(derived, Rows)
        assert derived.columns == rows.columns
        assert all(type(row)._columns == rows.columns for row in derived)
    assert rows["score"] == [3, 5]

    with pytest.raises(ValueError, match="cannot combine Rows"):
        rows + Rows(("other",), [(1,)])


def test_rows_mutations_preserve_invariants():
    rows = Rows(("name", "score"), [("Ada", 3)])
    rows.append(("Bob", 5))
    rows.insert(0, ("Cid", 8))
    rows.extend([("Dee", 13)])
    rows[0] = ("Eve", 21)
    rows[1:2] = [("Fox", 34)]
    rows += [("Gia", 55)]
    assert rows["name"] == ["Eve", "Fox", "Bob", "Dee", "Gia"]
    assert all(type(row)._columns == rows.columns for row in rows)

    with pytest.raises(ValueError, match="1 values for 2 columns"):
        rows.append(("bad",))
    with pytest.raises(ValueError, match="3 values for 2 columns"):
        rows[0] = ("bad", 1, 2)
    before = rows.copy()
    with pytest.raises(ValueError, match="1 values for 2 columns"):
        rows.extend([("valid", 89), ("bad",)])
    assert rows == before


def test_rows_copy_and_pickle_protocols():
    rows = Rows(("name", "atom"), [("Ada", S.person(S.Ada))])
    for restored in (copy.copy(rows), copy.deepcopy(rows)):
        assert isinstance(restored, Rows)
        assert restored == rows
        assert restored.columns == rows.columns
        assert restored is not rows
        assert restored[0].atom is rows[0].atom

    restored = pickle.loads(pickle.dumps(rows))
    assert isinstance(restored, Rows)
    assert restored == rows
    assert restored.columns == rows.columns
    assert restored[0].atom == rows[0].atom

    row = pickle.loads(pickle.dumps(rows[0]))
    assert row == rows[0]
    assert row._columns == rows.columns


def test_nonempty_zero_column_rows_refuse_table_but_frames_keep_row_count():
    rows = Rows((), [(), ()])
    with pytest.raises(ValueError, match="nonempty zero-column"):
        rows.table()

    pandas = pytest.importorskip("pandas")
    polars = pytest.importorskip("polars")
    assert isinstance(rows.to_df(), pandas.DataFrame)
    assert rows.to_df().shape == (2, 0)
    assert isinstance(rows.to_pl(), polars.DataFrame)
    assert rows.to_pl().shape == (2, 0)


def test_empty_zero_column_rows_remain_an_empty_table():
    assert Rows((), []).table() == {}
