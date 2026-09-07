"""Purpose: this seat's own first registrants, one row per library.

Every row is against a point declared in metta.seam, and every third-party
library name the Python seat knows lives HERE, inside the registration that
teaches the seat about it, and nowhere else: the frame libraries, the SQL
engines, the array library, the vector index, the Arrow C-struct builder, the
transport that raises its own timeout, and the model frameworks whose classes
project without being registered.

That is the whole point of the file. A name in a branch of seat logic is a
fork waiting to happen, because the second library of that class cannot reach
the branch; a name in a row is an example of a registration a stranger makes
the same way. `tests/checks/check_hardcoded_integrations.py` is the gate that
keeps it true, and this module is its one allowed site for the Python seat.

Loaded LAZILY, at the first dispatch of a point that names it in `shipped=`,
so the shipped rows arrive by exactly the path a stranger's entry point takes
and a program that never touches a frame pays nothing for pandas being known.
Registration still imports nothing: a row holds the module NAME and the
callables that would use it, and `import metta.tables` stays 15 ms where
`import pandas` is 531 ms [measured 2026-09-06, time.perf_counter around each
import in a fresh interpreter].

Assumes:
  - a library's own classes are reachable through sys.modules once the caller
    has imported it, so recognising a value never imports anything
Guarantees:
  - the shipped rows carry the behaviour their doors had before the seam, the
    existing suites being the differential [tested:
    extensions/python/tests/ch13_a_queryable_dataset/test_arrow_tables.py,
    extensions/python/tests/ch04_spaces_and_matching/test_arrow_doors.py,
    extensions/python/tests/ch08_data/test_arrays.py; commit=WORKTREE]
  - every name here sits inside one registration [tested:
    tests/checks/check_hardcoded_integrations_selftest.py; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import inspect
import sqlite3
import sys
from enum import Enum
from typing import Any, Final

from . import seam
from ._convert_registry import (
    _dataclass_registration,
    _field_types,
    _match_args_registration,
    _named_tuple_registration,
)
from ._optional import optional_module, require_module

# ------------------------------------------------------------ frame libraries

_PANDAS_MISSING: Final = (
    "to_df() builds a pandas DataFrame and pandas is not installed; "
    "rows.table() is the plain dict any frame constructor takes"
)
_POLARS_MISSING: Final = (
    "to_pl() builds a polars DataFrame and polars is not installed; "
    "rows.table() is the plain dict any frame constructor takes"
)


def _install_pandas_accessor(pandas: Any, name: str, door: type) -> None:
    """`df.<name>` on a pandas frame: its registered accessor."""
    pandas.api.extensions.register_dataframe_accessor(name)(door)


def _build_pandas(source: Any, projection: Any, view: Any) -> Any:
    """A pandas DataFrame of these rows.

    `DataFrame.from_arrow` is pandas 3's reader for the PyCapsule stream, so
    the columns are TYPED by the projection rather than inferred from Python
    objects. Without pandas 3, or without a builder for the capsules, the same
    projected columns go through the frame constructor and answer the same
    values.
    """
    pandas = require_module("pandas", _PANDAS_MISSING)
    from_arrow = getattr(pandas.DataFrame, "from_arrow", None)
    if from_arrow is not None and view is not None:
        return from_arrow(source)
    if len(source) and not projection.names:
        return pandas.DataFrame([{} for _ in source])
    return pandas.DataFrame(projection.table())


def _install_polars_accessor(polars: Any, name: str, door: type) -> None:
    """`df.<name>` on a polars frame: its registered namespace."""
    polars.api.register_dataframe_namespace(name)(door)


def _build_polars(source: Any, projection: Any, view: Any) -> Any:
    """A polars DataFrame of these rows, through the Arrow view where there is one.

    polars' constructor tests for a sequence before it looks for the capsule,
    so the view, which is the same data with nothing else on it, is what
    reaches the Arrow path.
    """
    polars = require_module("polars", _POLARS_MISSING)
    if view is not None:
        return polars.DataFrame(view)
    if len(source) and not projection.names:
        return polars.DataFrame([{} for _ in source])
    return polars.DataFrame(projection.table())


seam.frame.register(
    "pandas",
    source="shipped",
    module="pandas",
    accessor=_install_pandas_accessor,
    build=_build_pandas,
    sugar="to_df",
)
seam.frame.register(
    "polars",
    source="shipped",
    module="polars",
    accessor=_install_polars_accessor,
    build=_build_polars,
    sugar="to_pl",
)


# ---------------------------------------------------------------- SQL engines

def _claims_sqlite(connection: Any) -> Any:
    """sqlite3's own connection type, which is in the standard library."""
    return connection if isinstance(connection, sqlite3.Connection) else None


def _define_sqlite(connection: Any, name: str, call: Any, head: Any, signature: Any) -> None:
    """sqlite3 wants the arity and no types, so an undeclared head registers."""
    del head
    connection.create_function(name, seam.sql_arity(signature), call)


def _claims_duckdb(connection: Any) -> Any:
    """A DuckDB connection, recognised without importing DuckDB.

    A connection can only be DuckDB's if DuckDB is imported, so reading
    sys.modules first keeps this free for every program that has no DuckDB.
    """
    duckdb = sys.modules.get("duckdb")
    if duckdb is None:
        return None
    return connection if isinstance(connection, duckdb.DuckDBPyConnection) else None


def _undeclared_duckdb(name: str) -> str:
    """The refusal DuckDB gets for a head with no declared arrow."""
    return (
        f"DuckDB needs the types of {name} and cannot infer them; declare "
        f"the head's arrow, `(: {name} (-> Number Number))`, and register "
        f"again. sqlite3 needs only the arity and takes it undeclared"
    )


def _define_duckdb(connection: Any, name: str, call: Any, head: Any, signature: Any) -> None:
    """DuckDB wants the types, and reads them from the head's DECLARED arrow.

    `inspect.signature` shows the arrow the stored atoms JUSTIFY when nothing
    is declared (`Space.infer_types`'s proposal), which is the right thing to
    show a reader and the wrong thing to build SQL types from: a proposal is
    not a promise.
    """
    parameters, returns = seam.sql_types(head, name, signature, _undeclared_duckdb)
    # SPECIAL, so a head may answer nothing and get SQL NULL: under DuckDB's
    # DEFAULT a returned NULL is an error, and NULL arguments never reach the
    # function at all.
    connection.create_function(name, call, parameters, returns, null_handling="special")


seam.sql.register(
    "sqlite3",
    source="shipped",
    claims=_claims_sqlite,
    define=_define_sqlite,
)
seam.sql.register(
    "duckdb",
    source="shipped",
    claims=_claims_duckdb,
    define=_define_duckdb,
    undeclared=_undeclared_duckdb,
)


# ------------------------------------------------------------ array libraries

_NUMPY_MISSING: Final = (
    "metta.arrays needs NumPy for default arrays and embedding storage; "
    "install pymetta[arrays]"
)


def _numpy_scalars() -> Any:
    """NumPy integer and real scalars, as a Hypothesis strategy.

    These retain identity while MeTTa accepts them as Number operands and
    dispatches through Python operators.
    """
    from .testing import _st  # noqa: PLC0415  -- hypothesis is the test extra

    st = _st()
    numpy = require_module(
        "numpy",
        "metta.testing.numpy_scalars requires numpy; install pymetta[arrays,test]",
    )
    return st.one_of(
        st.integers(-(2**31), 2**31 - 1).map(numpy.int32),
        st.integers(-(2**62), 2**62).map(numpy.int64),
        st.floats(allow_nan=False, allow_infinity=False, width=32).map(numpy.float32),
        st.floats(allow_nan=False, allow_infinity=False, width=64).map(numpy.float64),
    )


seam.array.register(
    "numpy",
    source="shipped",
    module="numpy",
    default=True,
    missing=_NUMPY_MISSING,
    scalars=_numpy_scalars,
)


# --------------------------------------------------------- the index backends
#
# argsort is the seat's own path over the Array API and carries no library
# name; it is registered here rather than in metta.arrays so that the ORDER of
# the two rows is one file's reading order, which is what `backend="auto"`
# consults.

_FAISS_MISSING: Final = "the faiss embedding backend needs faiss-cpu; install pymetta[arrays]"


def _faiss_available() -> bool:
    return optional_module("faiss") is not None


def _faiss_build(matrix: Any) -> Any:
    """An exact inner-product index over the normalized matrix."""
    faiss = require_module("faiss", _FAISS_MISSING)
    numpy = require_module("numpy", _NUMPY_MISSING)
    staged = numpy.ascontiguousarray(numpy.asarray(matrix, dtype=numpy.float32))
    index = faiss.IndexFlatIP(staged.shape[1])
    index.add(staged)
    return index


def _faiss_search(index: Any, query: Any, count: int) -> list[tuple[int, float]]:
    """(row, score) pairs best first, from the built index."""
    numpy = require_module("numpy", _NUMPY_MISSING)
    probe = numpy.ascontiguousarray(numpy.asarray(query, dtype=numpy.float32).reshape(1, -1))
    scores, indexes = index.search(probe, count)
    return [
        (int(index), float(score))
        for score, index in zip(scores[0], indexes[0], strict=True)
    ]


seam.index.register(
    "faiss",
    source="shipped",
    available=_faiss_available,
    build=_faiss_build,
    search=_faiss_search,
    missing=_FAISS_MISSING,
)
def _argsort_available() -> bool:
    """Always: the Array API path is this seat's own and needs no library."""
    return True


def _argsort_build(matrix: Any) -> tuple[Any, Any]:
    """The matrix beside its own namespace; there is nothing else to build."""
    from .arrays import namespace_of  # noqa: PLC0415  -- the array satellite

    return namespace_of(matrix), matrix


def _argsort_search(built: tuple[Any, Any], query: Any, count: int) -> list[tuple[int, float]]:
    """(row, score) pairs best first, over the normalized matrix.

    NumPy-like namespaces use argpartition for the candidate set; namespaces
    exposing only the Array API use argsort.
    """
    from .arrays import _top_indices  # noqa: PLC0415  -- the bounded top-k

    xp, matrix = built
    scores = matrix @ query
    return [(index, float(scores[index])) for index in _top_indices(xp, scores, count)]


seam.index.register(
    "argsort",
    source="shipped",
    available=_argsort_available,
    build=_argsort_build,
    search=_argsort_search,
)


# ------------------------------------------------------ the Arrow C structs

_ARROW_MISSING: Final = (
    "the Arrow doors build the C structs with nanoarrow, which is not "
    "installed; install pymetta[arrow]. A consumer needs no pyarrow, only "
    "its own Arrow support"
)


def _nanoarrow_claims() -> Any:
    """nanoarrow, when it is installed; nothing otherwise.

    nanoarrow builds both C structs from buffers, so a producer needs no
    pyarrow and a consumer needs only whatever Arrow support it already has.
    """
    return optional_module("nanoarrow")


def _nanoarrow_types(na: Any) -> dict[str, Any]:
    from ._arrow import BOOL, FLOAT64, INT64, TEXT, UTF8  # noqa: PLC0415  -- the five column kinds

    return {
        INT64: na.int64(),
        FLOAT64: na.float64(),
        BOOL: na.bool_(),
        UTF8: na.string(),
        TEXT: na.string(),
    }


def _nanoarrow_schema_of(na: Any, projection: Any) -> Any:
    """The struct CSchema for a projection.

    Fields are built one at a time rather than from a name-to-type mapping,
    because a bridge declaration may name one table column twice and Arrow
    allows the duplicate where a dict would silently drop it.
    """
    types = _nanoarrow_types(na)
    fields = [
        na.Schema(types[kind], name=name)
        for name, kind in zip(projection.names, projection.kinds, strict=True)
    ]
    return na.c_schema(na.struct(fields))


def _nanoarrow_schema(projection: Any) -> Any:
    """The "arrow_schema" PyCapsule for a projection."""
    na = require_module("nanoarrow", _ARROW_MISSING)
    return _nanoarrow_schema_of(na, projection).__arrow_c_schema__()


def _nanoarrow_honour(na: Any, projection: Any, requested_schema: Any) -> Any:
    """The projection a requested schema asks for, or the derived one.

    Best-effort by the interface's own rule: a request this producer cannot
    satisfy exactly is ignored rather than refused, and a consumer that cares
    reads the schema it actually got.
    """
    from ._arrow import _REQUESTED_KIND  # noqa: PLC0415  -- the Arrow format strings

    if requested_schema is None:
        return projection
    try:
        wanted = na.c_schema(requested_schema)
        children = list(wanted.children)
    except Exception:  # noqa: BLE001  -- an unreadable request is a request this producer ignores
        return projection
    if wanted.format != "+s" or len(children) != len(projection.names):
        return projection
    if [child.name for child in children] != list(projection.names):
        return projection
    kinds = [_REQUESTED_KIND.get(child.format, "") for child in children]
    return projection.retyped(kinds) or projection


def _nanoarrow_stream(projection: Any, requested_schema: Any = None) -> Any:
    """The "arrow_array_stream" PyCapsule for a projection."""
    from nanoarrow.c_array_stream import CArrayStream  # noqa: PLC0415  -- the Arrow extra

    from ._arrow import batch_bounds  # noqa: PLC0415  -- the shared batch policy

    na = require_module("nanoarrow", _ARROW_MISSING)
    projection = _nanoarrow_honour(na, projection, requested_schema)
    schema = _nanoarrow_schema_of(na, projection)
    types = _nanoarrow_types(na)
    batches = [
        na.c_array_from_buffers(
            schema,
            stop - start,
            [None],
            children=[
                na.c_array(projection.values(index, start, stop), types[kind])
                for index, kind in enumerate(projection.kinds)
            ],
        )
        for start, stop in batch_bounds(projection.length)
    ]
    # Every batch was built from `schema` itself, so type equality holds by
    # construction and the per-batch re-check would only re-derive it.
    return CArrayStream.from_c_arrays(batches, schema, validate=False).__arrow_c_stream__()


def _nanoarrow_batches(source: Any) -> tuple[tuple[str, ...], Any]:
    """The stream's column names, and an iterator of its record batches."""
    na = require_module("nanoarrow", _ARROW_MISSING)
    stream = na.ArrayStream(source)
    schema = stream.schema
    if schema.type != na.Type.STRUCT:
        stream.close()
        msg = (
            f"an Arrow stream of rows is a stream of struct arrays; this one "
            f"carries {schema.type}, which has no columns to become an atom's "
            f"arguments"
        )
        raise TypeError(msg)
    names = tuple(field.name for field in schema.fields)

    def batches():
        with stream:
            for chunk in stream.iter_chunks():
                yield list(chunk.iter_tuples())

    return names, batches()


seam.arrow.register(
    "nanoarrow",
    source="shipped",
    claims=_nanoarrow_claims,
    schema=_nanoarrow_schema,
    stream=_nanoarrow_stream,
    batches=_nanoarrow_batches,
    missing=_ARROW_MISSING,
)


# ---------------------------------------------------- transports that time out

def _websocket_classes(module: Any) -> tuple[type[BaseException], ...]:
    """websocket-client's own timeout and closed-stream exceptions.

    The obvious test does not separate them from an application error: a
    socket timeout raises OSError, but websocket-client's own timeout does NOT
    subclass it, so "is the cause an OSError" misses exactly the shape a
    broken event stream takes under load.
    """
    return (module.WebSocketTimeoutException, module.WebSocketConnectionClosedException)


seam.transport_error.register(
    "websocket",
    source="shipped",
    module="websocket",
    classes=_websocket_classes,
)


# ------------------------------------------- default images for host classes
#
# The order is the order the chain used before the seam and it is
# load-bearing: a pydantic model is also a class with __match_args__, and a
# NamedTuple is also a tuple, so the most specific row has to be asked first.

def _enum_image(cls: type) -> Any:
    """An Enum crosses as a bare symbol, and runs backwards too."""
    if not issubclass(cls, Enum):
        return None
    return seam.image_of("symbol", None, None, cls.__name__)


def _pydantic_image(cls: type) -> Any:
    """A pydantic model is a constructor expression like a dataclass.

    Its fields are read from model_fields and its rebuild goes through the
    class itself, so validation runs exactly where pydantic runs it. Detected
    through sys.modules: if pydantic was never imported, no BaseModel subclass
    can exist, and the library keeps zero dependency on it.
    """
    pydantic = sys.modules.get("pydantic")
    if pydantic is None or not issubclass(cls, pydantic.BaseModel):
        return None
    model_cls: Any = cls
    names = tuple(model_cls.model_fields.keys())

    def pydantic_parts(obj: Any) -> tuple[Any, ...]:
        extras = getattr(obj, "__pydantic_extra__", None)
        if extras:
            extra_names = ", ".join(sorted(map(str, extras)))
            msg = (
                f"cannot project {cls.__name__}: its Pydantic extra fields "
                f"would be lost ({extra_names}). Declare those fields on "
                f"the model or register an explicit conversion."
            )
            raise TypeError(msg)
        return tuple(getattr(obj, name) for name in names)

    return seam.image_of(
        "expression",
        pydantic_parts,
        # model_validate with by_name, not cls(**...): a field declared with
        # an alias validates under the alias in the constructor, while
        # projection read attribute names, and by_name accepts them directly.
        lambda *parts: model_cls.model_validate(
            dict(zip(names, parts, strict=True)), by_name=True
        ),
        cls.__name__,
        fields=names,
        types=_field_types(cls, names),
    )


def _dataclass_image(cls: type) -> Any:
    """A dataclass destructures field-wise, its constructor the reverse."""
    if not dataclasses.is_dataclass(cls) or cls is type(None):
        return None
    return _dataclass_registration(cls)


def _named_tuple_image(cls: type) -> Any:
    """A NamedTuple is a tuple that already names its fields."""
    if not (issubclass(cls, tuple) and hasattr(cls, "_fields")):
        return None
    return _named_tuple_registration(cls)


def _match_args_image(cls: type) -> Any:
    """A plain class that states its own destructuring for Python's match.

    A class that says how it crosses through __metta__ has spoken; a default
    derived beside it would claim the type name for a projection the hook
    never uses.
    """
    match_args = getattr(cls, "__match_args__", None)
    if not (
        isinstance(match_args, tuple)
        and match_args
        and all(isinstance(name, str) for name in match_args)
        and inspect.getattr_static(cls, "__metta__", None) is None
    ):
        return None
    return _match_args_registration(cls, match_args)


for _name, _claims in (
    ("enum", _enum_image),
    ("pydantic", _pydantic_image),
    ("dataclass", _dataclass_image),
    ("namedtuple", _named_tuple_image),
    ("match-args", _match_args_image),
):
    seam.image.register(_name, source="shipped", claims=_claims)

del _name, _claims
