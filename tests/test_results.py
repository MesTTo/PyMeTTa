"""Purpose: the Rows container's interop surface: DataFrame conversions
with named-need refusals when the library is absent, and notebook display.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import Rows, S, V


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
    try:
        import pandas  # noqa: F401
    except ImportError:
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


def test_rows_reject_duplicate_columns_and_wrong_row_widths():
    with pytest.raises(ValueError, match="duplicate.*x"):
        Rows(("x", "x"), [(1, 2)])
    with pytest.raises(ValueError, match="row 0 has 1 values for 2 columns"):
        Rows(("x", "y"), [(1,)])
    with pytest.raises(ValueError, match="row 0 has 2 values for 1 columns"):
        Rows(("x",), [(1, 2)])


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
