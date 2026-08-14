"""Purpose: query results as rows. A Rows is a mutable sequence of Row tuples, one per
answer, with the query's variable names as columns and attribute access per
column, so rows drop into unpacking, DataFrame constructors and pattern
matching without a helper in between.
Guarantees:
  - Rows with the same columns share one bounded cached Row subclass [tested
    test_row_classes_are_reused_and_bounded]
  - slicing, copying, concatenation, and repetition preserve Rows and its
    columns [tested test_rows_sequence_operations_preserve_columns]
  - every mutation validates row width and preserves the named Row type
    [tested test_rows_mutations_preserve_invariants]
  - Row and Rows pickle through stable module-level rebuild functions rather
    than dynamic class names [tested test_rows_copy_and_pickle_protocols]
  - terminal representations bound both rows and individual values and state
    the omitted row count [tested test_rows_repr_is_bounded_and_recursive]
  - Rows.build preserves its requested class as the list element type [tested
    test_target_type_overloads_preserve_the_requested_class]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import html
import reprlib
from collections import UserList
from collections.abc import Iterable, Iterator
from functools import lru_cache
from typing import Any, Self, SupportsIndex, TypeVar, overload

from . import convert
from ._config import config
from ._optional import require_module
from .atoms import Gnd, decode

__all__ = ["Row", "Rows"]

_VALUE_REPR = reprlib.Repr()
_VALUE_REPR.maxlevel = 4
_VALUE_REPR.maxstring = 80
_VALUE_REPR.maxother = 120
_BuildT = TypeVar("_BuildT")


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

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        inner = ", ".join(
            f"{column}={_VALUE_REPR.repr(value)}"
            for column, value in zip(type(self)._columns, self, strict=True)
        )
        return f"Row({inner})"

    def asdict(self) -> dict[str, Any]:
        """Return this row as a column-to-value mapping."""
        return dict(zip(type(self)._columns, self, strict=True))

    def __reduce__(self):
        return _restore_row, (type(self)._columns, tuple(self))


@lru_cache(maxsize=256)
def _row_class(columns: tuple[str, ...]) -> type[Row]:
    return type("Row", (Row,), {"__slots__": (), "_columns": columns})


def _restore_row(columns: tuple[str, ...], values: tuple[Any, ...]) -> Row:
    return _row_class(columns)(values)


class Rows(UserList[Row]):
    """Every answer to a query, in the order the engine produced them.

    Sequence operations retain this type and its columns. ``rows["name"]``
    projects a column, while integer and slice indexing follow a normal list.
    """

    def __init__(self, columns: tuple[str, ...], rows: Iterable[Iterable[Any]]) -> None:
        columns = tuple(columns)
        duplicates = [name for i, name in enumerate(columns) if name in columns[:i]]
        if duplicates:
            raise ValueError(
                f"Rows column names must be unique; duplicate names: {duplicates}"
            )
        self.columns = columns
        checked = [self._coerce_row(row, index=index) for index, row in enumerate(rows)]
        super().__init__(checked)

    def _coerce_row(self, row: Iterable[Any], *, index: int | None = None) -> Row:
        values = tuple(row)
        if len(values) != len(self.columns):
            location = f" row {index}" if index is not None else " row"
            raise ValueError(
                f"Rows{location} has {len(values)} values for {len(self.columns)} columns"
            )
        return _row_class(self.columns)(values)

    @overload
    def __getitem__(self, i: SupportsIndex) -> Row: ...

    @overload
    def __getitem__(self, i: slice[SupportsIndex | None]) -> Rows: ...

    @overload
    def __getitem__(self, i: str) -> list[Any]: ...

    def __getitem__(
        self, i: SupportsIndex | slice[SupportsIndex | None] | str
    ) -> Row | Rows | list[Any]:
        if isinstance(i, str):
            return self.column(i)
        if isinstance(i, slice):
            return Rows(self.columns, self.data[i])
        return self.data[i]

    def __setitem__(
        self,
        i: SupportsIndex | slice[SupportsIndex | None],
        item: Iterable[Any] | Iterable[Iterable[Any]],
    ) -> None:
        if isinstance(i, slice):
            self.data[i] = [self._coerce_row(row) for row in item]
        else:
            self.data[i] = self._coerce_row(item)

    def insert(self, i: int, item: Iterable[Any]) -> None:
        self.data.insert(i, self._coerce_row(item))

    def append(self, item: Iterable[Any]) -> None:
        self.data.append(self._coerce_row(item))

    def extend(self, other: Iterable[Iterable[Any]]) -> None:
        checked = [self._coerce_row(row) for row in other]
        self.data.extend(checked)

    def copy(self) -> Rows:
        return Rows(self.columns, self.data)

    def __copy__(self) -> Rows:
        return self.copy()

    def __reduce__(self):
        values = [tuple(row) for row in self.data]
        return Rows, (self.columns, values)

    def _addition_rows(self, other: Iterable[Iterable[Any]]) -> Iterable[Iterable[Any]]:
        if isinstance(other, Rows) and other.columns != self.columns:
            raise ValueError(
                f"cannot combine Rows with columns {self.columns!r} and {other.columns!r}"
            )
        return other

    def __add__(self, other: Iterable[Iterable[Any]]) -> Rows:
        return Rows(self.columns, [*self.data, *self._addition_rows(other)])

    def __radd__(self, other: Iterable[Iterable[Any]]) -> Rows:
        return Rows(self.columns, [*self._addition_rows(other), *self.data])

    def __iadd__(self, other: Iterable[Iterable[Any]]) -> Self:
        self.extend(self._addition_rows(other))
        return self

    def __mul__(self, n: int) -> Rows:
        return Rows(self.columns, self.data * n)

    def __rmul__(self, n: int) -> Rows:
        return self * n

    def column(self, name: str) -> list[Any]:
        """Return one named column as a list."""
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

    def build(self, column: str, cls: type[_BuildT]) -> list[_BuildT]:
        """One column's atoms rebuilt as instances of cls, through the
        two-way translator: typed rows, one call."""
        return [convert.build(value, cls) for value in self.column(column)]

    def table(self) -> dict[str, list[Any]]:
        """The columns as a dict of plain values, the one shape every
        DataFrame constructor takes: pl.DataFrame(rows.table()),
        pd.DataFrame(rows.table()). Grounded values unwrap to Python;
        symbols and structure become their text."""
        if self and not self.columns:
            raise ValueError(
                "table() cannot represent nonempty zero-column Rows as a column mapping"
            )

        def plain(value: Any) -> Any:
            return decode(value) if isinstance(value, Gnd) else str(value)

        return {
            name: [plain(row[i]) for row in self] for i, name in enumerate(self.columns)
        }

    def to_df(self):
        """The rows as a pandas DataFrame, DuckDB's own conversion naming.
        pandas is the caller's dependency; its absence raises naming the
        need, and table() stays the constructor-agnostic shape."""
        pandas = require_module(
            "pandas",
            "to_df() builds a pandas DataFrame and pandas is not installed; "
            "rows.table() is the plain dict any frame constructor takes",
        )
        if self and not self.columns:
            return pandas.DataFrame([{} for _ in self])
        return pandas.DataFrame(self.table())

    def to_pl(self):
        """The rows as a polars DataFrame; the polars twin of to_df()."""
        polars = require_module(
            "polars",
            "to_pl() builds a polars DataFrame and polars is not installed; "
            "rows.table() is the plain dict any frame constructor takes",
        )
        if self and not self.columns:
            return polars.DataFrame([{} for _ in self])
        return polars.DataFrame(self.table())

    def _repr_html_(self) -> str:
        """Notebook display: the columns as a header, one row per answer,
        every cell escaped. Past config.display_rows the tail is an explicit
        count, never a silent cut."""
        shown = config.display_rows
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

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        header = ", ".join(self.columns)
        shown = config.display_rows
        body = ", ".join(repr(row) for row in self.data[:shown])
        if len(self) > shown:
            body += f", ... {len(self) - shown} more rows"
        return f"Rows[{header}]([{body}])"

    def __iter__(self) -> Iterator[Row]:
        return iter(self.data)
