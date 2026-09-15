"""Purpose: require one atomic table ingestion contract across representations.

Owns resources: every fixture space and registered frame row is released.
"""

from collections import Counter
from contextlib import contextmanager

import pytest

from metta import MeTTa, S, seam, tables
from metta._catalog import arrow
from metta._catalog.bounds import config
from metta.foreign import SpaceProvider


class _Source:
    def __init__(self, values, *, reader_error=None, close_error=None):
        self.values = iter(values)
        self.reader_error = reader_error
        self.close_error = close_error
        self.pulls = 0
        self.iterations = 0
        self.closed = 0

    def __iter__(self):
        self.iterations += 1
        return self

    def __next__(self):
        self.pulls += 1
        try:
            return next(self.values)
        except StopIteration:
            if self.reader_error is not None:
                raise self.reader_error from None
            raise

    def close(self):
        self.closed += 1
        if self.close_error is not None:
            raise self.close_error


class _Frame:
    def __init__(self, source):
        self.source = source

class _Arrow:
    def __init__(self, source):
        self.source = source

    def __arrow_c_stream__(self):
        msg = "fixture reader owns extraction"
        raise AssertionError(msg)


@pytest.fixture
def tabular(monkeypatch):
    """One reader exposes the same rows through each admitted representation."""
    monkeypatch.setattr(arrow, "read_batches", lambda data: (("value",), data.source))
    seam.frame.register(
        "audit-frame", module=__name__,
        accessor=lambda *_args: None, build=lambda *_args: None,
        rows=lambda data: data.source if isinstance(data, _Frame) else None,
    )

    def make(representation, values, **errors):
        if representation == "columns":
            source = _Source(values, **errors)
            return {"value": source}, source
        rows = [(value,) for value in values]
        if representation == "arrow":
            source = _Source(([row] for row in rows), **errors)
            return _Arrow(source), source
        source = _Source(rows, **errors)
        return (_Frame(source) if representation == "frame" else source), source

    try:
        yield make
    finally:
        seam.frame.unregister("audit-frame")


class _TxStore(SpaceProvider):
    def __init__(self, *, write_error=None):
        self.rows = [S.existing]
        self.saved = None
        self.events = []
        self.write_error = write_error

    def atoms(self):
        return iter(self.rows)

    def add(self, atom):
        if self.write_error is not None and len(self.rows) > config.chunk_cap:
            raise self.write_error
        self.rows.append(atom)

    def begin(self):
        self.events.append("begin")
        self.saved = list(self.rows)

    def commit(self):
        self.events.append("commit")
        self.saved = None

    def rollback(self):
        self.events.append("rollback")
        self.rows = self.saved
        self.saved = None


@contextmanager
def _store(metta, *, foreign, backing=None, atomicity="transactional"):
    if foreign:
        provider = _TxStore() if backing is None else backing
        with MeTTa() as context, context.space(backing=provider) as space:
            if atomicity is not None:
                space.atomicity(atomicity)
            yield space, provider
    else:
        with metta._new_space() as space:
            space.add(S.existing)
            yield space, None


@pytest.mark.parametrize("foreign", [False, True])
@pytest.mark.parametrize("representation", ["iterable", "frame", "arrow", "columns"])
@pytest.mark.parametrize("failure", ["reader", "encoding", "close", "reader_and_close"])
def test_table_ingestion_has_one_declared_failure_boundary(
    metta, monkeypatch, tabular, representation, foreign, failure
):
    """Reading, conversion and release all precede the single commit decision."""
    reader_error = ValueError("late row failure") if "reader" in failure else None
    close_error = RuntimeError("row close failure") if "close" in failure else None
    data, source = tabular(
        representation, range(config.chunk_cap + 1),
        reader_error=reader_error, close_error=close_error,
    )
    if failure == "encoding":
        original = tables._encode

        def encode(value):
            if value == config.chunk_cap:
                msg = "late encoding failure"
                raise ValueError(msg)
            return original(value)

        monkeypatch.setattr(tables, "_encode", encode)
    with _store(metta, foreign=foreign) as (space, provider):
        with pytest.raises(Exception) as raised:
            tables.add(space, "ingested", data)
        assert space.atoms() == [S.existing]
        assert source.closed == 1
        if failure == "reader_and_close":
            assert isinstance(raised.value, ExceptionGroup)
            assert raised.value.exceptions == (reader_error, close_error)
        else:
            assert "failure" in str(raised.value)
        if provider is not None:
            assert provider.events == ["begin", "rollback"]


@pytest.mark.parametrize("representation", ["iterable", "frame", "arrow", "columns"])
def test_table_writer_failure_rolls_back_and_closes_input(metta, tabular, representation):
    """A provider failure after a complete batch rolls back the same transaction."""
    provider = _TxStore(write_error=ValueError("late writer failure"))
    data, source = tabular(representation, range(config.chunk_cap + 1))
    with _store(metta, foreign=True, backing=provider) as (space, _provider):
        with pytest.raises(Exception, match="late writer failure"):
            tables.add(space, "ingested", data)
        assert provider.rows == [S.existing]
        assert provider.events == ["begin", "rollback"]
        assert source.closed == 1


@pytest.mark.parametrize("foreign", [False, True])
@pytest.mark.parametrize("representation", ["iterable", "frame", "arrow", "columns"])
@pytest.mark.parametrize("values", [[], [1, 1, 2]])
def test_table_ingestion_commits_empty_and_duplicate_rows(metta, tabular, representation, foreign, values):
    """Every representation preserves its empty bag or each duplicate occurrence."""
    data, source = tabular(representation, values)
    with _store(metta, foreign=foreign) as (space, provider):
        assert tables.add(space, "ingested", data) == len(values)
        assert Counter(space.atoms()) == Counter([S.existing, *(S.ingested(value) for value in values)])
        assert source.closed == 1
        if provider is not None:
            assert provider.events == ["begin", "commit"]


@pytest.mark.parametrize("atomicity", [None, "best-effort", "atomic-single"])
def test_unsupported_table_store_refuses_before_input_acquisition(metta, atomicity):
    """An unrollbackable provider never receives a row or acquires its iterator."""
    source = _Source([(1,)])
    with _store(metta, foreign=True, atomicity=atomicity) as (space, provider):
        with pytest.raises(Exception, match="transactional"):
            tables.add(space, "ingested", source)
        assert (source.pulls, source.iterations, source.closed) == (0, 0, 0)
        assert provider.rows == [S.existing]
        assert provider.events == []


def test_nested_foreign_table_ingestion_refuses_without_a_provider_savepoint(metta):
    """The declared refusal prevents a caught inner failure retaining a prefix."""
    source = _Source([(1,)])
    with _store(metta, foreign=True) as (space, provider):
        def outer():
            with pytest.raises(Exception, match="nested provider savepoint") as raised:
                tables.add(space, "ingested", source)
            assert raised.value.ground.kind == "metta-law"
            assert "capability" in raised.value.ground.citation
            assert raised.value.capability == "savepoint"
            assert "savepoint" in raised.value.remedy.title
            assert space.name in raised.value.remedy.title

        space.transaction(outer)
        assert (source.pulls, source.iterations, source.closed) == (0, 0, 0)
        assert provider.rows == [S.existing]
        assert provider.events == []


def test_native_nested_table_ingestion_preserves_outer_rollback(metta):
    """Native nested transactions retain their existing rollback semantics."""
    with _store(metta, foreign=False) as (space, _provider):
        def outer():
            assert tables.add(space, "ingested", [(1,), (2,)]) == 2
            msg = "outer rollback"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="outer rollback"):
            space.transaction(outer)
        assert space.atoms() == [S.existing]


def test_table_column_iterators_close_once_per_identity(metta):
    """Two columns may share one iterator; ownership follows the acquired object."""
    source = _Source(range(4))
    with _store(metta, foreign=False) as (space, _provider):
        assert tables.add(space, "pair", {"left": source, "right": source}) == 2
        assert Counter(space.atoms()) == Counter([S.existing, S.pair(0, 1), S.pair(2, 3)])
        assert source.closed == 1


def test_partial_column_acquisition_releases_every_acquired_iterator(metta):
    """A later column that cannot be iterated cannot strand an earlier resource."""
    source = _Source(range(4))

    class BrokenColumn:
        def __iter__(self):
            msg = "column acquisition failure"
            raise ValueError(msg)

    with _store(metta, foreign=False) as (space, _provider):
        with pytest.raises(ValueError, match="column acquisition failure"):
            tables.add(space, "pair", {"left": source, "right": BrokenColumn()})
        assert source.closed == 1
        assert source.pulls == 0
        assert space.atoms() == [S.existing]


def test_table_cleanup_attempts_every_column_and_preserves_each_failure(metta):
    """One close failure cannot suppress another column's release or error."""
    errors = (ValueError("left close failure"), RuntimeError("right close failure"))
    left = _Source([1], close_error=errors[0])
    right = _Source([2], close_error=errors[1])
    with _store(metta, foreign=False) as (space, _provider):
        with pytest.raises(ExceptionGroup) as raised:
            tables.add(space, "pair", {"left": left, "right": right})
        assert raised.value.exceptions == errors[::-1]
        assert (left.closed, right.closed) == (1, 1)
        assert space.atoms() == [S.existing]


@pytest.mark.parametrize("missing", ["rollback", "add"])
def test_table_provider_protocol_is_checked_before_input_acquisition(metta, missing):
    """A declaration cannot substitute for the provider's actual write protocol."""
    provider_type = type("IncompleteStore", (_TxStore,), {missing: None})
    source = _Source([(1,)])
    with _store(metta, foreign=True, backing=provider_type()) as (space, provider):
        with pytest.raises(Exception, match=r"begin/commit/rollback|can add rows"):
            tables.add(space, "ingested", source)
        assert (source.pulls, source.iterations, source.closed) == (0, 0, 0)
        assert provider.rows == [S.existing]
        assert provider.events == []


def test_an_empty_first_record_still_fixes_the_table_columns(metta):
    """A zero-column row cannot conceal a later change of schema."""
    with _store(metta, foreign=False) as (space, _provider):
        with pytest.raises(ValueError, match="same keys"):
            tables.add(space, "row", [{}, {"value": 1}])
        assert space.atoms() == [S.existing]
