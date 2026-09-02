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
    and rows_into selects that path for match(into=cls) [tested:
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
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - finalizing an Answers releases everything the engine holds for it, the
    cursor a declined count opened and never handed to the stream included
    [tested: test_a_counted_view_releases_its_engine_when_it_is_dropped;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - private item replay lets a deferred algebra route preserve those rows
    without probing the engine when its Answers view is constructed [tested:
    test_tagged_derivations_flow_through_match_and_reinterpret_without_requery;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - an Answers view crossing into a term observes exact-one cardinality and
    encodes that answer as the operand [tested:
    test_answer_views_observe_when_used_as_operands; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - Rows and Answers project caller variables by attribute, Variable key, or
    exact string key
    [tested: test_rows_share_the_answer_projection_contract; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - len on an untouched engine-backed Answers view uses its engine count door
    without populating the Python cache [tested:
    test_len_counts_an_unmaterialised_view_engine_side; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - a count source may decline a second evaluation, in which case len
    materializes the held cursor once [tested:
    test_effectful_relational_candidates_run_once_per_yield_on_fresh_list;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - the count source is told whether an iterator has already been handed out,
    so a count that would have to HOLD its answers can decline for a caller
    about to read them [measured 2026-08-26: without the hint, list() on an
    effect-bearing view paid the holding evaluation and ten corpus twins rose
    by 9 to 256 inferences; command=python
    extensions/python/tools/twin_coverage.py; commit=bbadc684deb3bdbe3426c44b64685717692c1dbc]
  - one(default=) distinguishes absence from multiplicity for both eager and
    lazy faces, while first without a default never returns None [tested:
    test_query_answers_complete_the_lazy_projection_protocol; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - the eager table doors refuse term answers instead of taking an answer
    apart into columns, and both display faces render term answers as a
    bounded list [tested test_term_answers_never_render_as_a_binding_table]
  - zip and reversed retain their lawful Sequence behavior while recording
    advisory ordering evidence for Space.lint [tested:
    test_zip_over_unordered_answers_is_lawful_and_linted,
    test_reversed_over_unordered_answers_is_lawful_and_linted; commit=acb40f1912f131ae088083d1af29b4b283019bea]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import dataclasses
import html
import importlib as _importlib
import inspect
import itertools
import reprlib
import threading
import typing
from collections import UserList
from collections.abc import Callable, Iterable, Iterator, Sequence
from difflib import get_close_matches
from functools import lru_cache
from typing import Any, Final, NamedTuple, Self, SupportsIndex, cast, overload

from ._config import config
from ._optional import require_module
from .atoms import Atom, Expression, Grounded, Symbol, Undefined, Variable, _decode, _encode
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

    Sequence operations retain this type and its columns. ``rows.name``,
    ``rows[V.name]``, and ``rows["name"]`` project a column, matching Answers,
    while integer and slice indexing follow a normal list.
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

    @overload  # type: ignore[override]
    def __getitem__(self, i: Variable) -> list[Any]: ...  # type: ignore[overload-overlap]

    @overload
    def __getitem__(self, i: str) -> list[Any]: ...

    @overload
    def __getitem__(self, i: SupportsIndex) -> Row: ...

    @overload
    def __getitem__(self, i: slice[SupportsIndex | None]) -> Rows: ...

    def __getitem__(  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self, i: SupportsIndex | slice[SupportsIndex | None] | Variable | str
    ) -> Row | Rows | list[Any]:
        if isinstance(i, (Variable, str)):
            return self._column(i.name if isinstance(i, Variable) else i)
        if isinstance(i, slice):
            return Rows(self.columns, self.data[i])
        return self.data[i]

    def __getattr__(self, name: str) -> list[Any]:  # noqa: D105  -- projection is the documented data-model extension
        try:
            return self._column(name)
        except KeyError as exc:
            raise AttributeError(str(exc)) from None

    def __dir__(self) -> list[str]:  # noqa: D105  -- completion exposes the documented projection columns
        return sorted(set(super().__dir__()) | set(self.columns))

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
        # Attribute and Variable-key projection share this implementation
        # with the cast route.
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

    def first(self, *, default: Any = _MISSING) -> Row | Any:
        """Return the first row, or the caller's explicit default."""
        if self:
            return self[0]
        if default is not _MISSING:
            return default
        msg = "first() found no rows; pass default= for absence"
        raise EngineError(msg)

    def one(self, *, default: Any = _MISSING) -> Row | Any:
        """THE row, when the query is asserted to have exactly one answer;
        none or several raise naming the count, so a lookup that silently
        picked an arbitrary row cannot hide.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if not self and default is not _MISSING:
            return default
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

            m.match(pattern).raise_for_errors()

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

        One of nine observability doors: metta.derivation answers HOW a
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
                "why() needs the match() result that retained its patterns; "
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

    def into(self, cls: type) -> list:
        """Each row as one ``cls``, matched by field name.

        ``match(..., into=cls)`` is sugar for this and says so: the
        conversion was only ever reachable through that keyword, so a
        prepared query's solve(), or any other Rows, could not ask for it
        even though rows_into() never cared where the rows came from
        [measured 2026-08-31]. build(cls) is the neighbouring method and a
        different question: it rebuilds ONE column of complete constructor
        expressions, where this maps every column onto a field.
        """
        return rows_into(self, cls)

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

            m.match(pattern).pipe(clean).pipe(score, weight=2)
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


def rows_into(rows: Rows, cls: type) -> list:
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
        "_count_source",
        "_done",
        "_error",
        "_known_length",
        "_lock",
        "_query",
        "_row_cache",
        "_source",
        "_space",
        "_target",
        "_values_demanded",
    )

    def __init__(  # noqa: D107 -- the enclosing type documents construction
        self,
        source: Iterable[T | _AnswerItem],
        *,
        columns: Iterable[str] = (),
        space: str | None = None,
        target: object = None,
        count: Callable[..., int | None] | None = None,
        query: _QueryContext | None = None,
    ) -> None:
        self._source = iter(source)
        self._columns = tuple(columns)
        self._count_source = count
        self._known_length: int | None = None
        self._space = space
        self._target = target
        self._query = query
        self._cache: list[T] = []
        self._row_cache: list[Row | None] = []
        self._done = False
        self._error: Exception | None = None
        # True once an iterator over these answers has been handed out, which
        # says the values are wanted and not just their number. `list(view)`
        # asks for an iterator BEFORE it asks for a length hint, so a count
        # source can tell it from a bare `len(view)` and skip work that only
        # pays for itself when the values are thrown away: a count that has
        # to HOLD its answers to avoid a second evaluation is pure overhead
        # for a caller about to read them anyway. It is a hint and nothing
        # else, so a Python that asked in the other order would pay that
        # overhead rather than answer differently.
        self._values_demanded = False
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

    def _iterate(self) -> Iterator[T]:
        position = 0
        while self._pull(position):
            yield self._cache[position]
            position += 1

    def __iter__(self) -> Iterator[T]:  # noqa: D105 -- Python's iteration protocol names the contract
        frame = inspect.currentframe()
        caller = None if frame is None else frame.f_back
        if self._space is not None and caller is not None:
            from ._lint_events import (  # noqa: PLC0415 -- lint remains optional
                frame_calls_builtin,
                record_event_for_name,
            )

            if frame_calls_builtin(caller, "zip"):
                record_event_for_name(
                    self._space,
                    "unordered-answers-zip",
                    "Answers",
                    caller,
                )
        self._values_demanded = True
        return self._iterate()

    def __reversed__(self) -> Iterator[T]:
        """Reverse the materialized view and retain the unordered-use lint."""
        frame = inspect.currentframe()
        caller = None if frame is None else frame.f_back
        if self._space is not None and caller is not None:
            from ._lint_events import (  # noqa: PLC0415 -- lint remains optional
                record_event_for_name,
            )

            record_event_for_name(
                self._space,
                "unordered-answers-reversed",
                "Answers",
                caller,
            )
        return reversed(self._materialize())

    def _items(self) -> Iterator[_AnswerItem]:
        """Replay values together with their private caller-row metadata."""
        self._values_demanded = True
        position = 0
        while self._pull(position):
            yield _AnswerItem(self._cache[position], self._row_cache[position])
            position += 1

    def __bool__(self) -> bool:  # noqa: D105 -- Python's truth protocol names the contract
        return self._pull(0)

    def __len__(self) -> int:  # noqa: D105 -- Python's sequence protocol names the contract
        with self._lock:
            if self._done:
                self._known_length = len(self._cache)
                return self._known_length
            if self._cache or self._count_source is None:
                self._known_length = len(self._materialize())
                return self._known_length
            if self._known_length is None:
                counted = self._count_source(values_wanted=self._values_demanded)
                if counted is None:
                    self._known_length = len(self._materialize())
                else:
                    self._known_length = counted
            return self._known_length

    @overload
    def __getitem__(self, key: int) -> T: ...

    @overload
    def __getitem__(self, key: slice) -> Answers[T]: ...

    @overload
    def __getitem__(self, key: Variable) -> Answers[Any]: ...

    @overload
    def __getitem__(self, key: str) -> Answers[Any]: ...

    def __getitem__(  # noqa: D105 -- Python's sequence protocol names the contract
        self, key: int | slice | Variable | str
    ) -> T | Answers[T] | Answers[Any]:
        if isinstance(key, (Variable, str)):
            return self._project(key.name if isinstance(key, Variable) else key)
        if isinstance(key, slice):
            return self._slice(key)
        if not isinstance(key, int):
            msg = (
                "Answers indices are integers, slices, Variables, or exact "
                f"column strings, not {type(key).__name__}"
            )
            raise TypeError(msg)
        return self._at(key)

    def _slice(self, window: slice) -> Answers[T]:
        if window.step == 0:
            msg = "slice step cannot be zero"
            raise ValueError(msg)

        def selected() -> Iterator[T | _AnswerItem]:
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
            close = get_close_matches(name, self._columns, n=1, cutoff=0.6)
            suggestion = f"; did you mean {close[0]!r}?" if close else ""
            msg = (
                f"no answer variable {name!r}; variables are "
                f"{list(self._columns)}{suggestion}"
            )
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

    def _answers_are_terms(self) -> bool:
        """Whether these answers are evaluation terms, not caller bindings.

        Reads answer zero and nothing further, so the question costs one
        pull. An empty view has nothing to look at and answers False,
        which keeps an empty match on the table face and with it the
        caption pointing at `why()`.
        """
        return self._pull(0) and not isinstance(self._cache[0], Row)

    def _eager_rows(self) -> Rows:
        """Materialize this binding view as the eager Rows face.

        Refuses term answers. `cast` states an element type and does
        nothing at runtime, so an ATOM used to reach Rows and be taken
        apart by `tuple(atom)`: over the single answer `(g $p)` to a
        two-variable call, `to_dicts()` read `{'x': 'g', 'y': '$p'}` and
        the notebook drew that as a table, presenting a head symbol as a
        binding. Answers whose arity did not line up raised from inside
        the display machinery instead.
        """
        if self._answers_are_terms():
            msg = (
                f"the table face needs caller bindings and these answers are "
                f"terms; answer 0 is {self._cache[0]!r}. Ask .rows for the "
                f"bindings behind each answer, or read the answers themselves "
                f"as a sequence"
            )
            raise TypeError(msg)
        rows = cast(Iterable[Iterable[Any]], self)
        return Rows(self._columns, rows, _query=self._query)

    def into(self, cls: type) -> list:
        """Materialize, then convert through Rows.into."""
        return self._eager_rows().into(cls)

    def build(self, *args: Any) -> list[Any]:
        """Materialize, then rebuild one column through Rows.build."""
        return self._eager_rows().build(*args)

    def to_dicts(self) -> list[dict[str, Any]]:
        """Materialize as plain column-to-value records."""
        return self._eager_rows().to_dicts()

    def table(self) -> dict[str, list[Any]]:
        """Materialize as a column mapping."""
        return self._eager_rows().table()

    def to_df(self):
        """Materialize as a pandas DataFrame."""
        return self._eager_rows().to_df()

    def to_pl(self):
        """Materialize as a polars DataFrame."""
        return self._eager_rows().to_pl()

    def pipe(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Materialize and pass the eager Rows face to ``fn``."""
        return self._eager_rows().pipe(fn, *args, **kwargs)

    def raise_for_errors(self) -> Self:
        """Raise stored error cells after materializing the row view."""
        self._eager_rows().raise_for_errors()
        return self

    def why(self) -> str:
        """Explain an empty query after materializing it."""
        return self._eager_rows().why()

    def _display_text(self) -> str:
        """Term answers as one line each, bounded by config.display_rows.

        Pulling stops at the bound rather than measuring the view, so a
        cell holding an unbounded answer stream still renders: a count
        would run the source to exhaustion and a MeTTa generator need not
        have one. The tail therefore says that more follow without
        saying how many.
        """
        shown = config.display_rows
        values: list[T] = []
        while len(values) < shown and self._pull(len(values)):
            values.append(self._cache[len(values)])
        lines = [str(value) for value in values]
        if self._pull(shown):
            lines.append("… more answers")
        return "\n".join(lines)

    def __rich__(self):
        """Render binding answers as a table and term answers as a list."""
        if self._answers_are_terms():
            return self._display_text()
        return self._eager_rows().__rich__()

    def _repr_html_(self) -> str:
        """Render binding answers as an HTML table and term answers as a list."""
        if self._answers_are_terms():
            return f"<pre>{html.escape(self._display_text())}</pre>"
        return self._eager_rows()._repr_html_()

    def __metta__(self) -> Atom:
        """Observe exactly one answer when this view enters a term."""
        return _encode(self.one())

    @staticmethod
    def _scalar(answer: Any) -> Any:
        if isinstance(answer, Undefined):
            msg = (
                "one answer was undefined; a scalar cardinality call asserts "
                "that a definite value exists"
            )
            raise EngineError(msg)
        return _decode(answer) if isinstance(answer, Grounded) else answer

    def one(self, *, default: Any = _MISSING) -> Any:
        """Return at most one decoded value, defaulting only on absence."""
        if not self._pull(0):
            if default is not _MISSING:
                return default
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

    def close(self) -> None:
        """Release the engine cursor this view holds, now rather than later.

            with metta.answers(S.fact(V.n)) as rows:
                for row in rows:
                    if enough(row):
                        break

        A lazy view owns a cursor and the engine behind it, and a view that is
        abandoned part-way holds both until the collector runs. `Space` has
        owned a resource and said so from the start, with `drop()` and the
        `with` form; this is the same vocabulary for the other type that owns
        one, which had only a finalizer.

        The finalizer stays as the backstop, and being only a backstop is the
        point: a `__del__` runs during interpreter shutdown with module globals
        already cleared, which is how an abandoned cursor printed
        "Exception ignored ... catching classes that do not inherit from
        BaseException" out of a torn-down module [measured 2026-08-31].

        Closing twice is a no-op, as it is for `drop()`. Answers already pulled
        stay readable, because they are cached values rather than engine state;
        only what has NOT been pulled is given up.
        """
        source = self._source
        close = getattr(source, "close", None)
        if callable(close):
            close()
        self._done = True

    def __enter__(self) -> Self:  # noqa: D105 -- the Python context protocol names the contract
        return self

    def __exit__(self, *_exception: object) -> None:  # noqa: D105 -- the Python context protocol names the contract
        self.close()

    def __del__(self) -> None:  # noqa: D105 -- finalization releases the owned source
        # The backstop under close(). The source owns everything the engine
        # holds for this view, which for a lazy evaluation is a cursor and the
        # engine behind it. A source that was never started owns one too, the
        # cursor a declined count opened, so the closable object the count
        # route hands over closes both; a bare generator's finally would never
        # run [source: metta/_space_execution.py, _RetainedAnswers.close; tested
        # test_a_counted_view_releases_its_engine_when_it_is_dropped].
        close = getattr(self._source, "close", None)
        if callable(close):
            close()
