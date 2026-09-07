"""Purpose: one typed projection of answer cells, and the Arrow doors on it.

A `Projection` is a column list with, per column, a KIND decided from the wire
kinds of the atoms in it and the plain Python values that kind implies. Every
typed target reads it: the Arrow schema and record batches, `Rows.to_df`,
`Rows.to_pl`, and `Column.__array__`. `Rows.table()` and `Rows.to_dicts()` stay
on their own per-cell rule, which is untyped by contract, and are not projections.

The Arrow PyCapsule Interface is two methods and two capsule names,
`__arrow_c_schema__() -> "arrow_schema"` and
`__arrow_c_stream__(requested_schema=None) -> "arrow_array_stream"`; a
requested schema is best-effort and a producer may ignore it
[source: https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html].
nanoarrow builds both C structs from buffers, so a producer needs no pyarrow
and a consumer needs only whatever Arrow support it already has.

Assumes:
  - nanoarrow is installed for the capsule doors only; the projection, the
    plain values and `Column.__array__` need nothing beyond the standard
    library and (for the array) numpy [tested:
    test_the_arrow_doors_name_the_extra_when_nanoarrow_is_absent]
  - pyarrow is installed for the IPC doors only, which are the ones that write
    and read the streaming format as BYTES for the wire. nanoarrow builds the C
    structs a PyCapsule carries and does not write that format, which is a
    FlatBuffers envelope [tested:
    test_the_ipc_doors_name_the_extra_when_pyarrow_is_absent; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
Guarantees:
  - a column of one wire kind carries that kind's Arrow type and its decoded
    values; a column mixing kinds, or holding a symbol, a variable, a nested
    expression or a number outside int64, carries utf8 canonical MeTTa text
    [tested: test_a_mixed_column_crosses_as_canonical_metta_text,
    test_an_out_of_range_integer_column_crosses_as_text]
  - `Grounded(None)` is Arrow null in every kind, so absence never becomes the
    text "None" [tested: test_nulls_cross_as_arrow_nulls]
  - batches double from one up to _CHUNK_CAP, the same policy the engine
    cursor pulls with [tested: test_the_stream_batches_double_to_the_chunk_cap]
  - a requested schema is honoured when every column can be produced at the
    requested type and ignored otherwise, never refused
    [tested: test_a_requested_schema_is_honoured_or_ignored]
  - one walk of a column answers both its kind and its values, and answers
    what two walks answered; the interleaved A/B that chose it, 135,580,140
    against 247,830,216 retired instructions over five 10,000-cell columns,
    is in docs/journal/2026-09-06-answers-as-arrow-streams.md
    [tested: test_the_fused_pass_answers_what_two_passes_answered;
    commit=6ef81c4dd8fe5fcdd7aec5eeb7d26b4c5a4ddf9d]
Fails when:
  - a consumer wants a lazy producer: nanoarrow 0.9.0 builds an
    ArrowArrayStream only from a resolved list of arrays
    (`CArrayStream.from_c_arrays`), so every batch is encoded before the
    capsule is handed over. Laziness lives on the consumer's side of the
    stream, not on ours.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any, Final, NamedTuple

from . import seam
from ._config import _CHUNK_CAP
from .atoms import Atom, Grounded, _encode

__all__ = [
    "IPC_MEDIA_TYPE",
    "ArrowView",
    "Projection",
    "batch_bounds",
    "ipc_concat",
    "ipc_schema",
    "ipc_stream",
    "read_batches",
    "read_ipc",
    "resolve",
    "values_of",
]

# The five column kinds. Four are native Arrow types; TEXT is utf8 too, and
# differs from UTF8 only in what a cell renders as: UTF8 carries a String
# atom's decoded value, TEXT carries any atom's canonical MeTTa text, which is
# the representation that stays faithful when one column holds several kinds.
INT64: Final = "int64"
FLOAT64: Final = "float64"
BOOL: Final = "bool"
UTF8: Final = "utf8"
TEXT: Final = "text"
_NULL: Final = "null"

_INT64_MIN: Final = -(2**63)
_INT64_MAX: Final = 2**63 - 1
_NO_VALUE: Final = object()

#: The Arrow C format string each kind produces, for reading a requested
#: schema back the other way [source:
#: https://arrow.apache.org/docs/format/CDataInterface.html#data-type-description-format-strings].
_REQUESTED_KIND: Final = {"l": INT64, "g": FLOAT64, "b": BOOL, "u": TEXT}

def _raw(cell: Any) -> Any:
    """The Python payload behind one answer cell, or _NO_VALUE.

    A Handle leaves its value slot unset on purpose, so this asks with a
    default rather than reading the slot.
    """
    if isinstance(cell, Grounded):
        return getattr(cell, "value", _NO_VALUE)
    if isinstance(cell, Atom):
        return _NO_VALUE
    return cell


def _text(cell: Any) -> str:
    """One cell as the MeTTa source text that denotes it."""
    return str(cell) if isinstance(cell, Atom) else str(_encode(cell))


def _read(cell: Any) -> tuple[str, Any]:
    """One cell's own kind and the value that kind carries.

    The two answers come from one walk of the cell because deriving the
    column's kind and rendering its values asked the same questions twice:
    over ten thousand five-column rows the second walk cost 90M of the
    capsule door's 393M retired instructions [measured 2026-09-07, recorded in
    docs/journal/2026-09-06-answers-as-arrow-streams.md].
    """
    if isinstance(cell, Grounded):
        raw = getattr(cell, "value", _NO_VALUE)
        if raw is _NO_VALUE:
            # A handle has no payload to read, so it is its own text.
            return TEXT, str(cell)
    elif isinstance(cell, Atom):
        return TEXT, str(cell)
    else:
        raw = cell
    if raw is None:
        return _NULL, None
    if isinstance(raw, bool):
        return BOOL, raw
    if isinstance(raw, int):
        # A Python int is unbounded and Arrow's is not. Widening silently to
        # float would round and wrapping would lie, so the cell becomes its
        # own text instead, and with it the whole column.
        if _INT64_MIN <= raw <= _INT64_MAX:
            return INT64, raw
        return TEXT, _text(cell)
    if isinstance(raw, float):
        return FLOAT64, raw
    if isinstance(raw, str):
        return UTF8, raw
    return TEXT, _text(cell)


def _column_kind(seen: set[str]) -> str:
    """The one kind a set of per-cell kinds resolves to.

    Nulls have already been dropped. One kind wins outright; integers and
    floats widen to float64, the one pair with a common Arrow type; anything
    else mixed falls to canonical MeTTa text, where every value is
    representable. An all-null column is text, so it is an ordinary nullable
    string column rather than Arrow's null type, which several consumers
    render as no type at all.
    """
    if not seen:
        return TEXT
    if len(seen) == 1:
        return next(iter(seen))
    if seen <= {INT64, FLOAT64}:
        return FLOAT64
    return TEXT


def resolve(cells: Sequence[Any]) -> tuple[str, list[Any]]:
    """One column's derived kind and the values it carries at that kind.

    One pass, with a fix-up only where the column's kind is not each cell's
    own: integers in a float64 column widen, and every non-text cell in a
    text column is re-read as its MeTTa source. A homogeneous column, which
    is what a query over one relation answers, pays neither.
    """
    kinds: list[str] = []
    values: list[Any] = []
    seen: set[str] = set()
    for cell in cells:
        kind, value = _read(cell)
        kinds.append(kind)
        values.append(value)
        seen.add(kind)
    seen.discard(_NULL)
    column = _column_kind(seen)
    if column == FLOAT64 and INT64 in seen:
        values = [None if value is None else float(value) for value in values]
    elif column == TEXT and seen - {TEXT}:
        values = [
            value if kind in (TEXT, _NULL) else _text(cell)
            for kind, value, cell in zip(kinds, values, cells, strict=True)
        ]
    return column, values


def values_of(cells: Sequence[Any], kind: str) -> list[Any]:
    """The plain Python values one column's cells carry at a GIVEN kind.

    `resolve` is the door for the kind a column derives; this is the door for
    a kind a consumer requested, where a value the kind cannot hold answers
    None rather than changing the schema under the consumer.
    """
    if kind == TEXT:
        return [None if _raw(cell) is None else _text(cell) for cell in cells]
    out: list[Any] = []
    for cell in cells:
        raw = _raw(cell)
        numeric = not isinstance(raw, bool)
        if raw is None or raw is _NO_VALUE:
            out.append(None)
        elif kind == FLOAT64:
            out.append(float(raw) if numeric and isinstance(raw, (int, float)) else None)
        elif kind == INT64:
            out.append(raw if numeric and isinstance(raw, int) else None)
        elif kind == BOOL:
            out.append(raw if not numeric else None)
        elif kind == UTF8:
            out.append(raw if isinstance(raw, str) else None)
        else:
            out.append(None)
    return out


def _producible(kind: str, requested: str) -> bool:
    """Whether a column derived at ``kind`` can be handed over as ``requested``."""
    if requested in (kind, TEXT):
        return True  # every atom has canonical text
    return requested == FLOAT64 and kind == INT64


class Projection(NamedTuple):
    """One answer set as named, kinded columns.

    Column-major because every consumer of it is: an Arrow child array, a
    frame column, a NumPy array. `cells` holds the ORIGINAL atoms beside the
    rendered `columns`, so a retype for a requested schema re-reads them
    rather than converting an already-converted value.
    """

    names: tuple[str, ...]
    kinds: tuple[str, ...]
    cells: tuple[tuple[Any, ...], ...]
    columns: tuple[list[Any], ...]
    length: int

    @classmethod
    def of(cls, names: Sequence[str], rows: Sequence[Sequence[Any]]) -> Projection:
        """Project rows of answer cells, deriving each column's kind."""
        names = tuple(names)
        cells = tuple(tuple(column) for column in zip(*rows, strict=True)) if rows else ()
        if not cells:
            cells = tuple(() for _ in names)
        resolved = [resolve(column) for column in cells]
        return cls(
            names,
            tuple(kind for kind, _values in resolved),
            cells,
            tuple(values for _kind, values in resolved),
            len(rows),
        )

    def values(self, index: int, start: int = 0, stop: int | None = None) -> list[Any]:
        """One column's plain values, over a row window; always a fresh list."""
        return self.columns[index][start:stop]

    def table(self) -> dict[str, list[Any]]:
        """The projection as the column mapping a frame constructor takes."""
        return {name: self.values(index) for index, name in enumerate(self.names)}

    def retyped(self, kinds: Sequence[str]) -> Projection | None:
        """The same cells at other kinds, or None when one cannot be produced."""
        if len(kinds) != len(self.kinds):
            return None
        if any(
            not _producible(kind, wanted)
            for kind, wanted in zip(self.kinds, kinds, strict=True)
        ):
            return None
        return Projection(
            self.names,
            tuple(kinds),
            self.cells,
            tuple(
                values_of(cells, kind)
                for cells, kind in zip(self.cells, kinds, strict=True)
            ),
            self.length,
        )


def batch_bounds(length: int) -> Iterator[tuple[int, int]]:
    """Row windows doubling from one up to _CHUNK_CAP.

    The engine cursor's policy, applied to record batches: a consumer that
    reads one batch and stops pays for one row, and one that reads everything
    pays a bounded number of batch boundaries.
    """
    start, size = 0, 1
    while start < length:
        stop = min(start + size, length)
        yield start, stop
        start = stop
        size = min(size * 2, _CHUNK_CAP)


def _builder() -> Any:
    """The row that builds the Arrow C structs here, or a refusal.

    The `arrow` point is ownership: the first registered builder whose library
    is importable claims, and with none the refusal is every registered
    builder's own missing-library sentence. A CONSUMER of the capsules needs
    no row; this is only who makes them.
    """
    claim = seam.arrow.claim()
    if claim is not None:
        return claim.row
    registered = seam.arrow.rows()
    if not registered:
        raise ImportError(seam.arrow.refusal("the Arrow capsule doors"))
    raise ImportError(" ".join(row.missing for row in registered))


def schema_capsule(projection: Projection) -> Any:
    """The "arrow_schema" PyCapsule for a projection."""
    return _builder().schema(projection)


def stream_capsule(projection: Projection, requested_schema: Any = None) -> Any:
    """The "arrow_array_stream" PyCapsule for a projection.

    A requested schema is honoured when every column can be produced at the
    type asked for and ignored otherwise, which the interface allows; the
    builder reads the request, because reading a foreign schema is its
    library's job.
    """
    return _builder().stream(projection, requested_schema)


def read_batches(source: Any) -> tuple[tuple[str, ...], Iterator[list[tuple[Any, ...]]]]:
    """The stream's column names, and an iterator of its record batches.

    The names arrive before the first batch, which is what lets a caller shape
    its own head and then write one batch at a time. The iterator owns the
    stream and releases it when it finishes or is closed.
    """
    return _builder().batches(source)


#: The IPC streaming format, a FlatBuffers envelope, is WRITTEN by the `ipc`
#: point's claiming row and not by the capsule builder: nanoarrow builds the C
#: structs a PyCapsule carries and does not write the envelope, pyarrow does.
#: Every door below asks the point, so a second encoder is a row and no edit.


#: The IANA-registered media type for the Arrow IPC streaming format, and the
#: one a gateway's Accept header names
#: [source: https://www.iana.org/assignments/media-types/media-types.xhtml#application,
#: `application/vnd.apache.arrow.stream`, registered by the Apache Arrow
#: Project; read 2026-09-07].
IPC_MEDIA_TYPE: Final = "application/vnd.apache.arrow.stream"


def _ipc() -> Any:
    """The row that encodes the IPC stream here, or a refusal.

    The `ipc` point is ownership like `arrow`: the first registered encoder
    whose library is importable claims, and with none the refusal is every
    registered encoder's own missing-library sentence.
    """
    claim = seam.ipc.claim()
    if claim is not None:
        return claim.row
    registered = seam.ipc.rows()
    if not registered:
        raise ImportError(seam.ipc.refusal("the Arrow IPC stream"))
    raise ImportError(" ".join(row.missing for row in registered))


def ipc_schema(names: Sequence[str], kinds: Sequence[str], declared: Sequence[str]) -> Any:
    """The Arrow schema for a set of columns, with what each says about itself.

    `declared` is one MeTTa type name per column, which the encoder writes into
    the field's metadata under `metta.type`; a column whose kind is text
    because nothing declared it also carries `metta.kind=mixed`.
    """
    return _ipc().schema(tuple(names), tuple(kinds), tuple(declared))


def ipc_stream(schema: Any, columns: Sequence[Sequence[Any]]) -> bytes:
    """One complete IPC stream: the schema message, one batch, the end marker.

    Complete rather than a fragment, because a response BODY is what a reader
    is handed and a fragment is not readable on its own; a cursor's chunks are
    therefore one stream each with the same schema. An empty chunk is still a
    stream, so a consumer reads a schema either way.
    """
    return _ipc().stream(schema, columns)


def read_ipc(raw: bytes) -> Any:
    """One IPC stream's record batches, as the encoder's own table."""
    return _ipc().read(raw)


def ipc_concat(tables: Sequence[Any]) -> Any:
    """The drained chunks of one cursor as one table."""
    return _ipc().concat(tables)


class ArrowView:
    """One producer wearing nothing but the Arrow PyCapsule Interface.

    polars' ``DataFrame`` constructor tests ``isinstance(data, Sequence)``
    before it looks for the capsule [source:
    polars/dataframe/frame.py, the `isinstance(data, (list, tuple, Sequence))`
    branch ahead of the Arrow branch], and Rows and Answers are sequences by
    contract, so ``pl.DataFrame(rows)`` reads them row by row and never asks
    for the stream. This is the same data with nothing else on it, so a
    consumer that dispatches on Python type before protocol still finds the
    capsule. It forwards, it does not copy: each call reaches the live source.
    """

    __slots__ = ("_source",)

    def __init__(self, source: Any) -> None:
        self._source = source

    def __arrow_c_schema__(self) -> Any:
        """Forward the source's "arrow_schema" capsule."""
        return self._source.__arrow_c_schema__()

    def __arrow_c_stream__(self, requested_schema: Any = None) -> Any:
        """Forward the source's "arrow_array_stream" capsule."""
        return self._source.__arrow_c_stream__(requested_schema)

    def __repr__(self) -> str:
        """Name the view and the producer it forwards to."""
        return f"ArrowView({self._source!r})"
