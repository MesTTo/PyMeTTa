"""Purpose: query results as rows. A Rows is a list of Row tuples, one per
answer, with the query's variable names as columns and attribute access per
column, so rows drop into unpacking, DataFrame constructors and pattern
matching without a helper in between.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Iterator

__all__ = ["Row", "Rows"]


class Row(tuple):
    """One answer: a tuple whose fields are the query's variable names.

    The column names live on a per-query subclass rather than on the
    instance, because a tuple subclass with empty slots has nowhere to put
    per-instance state.
    """

    __slots__ = ()
    _columns: tuple[str, ...] = ()

    def __getattr__(self, name: str) -> Any:
        try:
            return self[type(self)._columns.index(name)]
        except ValueError:
            raise AttributeError(
                f"no column {name!r}; columns are {list(type(self)._columns)}"
            ) from None

    def __getitem__(self, key):
        # A column NAME works everywhere an index does, and it is the only
        # spelling that reaches a column named like a tuple method: for a
        # query variable $count, row.count is tuple.count, row["count"] is
        # the answer.
        if isinstance(key, str):
            try:
                key = type(self)._columns.index(key)
            except ValueError:
                raise KeyError(
                    f"no column {key!r}; columns are {list(type(self)._columns)}"
                ) from None
        return tuple.__getitem__(self, key)

    def __repr__(self) -> str:
        inner = ", ".join(f"{c}={v!r}" for c, v in zip(type(self)._columns, self))
        return f"Row({inner})"

    def asdict(self) -> dict[str, Any]:
        return dict(zip(type(self)._columns, self))


def _row_class(columns: tuple[str, ...]) -> type[Row]:
    cls = type("Row", (Row,), {"__slots__": (), "_columns": columns})
    return cls


class Rows(list):
    """Every answer to a query, in the order the engine produced them.

    A list, so len, iteration, indexing and slicing behave as expected;
    columns names the variables. column(name) projects one column out.
    """

    __slots__ = ("columns",)

    def __init__(self, columns: tuple[str, ...], rows: list[tuple]) -> None:
        columns = tuple(columns)
        duplicates = [
            name for i, name in enumerate(columns) if name in columns[:i]
        ]
        if duplicates:
            raise ValueError(
                f"Rows column names must be unique; duplicate names: {duplicates}"
            )
        checked = []
        for index, row in enumerate(rows):
            values = tuple(row)
            if len(values) != len(columns):
                raise ValueError(
                    f"Rows row {index} has {len(values)} values for "
                    f"{len(columns)} columns"
                )
            checked.append(values)
        cls = _row_class(columns)
        super().__init__(cls(r) for r in checked)
        self.columns = columns

    def column(self, name: str) -> list[Any]:
        index = self.columns.index(name)
        return [row[index] for row in self]

    def first(self) -> Row | None:
        """The first row, or None when there are no answers: the tolerant
        accessor, SQLAlchemy's own naming."""
        return self[0] if self else None

    def one(self) -> Row:
        """THE row, when the query is asserted to have exactly one answer;
        none or several raise naming the count, so a lookup that silently
        picked an arbitrary row cannot hide."""
        if len(self) != 1:
            raise ValueError(
                f"one() expected exactly one row, got {len(self)}; "
                f"use first() for row-or-None, or iterate for all"
            )
        return self[0]

    def build(self, column: str, cls: type) -> list[Any]:
        """One column's atoms rebuilt as instances of cls, through the
        two-way translator: typed rows, one call."""
        from . import convert

        return [convert.build(value, cls) for value in self.column(column)]

    def table(self) -> dict[str, list[Any]]:
        """The columns as a dict of plain values, the one shape every
        DataFrame constructor takes: pl.DataFrame(rows.table()),
        pd.DataFrame(rows.table()). Grounded values unwrap to Python;
        symbols and structure become their text."""
        from .atoms import Gnd, decode

        if self and not self.columns:
            raise ValueError(
                "table() cannot represent nonempty zero-column Rows as a "
                "column mapping"
            )

        def plain(value: Any) -> Any:
            return decode(value) if isinstance(value, Gnd) else str(value)

        return {
            name: [plain(row[i]) for row in self]
            for i, name in enumerate(self.columns)
        }

    def to_df(self):
        """The rows as a pandas DataFrame, DuckDB's own conversion naming.
        pandas is the caller's dependency; its absence raises naming the
        need, and table() stays the constructor-agnostic shape."""
        try:
            import pandas
        except ImportError as missing:
            raise ImportError(
                "to_df() builds a pandas DataFrame and pandas is not "
                "installed; rows.table() is the plain dict any frame "
                "constructor takes"
            ) from missing
        if self and not self.columns:
            return pandas.DataFrame([{} for _ in self])
        return pandas.DataFrame(self.table())

    def to_pl(self):
        """The rows as a polars DataFrame; the polars twin of to_df()."""
        try:
            import polars
        except ImportError as missing:
            raise ImportError(
                "to_pl() builds a polars DataFrame and polars is not "
                "installed; rows.table() is the plain dict any frame "
                "constructor takes"
            ) from missing
        if self and not self.columns:
            return polars.DataFrame([{} for _ in self])
        return polars.DataFrame(self.table())

    def _repr_html_(self) -> str:
        """Notebook display: the columns as a header, one row per answer,
        every cell escaped. Past 100 rows the tail is an explicit count,
        never a silent cut."""
        import html

        shown = 100
        head = "".join(f"<th>{html.escape(str(c))}</th>" for c in self.columns)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>"
            for row in self[:shown]
        )
        rest = (
            f"<tr><td colspan={max(len(self.columns), 1)}>"
            f"&#8230; {len(self) - shown} more rows</td></tr>"
            if len(self) > shown
            else ""
        )
        return (
            "<table style='font-family: monospace; border-collapse: collapse;'>"
            f"<thead><tr>{head}</tr></thead><tbody>{body}{rest}</tbody></table>"
        )

    def __repr__(self) -> str:
        header = ", ".join(self.columns)
        return f"Rows[{header}]({super().__repr__()})"

    def __iter__(self) -> Iterator[Row]:
        return super().__iter__()
