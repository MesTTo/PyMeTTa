"""Purpose: query results as rows. A Rows is a mutable sequence of Row tuples, one per
answer, with the query's variable names as columns and attribute access per
column, so rows drop into unpacking, DataFrame constructors and pattern
matching without a helper in between. Eager query results retain their
patterns so an empty result can explain itself on demand.
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
  - a one-column Rows rebuilds constructor expressions through build(cls),
    and rows_into selects that path for query(into=cls) [tested:
    test_a_constructor_expression_rebuilds_through_the_query_door;
    commit=2bf66c123858feaeaf9909729db3e8700aaca546]
  - Rows.to_dicts returns one Python-native mapping per row, including empty
    mappings for zero-column rows [tested test_rows_to_dicts_returns_plain_records]
  - eager query results explain empty pattern, join, and guard outcomes [tested
    test_query_rows_explain_empty_results]
  - error_answer recognizes (Error ...) by head symbol alone, so quoted and
    nested errors stay data, and raise_for_errors chains when clean [tested
    test_raise_for_errors_chains_when_clean_and_raises_one_plainly]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import html
import reprlib
import typing
from collections import UserList
from collections.abc import Callable, Iterable, Iterator
from difflib import get_close_matches
from functools import lru_cache
from typing import Any, NamedTuple, Self, SupportsIndex, TypeVar, overload

from . import convert
from ._config import config
from ._optional import require_module
from .atoms import Atom, Expr, Gnd, Sym, decode
from .errors import EngineError, MettaResultError

__all__ = ["Row", "Rows"]

_ERROR_HEAD = Sym("Error")


def error_answer(answer: object, *, space: str | None = None) -> MettaResultError | None:
    """The structured exception for an `(Error ...)` answer, or None.

    The head symbol alone decides, MeTTa's own shape `(Error culprit
    reason)`, so a quoted or nested error stays data.
    """
    if not isinstance(answer, Expr):
        return None
    parts = answer.children
    if not parts or parts[0] != _ERROR_HEAD:
        return None
    culprit = parts[1] if len(parts) > 1 else None
    reason = parts[2] if len(parts) > 2 else None
    return MettaResultError(
        f"the answer is an error: {answer}",
        atom=answer,
        culprit=culprit,
        reason=reason,
        space=space,
    )


def raise_error_answers(
    answers: Iterable[object], *, space: str | None = None, target: object = None
) -> None:
    """Raise the first `(Error ...)` member of answers, if any.

    The check every single-value door runs before decoding: an error
    among the answers is the evaluation reporting failure, and failure
    outranks a count. The target rides as a note, so the traceback names
    the call without the message growing."""
    for answer in answers:
        error = error_answer(answer, space=space)
        if error is not None:
            if target is not None:
                error.add_note(f"while evaluating {target}")
            raise error

_VALUE_REPR = reprlib.Repr()
_VALUE_REPR.maxlevel = 4
_VALUE_REPR.maxstring = 80
_VALUE_REPR.maxother = 120
_BuildT = TypeVar("_BuildT")


class _QueryContext(NamedTuple):
    space: str
    patterns: tuple[Atom, ...]
    where: Atom | None


def _plain(value: Any) -> Any:
    """Decode a ground value and spell symbolic structure as source text."""
    if isinstance(value, Gnd):
        return decode(value)
    return str(value) if isinstance(value, Atom) else value


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


def _restore_rows(
    columns: tuple[str, ...],
    values: list[tuple[Any, ...]],
    query: _QueryContext | None,
) -> Rows:
    return Rows(columns, values, _query=query)


class Rows(UserList[Row]):
    """Every answer to a query, in the order the engine produced them.

    Sequence operations retain this type and its columns. ``rows["name"]``
    projects a column, while integer and slice indexing follow a normal list.
    """

    def __init__(
        self,
        columns: tuple[str, ...],
        rows: Iterable[Iterable[Any]],
        *,
        _query: _QueryContext | None = None,
    ) -> None:
        columns = tuple(columns)
        duplicates = [name for i, name in enumerate(columns) if name in columns[:i]]
        if duplicates:
            raise ValueError(
                f"Rows column names must be unique; duplicate names: {duplicates}"
            )
        self.columns = columns
        self._query = _query
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
            return self._column(i)
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
        return Rows(self.columns, self.data, _query=self._query)

    def __copy__(self) -> Rows:
        return self.copy()

    def __reduce__(self):
        values = [tuple(row) for row in self.data]
        return _restore_rows, (self.columns, values, self._query)

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

    def _column(self, name: str) -> list[Any]:
        #rows[name] is the one public door; this is its implementation,
        #shared with the cast route.
        if name not in self.columns:
            # tuple.index would otherwise report this as
            # "tuple.index(x): x not in tuple", naming neither the column
            # asked for nor the ones that exist.
            close = get_close_matches(str(name), self.columns, n=1, cutoff=0.6)
            suggestion = f"; did you mean {close[0]!r}?" if close else ""
            raise KeyError(
                f"no column {name!r} in {self.columns}{suggestion}"
            )
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
            raise EngineError(
                f"one() expected exactly one row, got {len(self)}; "
                f"use first() for row-or-None, or iterate for all"
            )
        return self[0]

    def raise_for_errors(self) -> Self:
        """Raise when any cell carries an `(Error ...)` atom; answer self
        otherwise, so the call chains.

            m.query(pattern).raise_for_errors()

        Query rows are BINDINGS, not evaluation answers, so a stored
        error record stays data through every Rows door, one() and
        first() included; this is the explicit bridge for callers who
        want the raise_for_status reading. One error raises it plainly,
        several raise one ExceptionGroup carrying each."""
        errors = [
            error
            for row in self
            for cell in row
            if (error := error_answer(cell)) is not None
        ]
        if not errors:
            return self
        if len(errors) == 1:
            raise errors[0]
        raise ExceptionGroup(
            f"{len(errors)} error atoms across {len(self)} rows", errors
        )

    def why(self) -> str:
        """Explain why this eager query returned no rows.

        The explanation reads the space's current state. A nonempty result
        has nothing to explain, and a manually constructed or transformed
        Rows has no query to inspect, so both uses fail loudly.

        One of nine observability doors: petta.derivation answers HOW a
        result was derived, and prepare(...).explain() answers what a
        query will do before it runs; the guide's observability page maps
        the family.
        """
        if self:
            raise ValueError(
                f"why() explains an empty query; this one returned {len(self)} row(s)"
            )
        if self._query is None:
            raise TypeError(
                "why() needs the query() result that retained its patterns; "
                "this Rows was constructed or transformed independently"
            )
        # Import after package initialization to break results -> space ->
        # results while keeping the retained context serializable.
        from ._space_diagnostics import explain_empty_query  # noqa: PLC0415
        from .space import MeTTa  # noqa: PLC0415

        context = self._query
        return explain_empty_query(
            MeTTa(context.space),
            context.patterns,
            context.where,
        )

    @overload
    def build(self, cls: type[_BuildT], /) -> list[_BuildT]: ...

    @overload
    def build(self, column: str, cls: type[_BuildT]) -> list[_BuildT]: ...

    def build(self, column: str | type, cls: type | None = None) -> list:
        """Rebuild constructor atoms through the two-way translator.

        ``build(column, cls)`` projects a named column. ``build(cls)`` is the
        query reconstruction door when exactly one column holds complete
        constructor expressions.
        """
        if cls is None:
            if not isinstance(column, type):
                raise TypeError("build(cls) needs a Python class as its sole argument")
            cls = column
            if len(self.columns) != 1:
                raise TypeError(
                    f"build({cls.__name__}) needs exactly one query column; "
                    f"these rows have {list(self.columns)}"
                )
            column = self.columns[0]
        if not isinstance(column, str):
            raise TypeError("build(column, cls) needs a column name")
        return [convert.build(value, cls) for value in self._column(column)]

    def to_dicts(self) -> list[dict[str, Any]]:
        """Return one Python-native column-to-value mapping per row."""
        return [
            {
                name: _plain(value)
                for name, value in zip(self.columns, row, strict=True)
            }
            for row in self
        ]

    def table(self) -> dict[str, list[Any]]:
        """The columns as a dict of plain values, the one shape every
        DataFrame constructor takes: pl.DataFrame(rows.table()),
        pd.DataFrame(rows.table()). Grounded values unwrap to Python;
        symbols and structure become their text."""
        if self and not self.columns:
            raise ValueError(
                "table() cannot represent nonempty zero-column Rows as a column mapping"
            )

        return {
            name: [_plain(row[i]) for row in self]
            for i, name in enumerate(self.columns)
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

    def pipe(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """fn(self, *args, **kwargs), pandas' chaining shape, so a
        pipeline reads left to right instead of inside out:

            m.query(pattern).pipe(clean).pipe(score, weight=2)
        """
        return fn(self, *args, **kwargs)

    def __rich__(self):
        """A real table in rich-using terminals. Only rich itself calls
        this, so the import cannot miss; plain terminals never pay it."""
        from rich.table import Table  # noqa: PLC0415  rich's own protocol call

        if not self.columns:
            return repr(self)
        shown = config.display_rows
        caption = None
        if len(self) > shown:
            caption = f"\u2026 {len(self) - shown} more rows"
        elif not self and self._query is not None:
            caption = "No rows. rows.why() explains."
        table = Table(*[str(c) for c in self.columns], caption=caption)
        for row in self[:shown]:
            table.add_row(*[str(v) for v in row])
        return table

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
        caption = (
            "<caption>No rows. Call <code>rows.why()</code> to explain.</caption>"
            if not self and self._query is not None
            else ""
        )
        return (
            "<table style='font-family: monospace; border-collapse: collapse;'>"
            f"{caption}<thead><tr>{head}</tr></thead><tbody>{body}{rest}</tbody></table>"
        )

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        header = ", ".join(self.columns)
        shown = config.display_rows
        body = ", ".join(repr(row) for row in self.data[:shown])
        if len(self) > shown:
            body += f", ... {len(self) - shown} more rows"
        if not self and self._query is not None:
            return f"Rows[{header}]([]; no rows, call .why())"
        return f"Rows[{header}]([{body}])"

    def __iter__(self) -> Iterator[Row]:
        return iter(self.data)


def _into_fields(cls: type) -> dict[str, Any]:
    """Field name to resolved annotation for a dataclass, NamedTuple, or
    TypedDict; anything else is refused naming the three."""
    if dataclasses.is_dataclass(cls):
        hints = typing.get_type_hints(cls)
        return {field.name: hints.get(field.name) for field in dataclasses.fields(cls)}
    named_fields = getattr(cls, "_fields", None)
    if isinstance(cls, type) and issubclass(cls, tuple) and named_fields is not None:
        hints = typing.get_type_hints(cls)
        return {name: hints.get(name) for name in named_fields}
    if hasattr(cls, "__annotations__") and hasattr(cls, "__total__"):
        return dict(typing.get_type_hints(cls))
    raise TypeError(
        f"into= takes a dataclass, NamedTuple, or TypedDict; "
        f"{getattr(cls, '__name__', cls)!r} is none of those"
    )


def rows_into(rows: Rows, cls: type) -> list:
    """Each row as one cls instance, matched by field name: sqlite3's
    row_factory reading, over the existing conversion machinery. A field
    annotated with a registered class builds through the two-way
    translator; a primitive annotation decodes and is CHECKED, so a
    symbol landing in an int field is an error at the door rather than
    a surprise downstream; an unannotated field decodes plainly."""
    constructor_rows: list[Any] | None = _constructor_rows(rows, cls)
    if constructor_rows is not None:
        return constructor_rows
    fields = _into_fields(cls)
    missing = [name for name in fields if name not in rows.columns]
    if missing:
        raise TypeError(
            f"{cls.__name__} needs column(s) {missing}; the query answered "
            f"{list(rows.columns)}"
        )
    indices = {name: rows.columns.index(name) for name in fields}
    primitives = (str, int, float, bool)
    built = []
    for row in rows:
        kwargs = {}
        for name, annotation in fields.items():
            atom = row[indices[name]]
            if annotation in (None, Any):
                kwargs[name] = _plain(atom)
            elif annotation in primitives:
                value = _plain(atom)
                if annotation is float and isinstance(value, int) and not isinstance(value, bool):
                    value = float(value)
                if isinstance(value, bool) and annotation is not bool:
                    raise TypeError(
                        f"column {name!r} answered {value!r}, not {annotation.__name__}"
                    )
                if not isinstance(value, annotation):
                    raise TypeError(
                        f"column {name!r} answered {value!r}, not {annotation.__name__}"
                    )
                kwargs[name] = value
            elif annotation is Atom or (
                isinstance(annotation, type) and issubclass(annotation, Atom)
            ):
                kwargs[name] = atom
            else:
                kwargs[name] = convert.build(atom, annotation)
        built.append(cls(**kwargs))
    return built


def _constructor_rows(rows: Rows, cls: type[_BuildT]) -> list[_BuildT] | None:
    """Rebuild a single complete-constructor column, or decline row shaping."""
    if len(rows.columns) != 1 or typing.is_typeddict(cls):
        return None
    try:
        registration = convert.ensure_registered(cls)
    except TypeError:
        return None
    if registration.image != "expression":
        return None
    values = rows._column(rows.columns[0])
    expected = Sym(registration.type_name)
    if not all(isinstance(value, Expr) and value.head == expected for value in values):
        return None
    return rows.build(cls)
