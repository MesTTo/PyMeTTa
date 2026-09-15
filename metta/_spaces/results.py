"""Purpose: expose eager query rows and lazy immutable evaluation answers.

A Rows is a mutable sequence of Row tuples, one per query answer, while
Answers progressively caches one evaluation source for replay, projections,
and exact-cardinality reads.
Guarantees:
  - Answers preserves broad sequence equality and is unhashable, so equal
    strings, bytes, ranges and tuples cannot become inconsistent dictionary
    keys [tested: test_audit_a3_broad_sequence_equality_is_unhashable;
    commit=4ecded66c4478341c5010c8f242d3c727ec0cf8f]
  - one immutable record retains each value and caller row through replay,
    slicing, source failure and asynchronous projection after close [tested:
    test_answer_record_survives_replay_slice_and_async_projection,
    test_closed_answer_record_replays_both_faces_without_resuming_source;
    commit=96b907668ca5afde3cdaddd29bbdbe7ca506c953]
  - context exit retains body and cleanup failures together, including
    cancellation, while single failures keep their identity [tested:
    test_owned_views_preserve_body_and_cleanup_errors,
    test_owned_exit_zero_one_or_two_failures; commit=4a3266c7354990618de5d9489f4e094f5a80c5b6]
  - row conversion follows named constructor inputs and native defaults,
    including positional-only, keyword-only and InitVar parameters, while
    omitted optional TypedDict keys stay absent [tested:
    test_rows_into_uses_constructor_inputs,
    test_registered_constructor_binds_positional_only_and_keyword_only_inputs,
    test_dataclass_factory_and_initvar_are_constructor_inputs,
    test_namedtuple_constructor_defaults_are_optional_columns,
    test_typed_mapping_keeps_omitted_optional_keys_absent; commit=c07bb08a0553f5e4e542baf7913b548327277bde]
  - Answers positions and slice bounds use Python's lossless index protocol
    without pulling beyond the selected prefix [tested:
    test_answers_accepts_index_protocol_like_rows,
    test_answers_slices_use_lossless_indices_without_extra_pulls; commit=e882171509ff90183b34f24da3189e6136695312]
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
  - both result faces render a template with the receiver bound as ``rows``,
    and answer the same text for the same rows, so a report written over one
    renders the other [tested: test_a_table_renders_the_columns_and_every_row,
    test_the_lazy_face_binds_the_same_name; commit=adb831d29a48596d3068a3087115b216c18b5b38]
  - ``format(result, spec)`` reaches the same rendering table as
    ``metta.render``, and ``format(result, "")`` stays ``str`` [tested:
    test_the_format_protocol_reaches_the_same_table,
    test_an_empty_spec_is_str_and_python_specs_still_work; commit=adb831d29a48596d3068a3087115b216c18b5b38]
  - eager query results explain empty pattern, join, and guard outcomes [tested
    test_query_rows_explain_empty_results]
  - both query-result views re-explain the match form they came from, and the
    lazy one pulls nothing to do it [tested:
    test_rows_explain_re_explains_the_query_that_produced_them,
    test_a_rows_with_no_query_behind_it_refuses_to_explain; commit=3287d4dd4928f09ce7c111d05a1c516808e226d5]
  - error_answer recognizes (Error ...) by head symbol alone, so quoted and
    nested errors stay data, and raise_for_errors chains when clean [tested
    test_raise_for_errors_chains_when_clean_and_raises_one_plainly]
  - every Answers iterator replays one shared prefix, and caller-variable
    projections and slices stay Answers [tested:
    test_answers_are_lazy_cached_and_cardinality_aware,
    test_answers_project_caller_variables_and_slices_stay_answers;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - a nonnegative bounded slice of an untouched view offers its stop as the
    producer bound before either source starts, while any prior observation
    keeps the original shared cursor [tested:
    test_only_a_pristine_bounded_slice_offers_its_stop_to_the_source;
    commit=2e627a593413191cda3170f2eb716835f7f62543]
  - evaluation values and their caller-binding rows are parallel faces of one
    Answers cursor [tested: test_calls_keep_values_and_binding_rows;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - finalizing an Answers releases everything the engine holds for it, the
    cursor a declined count opened and never handed to the stream included
    [tested: test_a_counted_view_releases_its_engine_when_it_is_dropped;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - caller inspection for ordering lint breaks its frame reference before
    returning, so dropping an iterated view closes its engine immediately
    [tested:
    test_iteration_does_not_delay_answer_finalization_in_a_frame_cycle;
    commit=853623455cdb02fe0afc1c815023a45c4a0eb989]
  - private item replay lets a deferred algebra route preserve those rows
    without probing the engine when its Answers view is constructed [tested:
    test_tagged_derivations_flow_through_match_and_reinterpret_without_requery;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - an Answers view crossing into a term observes exact-one cardinality and
    encodes that answer as the operand [tested:
    test_answer_views_observe_when_used_as_operands; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - Rows and Answers project caller variables by attribute, Variable key, or
    exact string key, and group binding rows by an atom-valued column [tested:
    test_rows_share_the_answer_projection_contract,
    test_binding_rows_group_by_their_column_atom; commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e]
  - Answers.index retains the Sequence row-position contract and directs a
    missing string that names a column to column() [tested:
    test_answers_index_keeps_the_sequence_contract_and_explains_columns;
    commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e]
  - len on an untouched engine-backed Answers view uses its engine count method
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
  - the eager table methods refuse term answers instead of taking an answer
    apart into columns, and both display faces render term answers as a
    bounded list [tested test_term_answers_never_render_as_a_binding_table]
  - zip and reversed retain their lawful Sequence behavior while recording
    advisory ordering evidence for Space.lint [tested:
    test_zip_over_unordered_answers_is_lawful_and_linted,
    test_reversed_over_unordered_answers_is_lawful_and_linted; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - Rows and Answers produce the Arrow C schema and stream capsules from one
    typed projection, so pyarrow, polars, pandas 3 and DuckDB read them with
    no glue, and to_df and to_pl are sugar over the same stream [tested:
    test_pyarrow_reads_the_rows_capsule_directly,
    test_to_pl_and_the_capsule_answer_the_same_frame; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - a column projects to a NumPy array of its decoded values through
    __array__, rather than an object array of atoms [tested:
    test_a_numeric_column_becomes_a_typed_numpy_array; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - __length_hint__ answers only a size already known and never pulls
    [tested: test_length_hint_never_pulls_and_len_counts; commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
  - a row, a table and an answer view each name their columns in __dir__ and
    carry them on a refusal, so the interpreter's suggestion and the
    library's sentence agree about the same mistake [tested:
    test_a_row_offers_its_own_columns,
    test_a_projection_answers_its_columns_from_dir; commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
Owns resources: Answers closes its source; a failed close keeps that source
  available for another attempt [tested:
  test_failed_answer_exit_retains_its_source_for_retry; commit=4a3266c7354990618de5d9489f4e094f5a80c5b6].
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
import operator
import reprlib
import threading
import typing
from collections import UserList
from collections.abc import Callable, Iterable, Iterator, Sequence
from difflib import get_close_matches
from functools import lru_cache
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, NamedTuple, Self, SupportsIndex, cast, overload

import metta.doors as _doors
from metta import seam
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Undefined,
    Variable,
    _decode,
    _encode,
)
from metta._catalog.bounds import config
from metta._errors.errors import EngineError, Ground, MettaResultError, Remedy, refusing
from metta._lazy import lazy
from metta._lazy import optional as require_module

#: `(Error culprit reason)` is a VALUE in MeTTa rather than a throw, which is
#: why every aggregating door keeps it as data and only the single-value
#: accessors raise. The arbiter settles it: at the parity pin
#: `!(return-on-error (Error 5 BadType) 6)` answers `(Error 5 BadType)`
#: [source: tests/conformance/petta/expected/he_error.metta.out against
#: tests/conformance/petta/examples/he_error.metta; commit=3fc5479961fd591b1884af118528c9a64a1afbb7].
_ERROR_IS_A_VALUE = Ground(
    "arbiter",
    "upstream PeTTa at the parity pin: "
    "tests/conformance/petta/expected/he_error.metta.out answers "
    "(Error 5 BadType) as a value rather than a throw",
)

if TYPE_CHECKING:
    import metta.doors._namespaces as _door_types
    from metta._catalog.arrow import ArrowView, Projection

__all__ = ["Answers", "Column", "Row", "Rows"]

_ERROR_HEAD = Symbol("Error")
_MISSING: Final[object] = object()


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
        ground=_ERROR_IS_A_VALUE,
        remedy=Remedy(
            "read the answers as a multiset, where an (Error ...) is a value",
            "refactor",
            "maybe",
            python="m.eval(target)",
        ),
    )


def raise_error_answers(
    answers: Iterable[object], *, space: str | None = None, target: object = None
) -> None:
    """Raise the first `(Error ...)` member of answers, if any.

    The check every single-value accessor runs before decoding: an error
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


def _twin_column(name: str, columns: tuple[str, ...] | list[str]) -> str | None:
    """The column this name differs from only by the host-convention map.

    `V.head_word` is `$head-word` and `V["head_word"]` is `$head_word`. That is
    the ladder working as designed: attribute access takes Python's convention
    to MeTTa's, and the bracket door stays exact so a head outside identifier
    grammar is still reachable. Mixing the two in one pattern therefore builds
    TWO variables, and the miss surfaced here as a bare "no column", a call or
    more away from the pattern that made it.
    """
    for candidate in (name.replace("_", "-"), name.replace("-", "_")):
        if candidate != name and candidate in columns:
            return candidate
    return None


def _missing_column(name: str, columns: tuple[str, ...] | list[str]) -> str:
    """Say a column is absent, naming its map-twin when one is present."""
    twin = _twin_column(name, columns)
    if twin is None:
        return f"no column {name!r}; columns are {list(columns)}"
    return (
        f"no column {name!r}, but {twin!r} is one: attribute access maps _ to -"
        f" and the bracket door is exact, so V.{name.replace('-', '_')} and"
        f" V[{name!r}] are different variables"
    )


def _explain_query(
    query: _QueryContext | None,
    columns: tuple[str, ...],
    called: str,
    *,
    analyze: bool,
    allow_writes: bool,
) -> _spaces_profile.Explanation:
    """Rebuild the match form a query result came from and explain it.

    The patterns and the space are what the call held; the template is its
    caller-variable columns, which is the template the cursor asked the engine
    for. A `where=` guard is NOT part of it: the guard filters answers after
    the match, so it changes which rows survive and not which join runs.
    """
    if query is None:
        msg = (
            f"{called}() needs the match() result that retained its patterns; "
            f"this one was constructed or transformed independently"
        )
        raise TypeError(msg)
    # Resolve after package initialization, the way why() does, so eager query
    # results stay in the core import layer without a static edge to the facade.
    pattern = (
        query.patterns[0]
        if len(query.patterns) == 1
        else Expression((Symbol(","), *query.patterns))
    )
    form = Expression(
        (
            Symbol("match"),
            Symbol(query.space),
            pattern,
            Expression(tuple(Variable(name) for name in columns)),
        )
    )
    return lazy('metta._faces.space').Space(query.space).explain(
        form, analyze=analyze, allow_writes=allow_writes
    )


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
            msg = _missing_column(name, type(self)._columns)
            raise AttributeError(msg, name=name, obj=self) from None

    def __dir__(self) -> list[str]:
        """Name this answer's columns beside a tuple's own attributes."""
        return sorted(set(super().__dir__()) | set(type(self)._columns))

    def __getitem__(self, key):
        # A column NAME works everywhere an index does, and it is the only
        # spelling that reaches a column named like a tuple method: for a
        # query variable $count, row.count is tuple.count, row["count"] is
        # the answer.
        if isinstance(key, str):
            try:
                key = type(self)._columns.index(key)
            except ValueError:
                msg = _missing_column(key, type(self)._columns)
                raise KeyError(
                    msg
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


class Column(list[Any]):
    """One projected query column: the answer atoms, and the array face.

    A list, because that is what a column of answers has always been and
    every caller that indexes, slices, compares or iterates one keeps
    working. What it adds is `__array__`: `np.asarray(rows["age"])` answers
    an int64 array rather than an object array of Grounded atoms, because
    the array face reads the column's DERIVED kind the way the Arrow doors
    and `to_pl` do, rather than handing NumPy the atoms to guess at.
    """

    __slots__ = ("name",)

    def __init__(self, name: str = "", values: Iterable[Any] = ()) -> None:
        """Hold one query column's atoms under the column's own name."""
        super().__init__(values)
        self.name = name

    def __getitem__(self, key):
        """Index or slice this column; a slice is still this column.

        The name and the array face travel with the window, so
        `np.asarray(rows["age"][:100])` stays an int64 array where a plain
        list would have become an object array of atoms.
        """
        if isinstance(key, slice):
            return Column(self.name, list.__getitem__(self, key))
        return list.__getitem__(self, key)

    def __array__(self, dtype: Any = None, copy: bool | None = None) -> Any:  # noqa: FBT001  -- NumPy's array protocol fixes this positional signature
        """This column as a NumPy array of its decoded values.

        The kind is the column's, not the cell's: a column of Numbers is
        int64 or float64, a column of Strings is text, and a column mixing
        kinds is the canonical MeTTa text of each atom, exactly as it
        crosses through the Arrow doors. A column carrying nulls leaves the
        dtype to NumPy, since no fixed-width dtype holds absence.
        """
        from metta._catalog.arrow import resolve  # noqa: PLC0415  -- the one projection

        if copy is False:
            msg = (
                f"column {self.name!r} decodes its atoms into a new array, so "
                f"np.asarray(column, copy=False) cannot be satisfied; ask for "
                f"the default copy"
            )
            raise ValueError(msg)
        library = _array_library("np.asarray(column) builds an array")
        kind, values = resolve(self)
        if dtype is None and not any(value is None for value in values):
            dtype = _ARRAY_DTYPE.get(kind)
        return library.array(values, dtype=dtype)


#: Only the fixed-width kinds name a dtype. Text is left to the library, whose
#: own answer for NumPy is a `<U` array sized to the longest value, and a
#: column carrying nulls is left to it too, because none of these dtypes holds
#: absence.
# closed-set: decides; policy=which Arrow column kinds have a NumPy dtype of the same width, the rest being left to NumPy's own answer; reads=none, the kinds are metta.seam.ARROW_KINDS and this is the dtype each maps to
_ARRAY_DTYPE: Final = {"int64": "int64", "float64": "float64", "bool": "bool"}


def _array_library(what: str) -> Any:
    """The registered default array library, imported, or a refusal.

    Which library that is comes from the `array` point's rows and not from a
    name here, so a second library becomes the default by registering with
    `default=True` ahead of the shipped row.
    """
    for row in seam.array.table().values():
        if row.default:
            guidance = (
                f"{what} and {row.module} is not installed; install "
                f"pymetta[arrays], or read the column as a list"
            )
            return require_module(row.module, guidance)
    raise TypeError(seam.array.refusal(what))


def _raise_exit_errors(
    message: str,
    body: BaseException | None,
    cleanup_failures: Iterable[BaseException],
) -> None:
    """Preserve each exit failure and let successful cleanup propagate the body."""
    failures = list(cleanup_failures)
    if not failures:
        return
    if body is not None:
        failures.insert(0, body)
    if len(failures) == 1:
        raise failures[0]
    raise BaseExceptionGroup(message, failures) from None


class _AnswerItem[T](NamedTuple):
    """One engine answer and the caller bindings produced alongside it."""

    value: T
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


#: The name a result binds itself under when it renders a template. One name
#: for both faces, so a report written over `m.match(...)` renders `m.answers(...)`
#: unchanged; it is the field name of the STRING face, since a template
#: carries its own values.
_RECEIVER = "rows"


def _render_receiver(
    receiver: Any, source: Any, values: dict[str, Any], *, called: str
) -> str:
    """One result's `render`, for both faces: the receiver is a value it supplies."""
    from metta._atoms.templates import render_with  # noqa: PLC0415  -- the door's other half

    if _RECEIVER in values:
        msg = (
            f"{called} binds {{{_RECEIVER}}} to the result it is called on, so "
            f"it cannot take {_RECEIVER}= as well. Name the other one "
            f"differently, or call metta.render(source, {_RECEIVER}=...) with "
            f"the one you mean."
        )
        raise TypeError(msg)
    return render_with(
        source,
        {_RECEIVER: receiver} | values,
        called=called,
        implicit=frozenset({_RECEIVER}),
    )


def _frame_row(field: str, value: str) -> Any:
    """The frame row whose `field` is `value`, or None."""
    for row in seam.frame.table().values():
        if row.fields.get(field) == value:
            return row
    return None




class Rows(UserList[Row], _doors.DoorOwner):
    """Every answer to a query, in the order the engine produced them.

    Sequence operations retain this type and its columns. ``rows.name``,
    ``rows[V.name]``, and ``rows["name"]`` project a column, matching Answers,
    while integer and slice indexing follow a normal list.
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
    def __getitem__(self, i: Variable) -> Column: ...  # type: ignore[overload-overlap]

    @overload
    def __getitem__(self, i: str) -> Column: ...

    @overload
    def __getitem__(self, i: SupportsIndex) -> Row: ...

    @overload
    def __getitem__(self, i: slice[SupportsIndex | None]) -> Rows: ...

    def __getitem__(
        self, i: SupportsIndex | slice[SupportsIndex | None] | Variable | str
    ) -> Row | Rows | Column:
        if isinstance(i, (Variable, str)):
            return self._column(i.name if isinstance(i, Variable) else i)
        if isinstance(i, slice):
            return Rows(self.columns, self.data[i])
        return self.data[i]

    def __getattr__(self, name: str) -> Column:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._column(name)
        except KeyError as exc:
            from metta.doors import Owner, sugar  # noqa: PLC0415  -- declared package sugars

            try:
                return sugar(self, Owner.rows, name)
            except AttributeError:
                pass
            raise AttributeError(str(exc), name=name, obj=self) from None

    def __dir__(self) -> list[str]:
        from metta.doors import Owner, table  # noqa: PLC0415  -- current registered sugars

        names = {row.python for row in table().values() if row.owner is Owner.rows and row.sugar_of}
        return sorted(set(super().__dir__()) | set(self.columns) | names)

    def __setitem__(
        self,
        i: SupportsIndex | slice[SupportsIndex | None],
        item: Iterable[Any] | Iterable[Iterable[Any]],
    ) -> None:
        if isinstance(i, slice):
            self.data[i] = [self._coerce_row(row) for row in item]
        else:
            self.data[i] = self._coerce_row(item)

    @_doors.door(
        kind=_doors.Kind.write,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_mutations_preserve_invariants',),
        state=_doors.State.any,
    )
    def insert(self, i: int, item: Iterable[Any]) -> None:
        """Read Rows.insert."""
        self.data.insert(i, self._coerce_row(item))

    @_doors.door(
        kind=_doors.Kind.write,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_mutations_preserve_invariants',),
        state=_doors.State.any,
    )
    def append(self, item: Iterable[Any]) -> None:
        """Read Rows.append."""
        self.data.append(self._coerce_row(item))

    @_doors.door(
        kind=_doors.Kind.write,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_mutations_preserve_invariants',),
        state=_doors.State.any,
    )
    def extend(self, other: Iterable[Iterable[Any]]) -> None:
        """Read Rows.extend."""
        checked = [self._coerce_row(row) for row in other]
        self.data.extend(checked)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.rows,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_rows_copy_and_pickle_protocols',),
        state=_doors.State.any,
    )
    def copy(self) -> Rows:
        """Read Rows.copy."""
        return Rows(self.columns, self.data, _query=self._query)

    def __copy__(self) -> Rows:
        return self.copy()

    def __reduce__(self):
        values = [tuple(row) for row in self.data]
        return _restore_rows, (self.columns, values, self._query)

    def _addition_rows(self, other: Iterable[Iterable[Any]]) -> Iterable[Iterable[Any]]:
        if isinstance(other, Rows) and other.columns != self.columns:
            msg = f"cannot combine Rows with columns {self.columns!r} and {other.columns!r}"
            raise ValueError(
                msg
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

    def _column(self, name: str) -> Column:
        # Attribute and Variable-key projection share this implementation
        # with the cast route.
        if name not in self.columns:
            # tuple.index would otherwise report this as
            # "tuple.index(x): x not in tuple", naming neither the column
            # asked for nor the ones that exist.
            if _twin_column(str(name), self.columns) is not None:
                msg = _missing_column(str(name), self.columns)
            else:
                close = get_close_matches(str(name), self.columns, n=1, cutoff=0.6)
                suggestion = f"; did you mean {close[0]!r}?" if close else ""
                msg = f"no column {name!r} in {self.columns}{suggestion}"
            raise KeyError(
                msg
            )
        index = self.columns.index(name)
        return Column(name, (row[index] for row in self))

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=_doors.State.any,
    )
    def column(self, name: str) -> Column:
        """Project one exact column name."""
        return self._column(name)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.mapping,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=_doors.State.any,
    )
    def group_by(self, column: str) -> dict[Atom, Rows]:
        """Group rows by the atom in one exact column."""
        keys = self.column(column)
        grouped: dict[Atom, Rows] = {}
        for key, row in zip(keys, self, strict=True):
            grouped.setdefault(
                cast(Atom, key), Rows(self.columns, (), _query=self._query)
            ).append(row)
        return grouped

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_rows_refuse_an_asserted_scalar[first]'),),
        state=_doors.State.any,
    )
    def first(self, *, default: Any = _MISSING) -> Row | Any:
        """Return the first row, or the caller's explicit default."""
        if self:
            return self[0]
        if default is not _MISSING:
            return default
        msg = "first() found no rows; pass default= for absence"
        raise EngineError(msg)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_rows_refuse_an_asserted_scalar[one]'),),
        state=_doors.State.any,
    )
    def one(self, *, default: Any = _MISSING) -> Row | Any:
        """Return the sole row, using an explicit default only for absence.

        Several rows always raise with their count.
        """
        if not self and default is not _MISSING:
            return default
        if len(self) != 1:
            msg = (
                f"one() expected exactly one row, got {len(self)}; "
                "use first(default=None) for row-or-None, or iterate for all"
            )
            raise EngineError(
                msg
            )
        return self[0]

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def raise_for_errors(self) -> Self:
        """Raise when any cell carries an `(Error ...)` atom; answer self
        otherwise, so the call chains.

            m.match(pattern).raise_for_errors()

        Query rows are BINDINGS, not evaluation answers, so a stored
        error record stays data through every Rows method, one() and
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

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.text,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[rows:why]'), _doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[rows:why]')),
        state=_doors.State.any,
    )
    def why(self) -> str:
        """Explain why this eager query returned no rows.

        The explanation reads the space's current state. A nonempty result
        has nothing to explain, and a manually constructed or transformed
        Rows has no query to inspect, so both uses fail loudly.

        One of nine observability methods: metta.derivation answers HOW a
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
        diagnostics = lazy('metta._observe.diagnostics')
        context = self._query
        return diagnostics.explain_empty_query(
            lazy('metta._faces.space').Space(context.space),
            context.patterns,
            context.where,
        )

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def explain(
        self, *, analyze: bool = False, allow_writes: bool = False
    ) -> _spaces_profile.Explanation:
        """What the engine did with the query that produced these rows.

        The same answer `Space.explain` gives, over the match form this result
        came from: the seam entry, pushdown, source, writes, error mode and the
        PLAN, `generic-join` with its variable order and columns or
        `nested-loop` with the conjunct the matcher leads with. Nothing is
        pulled and nothing is re-matched.

        `analyze=True` RE-RUNS the query inside `stats()` and adds
        `(inferences N)`, `(answers N)` and `(cputime S)`; it refuses a query
        whose operations write unless `allow_writes=True`.

        The longhand is `m.explain(form)` on the match form itself, and under
        that `m.run("!(explain <form>)")`.
        """
        return _explain_query(
            self._query,
            self.columns,
            "explain",
            analyze=analyze,
            allow_writes=allow_writes,
        )

    @overload
    def build[BuildT](self, cls: type[BuildT], /) -> list[BuildT]: ...

    @overload
    def build[BuildT](self, column: str, cls: type[BuildT]) -> list[BuildT]: ...

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[rows:build]'),),
        state=_doors.State.any,
    )
    def build(self, column: str | type, cls: type | None = None) -> list:
        """Rebuild constructor atoms through the two-way translator.

        ``build(column, cls)`` projects a named column. ``build(cls)`` is the
        query reconstruction form when exactly one column holds complete
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
        convert = lazy('metta.convert')
        return [convert.build(value, cls) for value in self._column(column)]

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def into(self, cls: type) -> list:
        """Each row as one ``cls``, matched to named constructor inputs.

        Dataclasses, NamedTuples and registered classes use their constructor
        defaults for omitted inputs. TypedDicts preserve omitted optional
        keys. Extra query columns are ignored. ``match(..., into=cls)`` uses
        this conversion too. A single column of complete constructor
        expressions rebuilds through ``build(cls)``.
        """
        return rows_into(self, cls)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def to_dicts(self) -> list[dict[str, Any]]:
        """Return one Python-native column-to-value mapping per row."""
        return [
            {
                name: _plain(value)
                for name, value in zip(self.columns, row, strict=True)
            }
            for row in self
        ]

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.mapping,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[rows:table]'),),
        state=_doors.State.any,
    )
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

    def _projection(self) -> Projection:
        """These rows as named, kinded columns: the one typed projection."""
        from metta._catalog.arrow import Projection  # noqa: PLC0415  -- the one projection

        return Projection.of(self.columns, self.data)

    def __arrow_c_schema__(self):
        """The Arrow struct schema these rows produce, as an "arrow_schema"
        PyCapsule. One field per column, typed from the wire kinds the column
        holds. Only a consumer of the PyCapsule Interface calls this.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        from metta._catalog.arrow import (  # noqa: PLC0415 -- the optional Arrow extra
            schema_capsule,
        )

        return schema_capsule(self._projection())

    def __arrow_c_stream__(self, requested_schema=None):
        """These rows as an "arrow_array_stream" PyCapsule, in record batches.

            pa.table(rows)                      # pyarrow
            pl.scan_arrow_c_stream(rows)        # polars, lazily
            pd.DataFrame.from_arrow(rows)       # pandas 3
            duckdb.sql("select * from rows")    # a replacement scan

        `requested_schema` is honoured when every column can be produced at
        the type asked for, and otherwise ignored, which the interface allows.
        `rows.arrow()` is the same stream for a consumer that dispatches on
        Python type before protocol.
        """
        from metta._catalog.arrow import (  # noqa: PLC0415 -- the optional Arrow extra
            stream_capsule,
        )

        return stream_capsule(self._projection(), requested_schema)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def arrow(self) -> ArrowView:
        """These rows wearing nothing but the Arrow protocol.

        `Rows` is a sequence, and polars' `DataFrame()` constructor tests for
        a sequence before it looks for the capsule, so `pl.DataFrame(rows)`
        reads the atoms row by row instead. `pl.DataFrame(rows.arrow())` is
        the stream. Consumers that ask for the protocol first, pyarrow,
        DuckDB, pandas 3 and `pl.scan_arrow_c_stream`, take `rows` itself.
        """
        from metta._catalog.arrow import ArrowView  # noqa: PLC0415  -- the optional Arrow extra

        return ArrowView(self)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[rows:to]'),),
        state=_doors.State.any,
    )
    def to(self, library: Any):
        """These rows as a frame of `library`: the general frame door.

            rows.to(polars)          # the module itself, never its name
            rows.to("polars")        # the escape, for a library not imported here

        Sugar over `__arrow_c_stream__` where the library reads it, which is
        typed BY the projection rather than inferred from Python objects, and
        over the projected columns where it does not; either way the values
        are the same. The library is the caller's dependency, and its absence
        raises naming the need. Which libraries are reachable is the `frame`
        point's rows: a library registers once and every rows object answers
        it, with no method added here.
        """
        name = library if isinstance(library, str) else getattr(library, "__name__", library)
        row = _frame_row("module", name)
        if row is None:
            raise TypeError(seam.frame.refusal(f"the frame library {name!r}"))
        return self._frame(row)

    def _frame(self, row: Any):
        """One frame row's library, built from these rows.

        The registrant takes the Arrow view when something builds the capsules
        and the typed projection when nothing does, so it never has to ask
        which situation the process is in.
        """
        from metta._catalog.arrow import ArrowView  # noqa: PLC0415  -- the optional Arrow extra

        view = ArrowView(self) if seam.arrow.claim() is not None else None
        return row.build(self, self._projection(), view)



    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def pipe(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """fn(self, *args, **kwargs), pandas' chaining shape, so a
        pipeline reads left to right instead of inside out:

            m.match(pattern).pipe(clean).pipe(score, weight=2)
        """  # noqa: D205, D415  -- the API contract is one continuous invariant, not summary-and-body prose; the first line deliberately introduces the indented example that follows
        return fn(self, *args, **kwargs)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.text,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def render(self, source: Any, /, **values: Any) -> str:
        """These rows through a template, as text: `metta.render` with `rows` bound.

            rows.render("| {rows:table}")
            rows.render(t"{len(rows)} answers")   # 3.14

        The longhand is `metta.render(source, rows=rows)`. The receiver is
        bound under the name `rows` on both result faces, so one template
        renders an eager result and a lazy one alike; a template carries its
        own values, so the binding is what the STRING face resolves `{rows}`
        against. That binding is always there, so this door always reads its
        text as fields, where `metta.render("{x}")` with no values leaves the
        braces alone. Every row is written, where `__rich__` stops at
        `config.display_rows`: a document is not a terminal.
        """
        return _render_receiver(self, source, values, called="Rows.render")

    def __format__(self, spec: str) -> str:
        """These rows under one format spec: `f"{rows:table}"` is `render`.

        An empty spec is `str(self)`, Python's law; a rendering spec is that
        rendering; anything else is Python's presentation grammar over the
        text.
        """
        from metta._atoms.templates import formatted  # noqa: PLC0415  -- the door's other half

        return formatted(self, spec, str(self))

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

    # begin generated extension declarations: Rows
    # Generated by tools/doorgen.py from extension door marks.
    if TYPE_CHECKING:
        to_df = _door_types._rows_to_df
        to_pl = _door_types._rows_to_pl
    # end generated extension declarations: Rows




def _into_fields(cls: type) -> tuple[dict[str, Any], inspect.Signature | None]:
    """Named constructor inputs, or the independently declared TypedDict keys."""
    if typing.is_typeddict(cls):
        return typing.get_type_hints(cls), None
    named_tuple = isinstance(cls, type) and issubclass(cls, tuple) and hasattr(cls, "_fields")
    if not dataclasses.is_dataclass(cls) and not named_tuple:
        _importlib.import_module("metta.convert").ensure_registered(cls)
    signature = inspect.signature(cls, eval_str=True)
    hints = typing.get_type_hints(cls)
    fields = {}
    for parameter in signature.parameters.values():
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        annotation = parameter.annotation
        if annotation is inspect.Parameter.empty:
            annotation = hints.get(parameter.name)
        if isinstance(annotation, dataclasses.InitVar):
            annotation = annotation.type
        fields[parameter.name] = annotation
    return fields, signature


def rows_into(rows: Rows, cls: type) -> list:
    """Each row as one cls instance, matched by field name: sqlite3's
    row_factory reading, over the existing conversion machinery. A field
    annotated with a registered class builds through the two-way
    translator; a primitive annotation decodes and is CHECKED, so a
    symbol landing in an int field is an error at the boundary rather than
    a surprise downstream; an unannotated field decodes plainly.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    constructor_rows: list[Any] | None = _constructor_rows(rows, cls)
    if constructor_rows is not None:
        return constructor_rows
    fields, signature = _into_fields(cls)
    required = (
        cls.__required_keys__ if signature is None else {
            name for name in fields
            if signature.parameters[name].default is inspect.Parameter.empty
        }
    )
    missing = [name for name in fields if name in required and name not in rows.columns]
    if missing:
        msg = (
            f"{cls.__name__} needs column(s) {missing}; the query answered "
            f"{list(rows.columns)}"
        )
        raise TypeError(
            msg
        )
    indices = {name: rows.columns.index(name) for name in fields if name in rows.columns}
    primitives = (str, int, float, bool)
    built = []
    for row in rows:
        kwargs = {}
        for name, index in indices.items():
            annotation = fields[name]
            atom = row[index]
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
                    "metta.convert"
                ).build(atom, annotation)
        if signature is None:
            built.append(cls(**kwargs))
        else:
            # BoundArguments retains positional-only slots when an earlier
            # omitted input has a default. Python owns the final call shape.
            # https://docs.python.org/3.12/library/inspect.html#inspect.BoundArguments
            bound = inspect.BoundArguments(signature, kwargs)
            bound.apply_defaults()
            built.append(cls(*bound.args, **bound.kwargs))
    return built


def _constructor_rows[BuildT](rows: Rows, cls: type[BuildT]) -> list[BuildT] | None:
    """Rebuild a single complete-constructor column, or decline row shaping."""
    if len(rows.columns) != 1 or typing.is_typeddict(cls):
        return None
    try:
        registration = _importlib.import_module(
            "metta.convert"
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


class Answers[T](Sequence[T], _doors.DoorOwner):
    """A replayable view over an answer source whose size is not yet known.

    Pulling is progressive. Each iterator starts at answer zero, reads the
    shared prefix already computed, and advances the single source only when
    it reaches the frontier. The sequence has no mutation methods.
    """

    __slots__ = (
        "_bound_source",
        "_cache",
        "_columns",
        "_count_source",
        "_done",
        "_error",
        "_known_length",
        "_lock",
        "_query",
        "_source",
        "_space",
        "_target",
        "_values_demanded",
    )

    def __init__(
        self,
        source: Iterable[T | _AnswerItem[T]],
        *,
        columns: Iterable[str] = (),
        space: str | None = None,
        target: object = None,
        count: Callable[..., int | None] | None = None,
        query: _QueryContext | None = None,
        bound_source: Callable[
            [int, Iterable[T | _AnswerItem[T]]],
            Iterable[T | _AnswerItem[T]] | None,
        ]
        | None = None,
    ) -> None:
        self._source = iter(source)
        self._bound_source = bound_source
        self._columns = tuple(columns)
        self._count_source = count
        self._known_length: int | None = None
        self._space = space
        self._target = target
        self._query = query
        self._cache: list[_AnswerItem[T]] = []
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
    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.tuple,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        is_property=True,
        state=_doors.State.any,
    )
    def columns(self) -> tuple[str, ...]:
        """Caller-variable names available for projection."""
        return self._columns

    def _pull(self, index: int) -> bool:
        """Ensure cache[index] exists, or report ordinary exhaustion."""
        with self._lock:
            while len(self._cache) <= index and not self._done:
                try:
                    item = next(self._source)
                    self._cache.append(
                        item if isinstance(item, _AnswerItem) else _AnswerItem(item, None)
                    )
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

    def _cached_item(self, position: int) -> _AnswerItem[T] | None:
        """Read an available record or terminal failure without advancing the source."""
        with self._lock:
            if position < len(self._cache):
                return self._cache[position]
            if self._error is not None:
                raise self._error
            return None

    def _at(self, index: int) -> T:
        if index < 0:
            self._materialize()
            index += len(self._cache)
        if index < 0 or not self._pull(index):
            msg = "Answers index out of range"
            raise IndexError(msg)
        return self._cache[index].value

    def _materialize(self) -> tuple[T, ...]:
        position = len(self._cache)
        while self._pull(position):
            position += 1
        return tuple(item.value for item in self._cache)

    def _iterate(self) -> Iterator[T]:
        position = 0
        while self._pull(position):
            yield self._cache[position].value
            position += 1

    def __iter__(self) -> Iterator[T]:
        frame = inspect.currentframe()
        try:
            caller = None if frame is None else frame.f_back
            if self._space is not None and caller is not None:
                from metta._spaces.intents import (  # noqa: PLC0415 -- intent recording runs only when a result is consumed
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
        finally:
            del frame
        self._values_demanded = True
        return self._iterate()

    def __reversed__(self) -> Iterator[T]:
        """Reverse the materialized view and retain the unordered-use lint."""
        frame = inspect.currentframe()
        try:
            caller = None if frame is None else frame.f_back
            if self._space is not None and caller is not None:
                # intent recording runs only when a result is consumed
                from metta._spaces.intents import record_event_for_name  # noqa: PLC0415

                record_event_for_name(
                    self._space,
                    "unordered-answers-reversed",
                    "Answers",
                    caller,
                )
        finally:
            del frame
        return reversed(self._materialize())

    def _items(self) -> Iterator[_AnswerItem[T]]:
        """Replay values together with their private caller-row metadata."""
        self._values_demanded = True
        position = 0
        while self._pull(position):
            yield self._cache[position]
            position += 1

    def __bool__(self) -> bool:
        return self._pull(0)

    def __len__(self) -> int:
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

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.integer,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def index(self, value: T, start: int = 0, stop: int | None = None) -> int:
        """Return a row position, with a remedy for column-name collisions."""
        try:
            if stop is None:
                return super().index(value, start)
            return super().index(value, start, stop)
        except ValueError:
            if isinstance(value, str) and value in self._columns:
                msg = (
                    "`index` is the Sequence method and answers a row position; "
                    f"{value!r} is a column, read it with `.column({value!r})`"
                )
                raise refusing(
                    ValueError(msg),
                    remedy=Remedy(
                        f"read the column with .column({value!r})",
                        "quickfix",
                        "maybe",
                        python=f"answers.column({value!r})",
                    ),
                ) from None
            raise

    @overload
    def __getitem__(self, key: SupportsIndex) -> T: ...

    @overload
    def __getitem__(self, key: slice) -> Answers[T]: ...

    @overload
    def __getitem__(self, key: Variable) -> Answers[Any]: ...

    @overload
    def __getitem__(self, key: str) -> Answers[Any]: ...

    def __getitem__(
        self, key: SupportsIndex | slice | Variable | str
    ) -> T | Answers[T] | Answers[Any]:
        if isinstance(key, (Variable, str)):
            return self._project(key.name if isinstance(key, Variable) else key)
        if isinstance(key, slice):
            return self._slice(slice(*(
                None if bound is None else operator.index(bound)
                for bound in (key.start, key.stop, key.step)
            )))
        try:
            index = operator.index(key)
        except TypeError:
            msg = (
                "Answers indices are integers, slices, Variables, or exact "
                f"column strings, not {type(key).__name__}"
            )
            raise TypeError(msg) from None
        return self._at(index)

    @property
    def _pristine(self) -> bool:
        """Whether nothing has yet been read out of this view.

        A bound may be pushed into the producer only while every one of these
        holds. A cached prefix, a finished cursor, a demand for values, an
        error or a known length all mean answers or a count have already been
        reported, and a narrower producer would answer a different prefix from
        the one already given out.
        """
        return not (
            self._cache
            or self._done
            or self._values_demanded
            or self._error is not None
            or self._known_length is not None
        )

    def _slice(self, window: slice) -> Answers[T]:
        if window.step == 0:
            msg = "slice step cannot be zero"
            raise ValueError(msg)

        base: Answers[T] = self
        stop = window.stop
        nonnegative = not any(
            value is not None and value < 0
            for value in (window.start, stop, window.step)
        )
        if (
            stop is not None
            and stop > 0
            and nonnegative
            and self._bound_source is not None
            and self._pristine
        ):
            replacement = self._bound_source(stop, self._items())
            if replacement is not None:
                base = Answers(
                    replacement,
                    columns=self._columns,
                    space=self._space,
                    target=self._target,
                    query=self._query,
                )

        def selected() -> Iterator[_AnswerItem[T]]:
            if not nonnegative:
                base._materialize()
                for index in range(len(base._cache))[window]:
                    yield base._cache[index]
                return
            indices = itertools.islice(
                itertools.count(),
                window.start or 0,
                window.stop,
                window.step or 1,
            )
            for index in indices:
                if not base._pull(index):
                    return
                yield base._cache[index]

        return Answers(
            selected(), columns=self._columns, space=self._space, target=self._target
        )

    def _project(self, name: str) -> Answers[Any]:
        if name not in self._columns:
            twin = _twin_column(name, self._columns)
            if twin is not None:
                # The map-twin is a specific, diagnosable mistake rather than a
                # near miss, so it names the mechanism instead of guessing.
                msg = (
                    f"no answer variable {name!r}, but {twin!r} is one: attribute"
                    f" access maps _ to - and the bracket door is exact, so"
                    f" V.{name.replace('-', '_')} and V[{name!r}] are different"
                    f" variables"
                )
            else:
                close = get_close_matches(name, self._columns, n=1, cutoff=0.6)
                suggestion = f"; did you mean {close[0]!r}?" if close else ""
                msg = (
                    f"no answer variable {name!r}; variables are "
                    f"{list(self._columns)}{suggestion}"
                )
            raise AttributeError(msg, name=name, obj=self)
        index = self._columns.index(name)

        def values() -> Iterator[Any]:
            position = 0
            while self._pull(position):
                item = self._cache[position]
                row = item.row
                if row is None:
                    msg = (
                        f"answer {item.value!r} carries no variable "
                        f"row for {name!r}"
                    )
                    raise TypeError(msg)
                yield row[index]
                position += 1

        return Answers(values(), space=self._space, target=self._target)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.answers,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=_doors.State.any,
    )
    def column(self, name: str) -> Answers[Any]:
        """Project one exact caller-variable column."""
        return self._project(name)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.mapping,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_binding_rows_group_by_their_column_atom',),
        state=_doors.State.any,
    )
    def group_by(self, column: str) -> dict[Atom, Rows]:
        """Materialize binding rows grouped by one atom-valued column."""
        return self._eager_rows().group_by(column)

    @property
    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.answers,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        is_property=True,
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_answer_rows_refuses_an_answer_without_bindings'),),
        state=_doors.State.any,
    )
    def rows(self) -> Answers[Row]:
        """The caller-binding row paired with each evaluation answer."""

        def values() -> Iterator[Row]:
            position = 0
            while self._pull(position):
                item = self._cache[position]
                row = item.row
                if row is None:
                    msg = f"answer {item.value!r} carries no variable row"
                    raise TypeError(msg)
                yield row
                position += 1

        return Answers(values(), columns=self._columns, space=self._space, target=self._target)

    def __getattr__(self, name: str) -> Answers[Any]:
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._columns:
            from metta.doors import Owner, sugar  # noqa: PLC0415  -- declared package sugars

            try:
                return sugar(self, Owner.answers, name)
            except AttributeError:
                pass
        return self._project(name)

    def __dir__(self) -> list[str]:
        from metta.doors import Owner, table  # noqa: PLC0415  -- current registered sugars

        names = {row.python for row in table().values() if row.owner is Owner.answers and row.sugar_of}
        return sorted(set(super().__dir__()) | set(self._columns) | names)

    def _answers_are_terms(self) -> bool:
        """Whether these answers are evaluation terms, not caller bindings.

        Reads answer zero and nothing further, so the question costs one
        pull. An empty view has nothing to look at and answers False,
        which keeps an empty match on the table face and with it the
        caption pointing at `why()`.
        """
        return self._pull(0) and not isinstance(self._cache[0].value, Row)

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
                f"terms; answer 0 is {self._cache[0].value!r}. Ask .rows for the "
                f"bindings behind each answer, or read the answers themselves "
                f"as a sequence"
            )
            raise TypeError(msg)
        rows = cast(Iterable[Iterable[Any]], self)
        return Rows(self._columns, rows, _query=self._query)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def into(self, cls: type) -> list:
        """Materialize, then convert through Rows.into."""
        return self._eager_rows().into(cls)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def build(self, *args: Any) -> list[Any]:
        """Materialize, then rebuild one column through Rows.build."""
        return self._eager_rows().build(*args)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def to_dicts(self) -> list[dict[str, Any]]:
        """Materialize as plain column-to-value records."""
        return self._eager_rows().to_dicts()

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.mapping,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def table(self) -> dict[str, list[Any]]:
        """Materialize as a column mapping."""
        return self._eager_rows().table()

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def to(self, library: Any):
        """Materialize, then build a frame of `library`: Rows.to."""
        return self._eager_rows().to(library)



    def __arrow_c_schema__(self):
        """Materialize as binding rows and answer their Arrow schema.

        Materializing is the schema's own requirement, not a shortcut: a
        column's Arrow type is derived from the wire kinds it holds, so the
        schema is not known until the answers are. Term answers are refused
        here for the same reason every other table face refuses them.
        """
        return self._eager_rows().__arrow_c_schema__()

    def __arrow_c_stream__(self, requested_schema=None):
        """Materialize as binding rows and answer their Arrow stream."""
        return self._eager_rows().__arrow_c_stream__(requested_schema)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def arrow(self) -> ArrowView:
        """These answers wearing nothing but the Arrow protocol."""
        return self._eager_rows().arrow()

    def __length_hint__(self) -> int | Any:
        """The size already known, without pulling a single answer.

        Python's `operator.length_hint` and `list()` both try `__len__`
        first, and `Answers.__len__` will run an engine count or materialize
        to answer, which is what a caller asking for a length wants. This is
        the other question: what is the size IF it costs nothing. A finished
        cursor knows it, a view whose length was already counted knows it,
        and anything else answers NotImplemented rather than starting work.
        """
        with self._lock:
            if self._done:
                return len(self._cache)
            if self._known_length is not None:
                return self._known_length
        return NotImplemented

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def pipe(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Materialize and pass the eager Rows face to ``fn``."""
        return self._eager_rows().pipe(fn, *args, **kwargs)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def raise_for_errors(self) -> Self:
        """Raise stored error cells after materializing the row view."""
        self._eager_rows().raise_for_errors()
        return self

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.text,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def why(self) -> str:
        """Explain an empty query after materializing it."""
        return self._eager_rows().why()

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def explain(
        self, *, analyze: bool = False, allow_writes: bool = False
    ) -> _spaces_profile.Explanation:
        """What the engine did with the query behind this view, pulling nothing.

        `why()` materializes because an empty answer set is what it explains;
        this one reads the query the view holds, so a lazy stream stays exactly
        where it was and an infinite one is explainable at all. Otherwise it is
        `Rows.explain` and answers the same `Explanation`.
        """
        return _explain_query(
            self._query,
            self._columns,
            "explain",
            analyze=analyze,
            allow_writes=allow_writes,
        )

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
            values.append(self._cache[len(values)].value)
        lines = [str(value) for value in values]
        if self._pull(shown):
            lines.append("… more answers")
        return "\n".join(lines)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.text,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
    def render(self, source: Any, /, **values: Any) -> str:
        """These answers through a template, as text: `Rows.render`'s lazy twin.

        The receiver is bound under the same name, `rows`, so a template
        written for one face renders the other unchanged. Rendering reads the
        answers, so an unbounded view is bounded first, the way `to_dicts`
        and `table` are.
        """
        return _render_receiver(self, source, values, called="Answers.render")

    def __format__(self, spec: str) -> str:
        """These answers under one format spec, exactly as `Rows.__format__`."""
        from metta._atoms.templates import formatted  # noqa: PLC0415  -- the door's other half

        return formatted(self, spec, str(self))

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

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_answers_refuse_an_asserted_scalar[one]'),),
        state=_doors.State.any,
    )
    def one(self, *, default: Any = _MISSING) -> Any:
        """Return at most one decoded value, defaulting only on absence."""
        if not self._pull(0):
            if default is not _MISSING:
                return default
            msg = "one() expected exactly one answer, got 0"
            raise EngineError(msg)
        first = self._cache[0].value
        raise_error_answers((first,), space=self._space, target=self._target)
        if self._pull(1):
            msg = "one() expected exactly one answer, got more than 1"
            raise EngineError(msg)
        return self._scalar(first)

    @_doors.door(
        kind=_doors.Kind.query,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_empty_answers_refuse_an_asserted_scalar[first]'),),
        state=_doors.State.any,
    )
    def first(self, *, default: Any = _MISSING) -> Any:
        """Return the first decoded value, or the caller's explicit default."""
        if not self._pull(0):
            if default is _MISSING:
                msg = "first() found no answers; pass default= for absence"
                raise EngineError(msg)
            return default
        first = self._cache[0].value
        raise_error_answers((first,), space=self._space, target=self._target)
        return self._scalar(first)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Answers):
            return self._materialize() == other._materialize()
        if isinstance(other, Sequence):
            return self._materialize() == tuple(other)
        return NotImplemented

    def __repr__(self) -> str:
        shown: list[Any] = []
        shown_items = config.repr_items
        for index in range(shown_items + 1):
            if not self._pull(index):
                break
            shown.append(self._cache[index].value)
        if len(shown) > shown_items:
            inner = ", ".join(repr(value) for value in shown[:shown_items])
            return f"[{inner}, ...]"
        return repr(shown)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        del memo
        return self

    @_doors.door(
        kind=_doors.Kind.lifecycle,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_result_door_projections_preserve_fields_and_host_conversions',),
        state=_doors.State.any,
    )
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

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            self.close()
        except BaseException as cleanup:  # noqa: BLE001 -- retain cancellation and failed release together
            _raise_exit_errors("answer scope and cleanup failed", exc, (cleanup,))

    def __del__(self) -> None:
        # The backstop under close(). The source owns everything the engine
        # holds for this view, which for a lazy evaluation is a cursor and the
        # engine behind it. A source that was never started owns one too, the
        # cursor a declined count opened, so the closable object the count
        # route hands over closes both; a bare generator's finally would never
        # run [source: extensions/python/metta/_spaces/execution.py:685, _RetainedAnswers.close; tested
        # test_a_counted_view_releases_its_engine_when_it_is_dropped; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
        #
        # close_deferred, where the source has one, because THIS IS A
        # FINALISER: the cyclic collector runs it at a point no caller chose,
        # possibly while this thread is already inside an engine crossing, and
        # it finalises the members of one cycle in no defined order. Closing
        # the cursor synchronously from here aborted the process inside SWI's
        # copy_record on a record another member's finaliser had already
        # erased [source: docs/journal/2026-09-06-finalisers-must-not-call-prolog.md;
        # commit=2421d06e697daffb0797c307a798131616ebdd8e]. Asked for by name rather
        # than by a flag, so a
        # source that has no engine behind it needs no changes and keeps its
        # plain close().
        # [tested: test_a_view_dropped_in_a_cycle_defers_its_cursor_close;
        # commit=2421d06e697daffb0797c307a798131616ebdd8e]
        source = self._source
        close = getattr(source, "close_deferred", None) or getattr(source, "close", None)
        if callable(close):
            close()

    # begin generated extension declarations: Answers
    # Generated by tools/doorgen.py from extension door marks.
    if TYPE_CHECKING:
        to_df = _door_types._answers_to_df
        to_pl = _door_types._answers_to_pl
    # end generated extension declarations: Answers

# Resolve annotations after definitions so peer imports can finish.
import metta._spaces.profile as _spaces_profile  # noqa: E402 -- deferred annotation bindings
