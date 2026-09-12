"""Purpose: verify native database values, journal boundaries and process locks.

Guarantees: generated action sequences agree with a Python ordered multiset;
fresh processes contend for the same store and reopen its committed values.
[tested: test_database_model, test_database_process_lock,
test_database_invalid_journal_bytes; commit=060bea3199e9f504c6d425f60841f229fc96e861].
Owns resources: context managers close every store and temporary directory;
subprocess.run joins each child before returning.
"""

import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import G, S, V, lib
from metta._errors.errors import EngineError


@pytest.fixture(scope="module")
def database(metta):
    """Import the generated face used by the executable chapter."""
    metta += lib.database
    return metta


@contextmanager
def store(database, path, sync=S.close):
    """Keep the native handle alive and close it on every exit."""
    handle = database.fn["database-open!"](G(str(path)), sync)[0]
    try:
        yield handle
    finally:
        database.fn["database-close!"](handle).one()


VALUES = st.recursive(
    st.one_of(st.integers(min_value=-(1 << 100), max_value=1 << 100),
              st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=20).map(G),
              st.sampled_from([S.alpha, S.beta, S[":="], S[":seg"]])),
    lambda children: st.lists(children, max_size=5).map(tuple), max_leaves=20,
)


@settings(max_examples=80)
@given(st.lists(st.tuples(st.booleans(), VALUES), max_size=40),
       st.sampled_from([S.none, S.flush, S.close]))
def test_database_model(database, actions, sync):
    """Every add, one-occurrence removal and reopen agrees with a list model."""
    expected = []
    fn = database.fn
    with tempfile.TemporaryDirectory(prefix="database-model-") as directory:
        with store(database, directory, sync) as handle:
            for removing, value in actions:
                if removing:
                    present = value in expected
                    assert fn["database-remove!"](handle, value).one() == present
                    if present:
                        expected.remove(value)
                else:
                    assert fn["database-add!"](handle, value).one() is True
                    expected.append(value)
                assert fn.database_query(handle, V.value, V.value) == [tuple(expected)]
        with store(database, directory) as reopened:
            assert fn.database_query(reopened, V.value, V.value) == [tuple(expected)]


def test_database_process_lock(database, tmp_path):
    """A child refuses an active owner, then reopens after that owner closes."""
    path = tmp_path / "store"
    code = """
import sys
from metta import G, S, V, MeTTa, lib
from metta._errors.errors import EngineError
with MeTTa() as engine:
    engine += lib.database
    try:
        handle = engine.fn['database-open!'](G(sys.argv[1]), S.close)[0]
    except EngineError as error:
        assert sys.argv[2] == 'locked' and 'database_lock_failed' in str(error), error
        print('locked')
    else:
        try:
            assert sys.argv[2] == 'open'
            assert engine.fn.database_query(handle, V.x, V.x) == [(S.parent,)]
            assert engine.fn['database-add!'](handle, S.child).one() is True
            print('open')
        finally:
            engine.fn['database-close!'](handle).one()
"""
    environment = os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    with store(database, path) as handle:
        assert database.fn["database-add!"](handle, S.parent).one() is True
        locked = subprocess.run([sys.executable, "-c", code, str(path), "locked"],
                                env=environment, capture_output=True, text=True, check=False)
        assert locked.returncode == 0, locked.stdout + locked.stderr
        assert locked.stdout.strip() == "locked"
    opened = subprocess.run([sys.executable, "-c", code, str(path), "open"],
                            env=environment, capture_output=True, text=True, check=False)
    assert opened.returncode == 0, opened.stdout + opened.stderr
    assert opened.stdout.strip() == "open"
    with store(database, path) as reopened:
        assert database.fn.database_query(reopened, V.x, V.x) == [(S.parent, S.child)]


@pytest.mark.parametrize("raw", [b"\xff", b"\xc0\x80", b"\xed\xa0\x80", b"\xf4\x90\x80\x80"])
def test_database_invalid_journal_bytes(database, tmp_path, raw):
    """Invalid Unicode never becomes a different stored String during replay."""
    journal = tmp_path / "journal.pl"
    packed = b'assert(row("' + raw + b'")).\n'
    journal.write_bytes(packed)
    with pytest.raises(EngineError, match="database_journal"):
        with store(database, tmp_path):
            pass
    assert journal.read_bytes() == packed


def test_database_foreign_python_values_refuse_before_writing(database, tmp_path):
    """A Python resource's printed representation is never persisted as data."""
    with store(database, tmp_path) as handle:
        for value in [G(object()), S.row(G(object())), V.unbound]:
            with pytest.raises(EngineError, match="persistent_value"):
                database.fn["database-add!"](handle, value).one()
        assert database.fn.database_query(handle, V.x, V.x) == [()]


def test_database_nul_and_numeric_values_keep_native_identity(database, tmp_path):
    """A reopened NUL String and exact integer retain their native types."""
    values = (S.text(G("a\0b")), S.number(1), S.number(1.0), S.number(1 << 2000))
    with store(database, tmp_path) as handle:
        for value in values:
            database.fn["database-add!"](handle, value).one()
    with store(database, tmp_path) as handle:
        assert database.fn.database_query(handle, S.text(V.x), V.x) == [(G("a\0b"),)]
        assert database.fn.database_query(handle, S.number(1), S.hit) == [(S.hit, S.hit)]
        assert database.fn["database-remove!"](handle, S.number(1)).one() is True
        numbers = database.fn.database_query(handle, S.number(V.x), V.x).one()
        assert type(numbers[0].value) is float
        assert numbers[1].value == 1 << 2000
