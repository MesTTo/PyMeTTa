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
        cls = _row_class(tuple(columns))
        super().__init__(cls(r) for r in rows)
        self.columns = tuple(columns)

    def column(self, name: str) -> list[Any]:
        index = self.columns.index(name)
        return [row[index] for row in self]

    def build(self, column: str, cls: type) -> list[Any]:
        """One column's atoms rebuilt as instances of cls, through the
        two-way translator: typed rows, one call."""
        from . import convert

        return [convert.build(value, cls) for value in self.column(column)]

    def __repr__(self) -> str:
        header = ", ".join(self.columns)
        return f"Rows[{header}]({super().__repr__()})"

    def __iter__(self) -> Iterator[Row]:
        return super().__iter__()
