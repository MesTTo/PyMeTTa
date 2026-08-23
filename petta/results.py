"""Purpose: expose eager query rows and lazy immutable evaluation answers.

A Rows is a mutable sequence of Row tuples, one per query answer, while
Answers progressively caches one evaluation source for replay, projections,
and exact-cardinality reads.
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
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Rows.to_dicts returns one Python-native mapping per row, including empty
    mappings for zero-column rows [tested test_rows_to_dicts_returns_plain_records]
  - eager query results explain empty pattern, join, and guard outcomes [tested
    test_query_rows_explain_empty_results]
  - error_answer recognizes (Error ...) by head symbol alone, so quoted and
    nested errors stay data, and raise_for_errors chains when clean [tested
    test_raise_for_errors_chains_when_clean_and_raises_one_plainly]
  - every Answers iterator replays one shared prefix, and caller-variable
    projections and slices stay Answers [tested:
    test_answers_are_lazy_cached_and_cardinality_aware,
    test_answers_project_caller_variables_and_slices_stay_answers;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - evaluation values and their caller-binding rows are parallel faces of one
    Answers cursor [tested: test_calls_keep_values_and_binding_rows;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import dataclasses
import html
import importlib as _importlib
import itertools
import reprlib
import threading
import typing
from collections import UserList
from collections.abc import Callable, Iterable, Iterator, Sequence
from difflib import get_close_matches
from functools import lru_cache
from typing import Any, Final, NamedTuple, Self, SupportsIndex, overload

from ._config import config
from ._optional import require_module
from .atoms import Atom, Expression, Grounded, Symbol, Undefined, Variable, _decode
from .errors import EngineError, MettaResultError

__all__ = ["Answers", "Row", "Rows"]

_ERROR_HEAD = Symbol("Error")
_MISSING: Final = object()
_REPR_ITEMS = 4


def error_answer(answer: object, *, space: str | None = None) -> MettaResultError | None:
    """The structured exception for an `(Error ...)` answer, or None.

    The head symbol alone decides, MeTTa's own shape `(Error culprit
    reason)`, so a quoted or nested error stays data.
    """
    if not isinstance(answer, Expression):
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
    the call without the message growing.
    """
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


class _QueryContext(NamedTuple):
    space: str
    patterns: tuple[Atom, ...]
    where: Atom | None


def _plain(value: Any) -> Any:
    """Decode a ground value and spell symbolic structure as source text."""
    if isinstance(value, Grounded):
        return _decode(value)
    return str(value) if isinstance(value, Atom) else value


class Row(tuple):
    """One answer: a tuple whose fields are the query's variable names.

    The column names live on a per-query subclass rather than on the
    instance, because a tuple subclass with empty slots has nowhere to put
    per-instance state.
    """

    __slots__ = ()
    _columns: tuple[str, ...] = ()

    def __getattr__(self, name: str) -> Any:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        try:
            return self[type(self)._columns.index(name)]
        except ValueError:
            msg = f"no column {name!r}; columns are {list(type(self)._columns)}"
            raise AttributeError(
                msg
            ) from None

    def __getitem__(self, key):  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        # A column NAME works everywhere an index does, and it is the only
        # spelling that reaches a column named like a tuple method: for a
        # query variable $count, row.count is tuple.count, row["count"] is
        # the answer.
        if isinstance(key, str):
            try:
                key = type(self)._columns.index(key)
            except ValueError:
                msg = f"no column {key!r}; columns are {list(type(self)._columns)}"
                raise KeyError(
                    msg
                ) from None
        return tuple.__getitem__(self, key)

    @reprlib.recursive_repr()
    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        inner = ", ".join(
            f"{column}={_VALUE_REPR.repr(value)}"
            for column, value in zip(type(self)._columns, self, strict=True)
        )
        return f"Row({inner})"

    def asdict(self) -> dict[str, Any]:
        """Return this row as a column-to-value mapping."""
        return dict(zip(type(self)._columns, self, strict=True))

    def __reduce__(self):  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return _restore_row, (type(self)._columns, tuple(self))


class _AnswerItem(NamedTuple):
    """One engine answer and the caller bindings produced alongside it."""

    value: Any
    row: Row | None


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

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        columns: tuple[str, ...],
        rows: Iterable[Iterable[Any]],
        *,
        _query: _QueryContext | None = None,
    ) -> None:
        columns = tuple(columns)
        duplicates = [name for i, name in enumerate(columns) if name in columns[:i]]
        if duplicates:
            msg = f"Rows column names must be unique; duplicate names: {duplicates}"
            raise ValueError(
                msg
            )
        self.columns = columns
        self._query = _query
        checked = [self._coerce_row(row, index=index) for index, row in enumerate(rows)]
        super().__init__(checked)

    def _coerce_row(self, row: Iterable[Any], *, index: int | None = None) -> Row:
        values = tuple(row)
        if len(values) != len(self.columns):
            location = f" row {index}" if index is not None else " row"
            msg = f"Rows{location} has {len(values)} values for {len(self.columns)} columns"
            raise ValueError(
                msg
            )
        return _row_class(self.columns)(values)

    @overload
    def __getitem__(self, i: SupportsIndex) -> Row: ...

    @overload
    def __getitem__(self, i: slice[SupportsIndex | None]) -> Rows: ...

    @overload
    def __getitem__(self, i: str) -> list[Any]: ...

    def __getitem__(  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self, i: SupportsIndex | slice[SupportsIndex | None] | str
    ) -> Row | Rows | list[Any]:
        if isinstance(i, str):
            return self._column(i)
        if isinstance(i, slice):
            return Rows(self.columns, self.data[i])
        return self.data[i]

    def __setitem__(  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self,
        i: SupportsIndex | slice[SupportsIndex | None],
        item: Iterable[Any] | Iterable[Iterable[Any]],
    ) -> None:
        if isinstance(i, slice):
            self.data[i] = [self._coerce_row(row) for row in item]
        else:
            self.data[i] = self._coerce_row(item)

    def insert(self, i: int, item: Iterable[Any]) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self.data.insert(i, self._coerce_row(item))

    def append(self, item: Iterable[Any]) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self.data.append(self._coerce_row(item))

    def extend(self, other: Iterable[Iterable[Any]]) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        checked = [self._coerce_row(row) for row in other]
        self.data.extend(checked)

    def copy(self) -> Rows:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return Rows(self.columns, self.data, _query=self._query)

    def __copy__(self) -> Rows:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self.copy()

    def __reduce__(self):  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        values = [tuple(row) for row in self.data]
        return _restore_rows, (self.columns, values, self._query)

    def _addition_rows(self, other: Iterable[Iterable[Any]]) -> Iterable[Iterable[Any]]:
        if isinstance(other, Rows) and other.columns != self.columns:
            msg = f"cannot combine Rows with columns {self.columns!r} and {other.columns!r}"
            raise ValueError(
                msg
            )
        return other

    def __add__(self, other: Iterable[Iterable[Any]]) -> Rows:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return Rows(self.columns, [*self.data, *self._addition_rows(other)])

    def __radd__(self, other: Iterable[Iterable[Any]]) -> Rows:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return Rows(self.columns, [*self._addition_rows(other), *self.data])

    def __iadd__(self, other: Iterable[Iterable[Any]]) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self.extend(self._addition_rows(other))
        return self

    def __mul__(self, n: int) -> Rows:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return Rows(self.columns, self.data * n)

    def __rmul__(self, n: int) -> Rows:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
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
            msg = f"no column {name!r} in {self.columns}{suggestion}"
            raise KeyError(
                msg
            )
        index = self.columns.index(name)
        return [row[index] for row in self]

    def first(self) -> Row | None:
        """The first row, or None when there are no answers: the tolerant
        accessor, SQLAlchemy's own naming.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self[0] if self else None

    def one(self) -> Row:
        """THE row, when the query is asserted to have exactly one answer;
        none or several raise naming the count, so a lookup that silently
        picked an arbitrary row cannot hide.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if len(self) != 1:
            msg = (
                f"one() expected exactly one row, got {len(self)}; "
                f"use first() for row-or-None, or iterate for all"
            )
            raise EngineError(
                msg
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
        several raise one ExceptionGroup carrying each.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
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
        msg = f"{len(errors)} error atoms across {len(self)} rows"
        raise ExceptionGroup(
            msg, errors
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
            msg = f"why() explains an empty query; this one returned {len(self)} row(s)"
            raise ValueError(
                msg
            )
        if self._query is None:
            msg = (
                "why() needs the query() result that retained its patterns; "
                "this Rows was constructed or transformed independently"
            )
            raise TypeError(
                msg
            )
        # Resolve after package initialization so eager query results stay in
        # the core import layer without a static edge back to the facade.
        diagnostics = _importlib.import_module(f"{__package__}._space_diagnostics")
        space_api = _importlib.import_module(f"{__package__}._space")
        context = self._query
        return diagnostics.explain_empty_query(
            space_api.Space(context.space),
            context.patterns,
            context.where,
        )

    @overload
    def build[BuildT](self, cls: type[BuildT], /) -> list[BuildT]: ...

    @overload
    def build[BuildT](self, column: str, cls: type[BuildT]) -> list[BuildT]: ...

    def build(self, column: str | type, cls: type | None = None) -> list:
        """Rebuild constructor atoms through the two-way translator.

        ``build(column, cls)`` projects a named column. ``build(cls)`` is the
        query reconstruction door when exactly one column holds complete
        constructor expressions.
        """
        if cls is None:
            if not isinstance(column, type):
                msg = "build(cls) needs a Python class as its sole argument"
                raise TypeError(msg)
            cls = column
            if len(self.columns) != 1:
                msg = (
                    f"build({cls.__name__}) needs exactly one query column; "
                    f"these rows have {list(self.columns)}"
                )
                raise TypeError(msg)
            column = self.columns[0]
        if not isinstance(column, str):
            msg = "build(column, cls) needs a column name"
            raise TypeError(msg)
        convert = _importlib.import_module(f"{__package__}.convert")
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
        symbols and structure become their text.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self and not self.columns:
            msg = "table() cannot represent nonempty zero-column Rows as a column mapping"
            raise ValueError(
                msg
            )

        return {
            name: [_plain(row[i]) for row in self]
            for i, name in enumerate(self.columns)
        }

    def to_df(self):
        """The rows as a pandas DataFrame, DuckDB's own conversion naming.
        pandas is the caller's dependency; its absence raises naming the
        need, and table() stays the constructor-agnostic shape.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
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
        """  # noqa: D205, D415  -- the API contract is one continuous invariant, not summary-and-body prose; the first line deliberately introduces the indented example that follows
        return fn(self, *args, **kwargs)

    def __rich__(self):
        """A real table in rich-using terminals. Only rich itself calls
        this, so the import cannot miss; plain terminals never pay it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
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
        count, never a silent cut.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
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
    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        header = ", ".join(self.columns)
        shown = config.display_rows
        body = ", ".join(repr(row) for row in self.data[:shown])
        if len(self) > shown:
            body += f", ... {len(self) - shown} more rows"
        if not self and self._query is not None:
            return f"Rows[{header}]([]; no rows, call .why())"
        return f"Rows[{header}]([{body}])"

    def __iter__(self) -> Iterator[Row]:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return iter(self.data)


def _into_fields(cls: type) -> dict[str, Any]:
    """Field name to resolved annotation for a dataclass, NamedTuple, or
    TypedDict; anything else is refused naming the three.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if dataclasses.is_dataclass(cls):
        hints = typing.get_type_hints(cls)
        return {field.name: hints.get(field.name) for field in dataclasses.fields(cls)}
    named_fields = getattr(cls, "_fields", None)
    if isinstance(cls, type) and issubclass(cls, tuple) and named_fields is not None:
        hints = typing.get_type_hints(cls)
        return {name: hints.get(name) for name in named_fields}
    if hasattr(cls, "__annotations__") and hasattr(cls, "__total__"):
        return dict(typing.get_type_hints(cls))
    msg = (
        f"into= takes a dataclass, NamedTuple, or TypedDict; "
        f"{getattr(cls, '__name__', cls)!r} is none of those"
    )
    raise TypeError(
        msg
    )


def rows_into(rows: Rows, cls: type) -> list:  # noqa: C901  -- rows_into keeps the per-annotation decode paths together so its branches share one row state
    """Each row as one cls instance, matched by field name: sqlite3's
    row_factory reading, over the existing conversion machinery. A field
    annotated with a registered class builds through the two-way
    translator; a primitive annotation decodes and is CHECKED, so a
    symbol landing in an int field is an error at the door rather than
    a surprise downstream; an unannotated field decodes plainly.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    constructor_rows: list[Any] | None = _constructor_rows(rows, cls)
    if constructor_rows is not None:
        return constructor_rows
    fields = _into_fields(cls)
    missing = [name for name in fields if name not in rows.columns]
    if missing:
        msg = (
            f"{cls.__name__} needs column(s) {missing}; the query answered "
            f"{list(rows.columns)}"
        )
        raise TypeError(
            msg
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
                    msg = f"column {name!r} answered {value!r}, not {annotation.__name__}"
                    raise TypeError(
                        msg
                    )
                if not isinstance(value, annotation):
                    msg = f"column {name!r} answered {value!r}, not {annotation.__name__}"
                    raise TypeError(
                        msg
                    )
                kwargs[name] = value
            elif annotation is Atom or (
                isinstance(annotation, type) and issubclass(annotation, Atom)
            ):
                kwargs[name] = atom
            else:
                kwargs[name] = _importlib.import_module(
                    f"{__package__}.convert"
                ).build(atom, annotation)
        built.append(cls(**kwargs))
    return built


def _constructor_rows[BuildT](rows: Rows, cls: type[BuildT]) -> list[BuildT] | None:
    """Rebuild a single complete-constructor column, or decline row shaping."""
    if len(rows.columns) != 1 or typing.is_typeddict(cls):
        return None
    try:
        registration = _importlib.import_module(
            f"{__package__}.convert"
        ).ensure_registered(cls)
    except TypeError:
        return None
    if registration.image != "expression":
        return None
    values = rows._column(rows.columns[0])
    expected = Symbol(registration.type_name)
    if not all(isinstance(value, Expression) and value.head == expected for value in values):
        return None
    return rows.build(cls)


class Answers[T](Sequence[T]):
    """A replayable view over an answer source whose size is not yet known.

    Pulling is progressive. Each iterator starts at answer zero, reads the
    shared prefix already computed, and advances the single source only when
    it reaches the frontier. The sequence has no mutation methods.
    """

    __slots__ = (
        "_cache",
        "_columns",
        "_done",
        "_error",
        "_lock",
        "_row_cache",
        "_source",
        "_space",
        "_target",
    )

    def __init__(  # noqa: D107 -- the enclosing type documents construction
        self,
        source: Iterable[T],
        *,
        columns: Iterable[str] = (),
        space: str | None = None,
        target: object = None,
    ) -> None:
        self._source = iter(source)
        self._columns = tuple(columns)
        self._space = space
        self._target = target
        self._cache: list[T] = []
        self._row_cache: list[Row | None] = []
        self._done = False
        self._error: Exception | None = None
        self._lock = threading.RLock()

    @property
    def columns(self) -> tuple[str, ...]:
        """Caller-variable names available for projection."""
        return self._columns

    def _pull(self, index: int) -> bool:
        """Ensure cache[index] exists, or report ordinary exhaustion."""
        with self._lock:
            while len(self._cache) <= index and not self._done:
                try:
                    item = next(self._source)
                    if isinstance(item, _AnswerItem):
                        self._cache.append(item.value)
                        self._row_cache.append(item.row)
                    else:
                        self._cache.append(item)
                        self._row_cache.append(None)
                except StopIteration:
                    self._done = True
                except Exception as exc:  # noqa: BLE001 -- replay requires caching the source's terminal failure unchanged
                    self._done = True
                    self._error = exc
            if len(self._cache) > index:
                return True
            if self._error is not None:
                raise self._error
            return False

    def _at(self, index: int) -> T:
        if index < 0:
            self._materialize()
            index += len(self._cache)
        if index < 0 or not self._pull(index):
            msg = "Answers index out of range"
            raise IndexError(msg)
        return self._cache[index]

    def _materialize(self) -> tuple[T, ...]:
        position = len(self._cache)
        while self._pull(position):
            position += 1
        return tuple(self._cache)

    def __iter__(self) -> Iterator[T]:  # noqa: D105 -- Python's iteration protocol names the contract
        position = 0
        while self._pull(position):
            yield self._cache[position]
            position += 1

    def __bool__(self) -> bool:  # noqa: D105 -- Python's truth protocol names the contract
        return self._pull(0)

    def __len__(self) -> int:  # noqa: D105 -- Python's sequence protocol names the contract
        return len(self._materialize())

    @overload
    def __getitem__(self, key: int) -> T: ...

    @overload
    def __getitem__(self, key: slice) -> Answers[T]: ...

    @overload
    def __getitem__(self, key: Variable) -> Answers[Any]: ...

    def __getitem__(  # noqa: D105 -- Python's sequence protocol names the contract
        self, key: int | slice | Variable
    ) -> T | Answers[T] | Answers[Any]:
        if isinstance(key, Variable):
            return self._project(key.name)
        if isinstance(key, slice):
            return self._slice(key)
        if not isinstance(key, int):
            msg = f"Answers indices are integers, slices, or Variables, not {type(key).__name__}"
            raise TypeError(msg)
        return self._at(key)

    def _slice(self, window: slice) -> Answers[T]:
        if window.step == 0:
            msg = "slice step cannot be zero"
            raise ValueError(msg)

        def selected() -> Iterator[T]:
            if any(
                value is not None and value < 0
                for value in (window.start, window.stop, window.step)
            ):
                self._materialize()
                for index in range(len(self._cache))[window]:
                    yield _AnswerItem(self._cache[index], self._row_cache[index])
                return
            indices = itertools.islice(
                itertools.count(),
                window.start or 0,
                window.stop,
                window.step or 1,
            )
            for index in indices:
                if not self._pull(index):
                    return
                yield _AnswerItem(self._cache[index], self._row_cache[index])

        return Answers(
            selected(), columns=self._columns, space=self._space, target=self._target
        )

    def _project(self, name: str) -> Answers[Any]:
        if name not in self._columns:
            msg = f"no answer variable {name!r}; variables are {list(self._columns)}"
            raise AttributeError(msg)
        index = self._columns.index(name)

        def values() -> Iterator[Any]:
            position = 0
            while self._pull(position):
                row = self._row_cache[position]
                if row is None:
                    msg = (
                        f"answer {self._cache[position]!r} carries no variable "
                        f"row for {name!r}"
                    )
                    raise TypeError(msg)
                yield row[index]
                position += 1

        return Answers(values(), space=self._space, target=self._target)

    @property
    def rows(self) -> Answers[Row]:
        """The caller-binding row paired with each evaluation answer."""

        def values() -> Iterator[Row]:
            position = 0
            while self._pull(position):
                row = self._row_cache[position]
                if row is None:
                    msg = f"answer {self._cache[position]!r} carries no variable row"
                    raise TypeError(msg)
                yield row
                position += 1

        return Answers(values(), columns=self._columns, space=self._space, target=self._target)

    def __getattr__(self, name: str) -> Answers[Any]:  # noqa: D105 -- projection is documented by the type
        return self._project(name)

    def __dir__(self) -> list[str]:  # noqa: D105 -- completion extends Python's standard directory
        return sorted(set(super().__dir__()) | set(self._columns))

    @staticmethod
    def _scalar(answer: Any) -> Any:
        if isinstance(answer, Undefined):
            msg = (
                "one answer was undefined; a scalar cardinality call asserts "
                "that a definite value exists"
            )
            raise EngineError(msg)
        return _decode(answer) if isinstance(answer, Grounded) else answer

    def one(self) -> Any:
        """Return exactly one decoded value, rejecting zero or multiplicity."""
        if not self._pull(0):
            msg = "one() expected exactly one answer, got 0"
            raise EngineError(msg)
        first = self._cache[0]
        raise_error_answers((first,), space=self._space, target=self._target)
        if self._pull(1):
            msg = "one() expected exactly one answer, got more than 1"
            raise EngineError(msg)
        return self._scalar(first)

    def first(self, *, default: Any = _MISSING) -> Any:
        """Return the first decoded value, or the caller's explicit default."""
        if not self._pull(0):
            if default is _MISSING:
                msg = "first() found no answers; pass default= for absence"
                raise EngineError(msg)
            return default
        first = self._cache[0]
        raise_error_answers((first,), space=self._space, target=self._target)
        return self._scalar(first)

    def __eq__(self, other: object) -> bool:  # noqa: D105 -- Python's equality protocol names the contract
        if isinstance(other, Answers):
            return self._materialize() == other._materialize()
        if isinstance(other, Sequence):
            return self._materialize() == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:  # noqa: D105 -- Python's hash protocol names the contract
        return hash(self._materialize())

    def __repr__(self) -> str:  # noqa: D105 -- Python's representation protocol names the contract
        shown: list[Any] = []
        for index in range(_REPR_ITEMS + 1):
            if not self._pull(index):
                break
            shown.append(self._cache[index])
        if len(shown) > _REPR_ITEMS:
            inner = ", ".join(repr(value) for value in shown[:_REPR_ITEMS])
            return f"[{inner}, ...]"
        return repr(shown)

    def __copy__(self) -> Self:  # noqa: D105 -- immutable instances copy as themselves
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:  # noqa: D105 -- immutable instances copy as themselves
        del memo
        return self

    def __del__(self) -> None:  # noqa: D105 -- finalization releases the owned source
        close = getattr(self._source, "close", None)
        if callable(close):
            close()
