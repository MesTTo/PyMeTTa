"""Purpose: verify CSV interoperability, streamed ownership and file transactions.

Guarantees: Python's independent CSV codec checks generated Unicode dialects
and row shapes; process writers retain every submitted row
[tested: test_generated_csv_agrees_with_python,
test_generated_files_live_views_and_snapshots,
test_csv_concurrent_process_appends; commit=WORKTREE].
Owns resources: temporary directories remove fixtures and writer locks;
snapshots and answer cursors close explicitly. Every subprocess is joined,
and closing its input releases the test's start barrier even on failure.
"""

import csv
import io
import subprocess
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

import janus_swi
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import metta
from metta import G, S, lib
from metta._errors.errors import EngineError

ROOT = Path(__file__).resolve().parents[4]
FIELD = st.one_of(st.sampled_from(("", "001", "\x00", "é🦊λ", "\r\n", "a\"b", "from", "internal")),
                  st.text(st.characters(blacklist_categories=("Cs",)), max_size=30))
ROWS = st.lists(st.lists(FIELD, max_size=5), max_size=7)
DIALECT = st.sampled_from([(separator, quote)
                          for separator in (",", ";", "\t", "🦊", "λ", "\x00")
                          for quote in ('"', "'", "λ", "🦊", "\x00")
                          if separator != quote])


@pytest.fixture(scope="module")
def cv(metta):
    """Exercise the generated native face in the ordinary engine context."""
    metta += lib.csv
    return metta


def options(separator=",", quote='"', newline="\r\n", skip=0):
    """Literal configuration uses the language's existing quote barrier."""
    return S.quote(((S.separator, G(separator)), (S.quote, G(quote)),
                    (S.newline, G(newline)), (S.width, S.any), (S.skip, skip)))


def string_rows(rows):
    """Mark fields as Strings at the Python atom boundary."""
    return tuple(tuple(G(field) for field in row) for row in rows)


def python_csv(rows, separator, quote, newline):
    """Use CPython's public dialect and newline-preserving stream interface."""
    output = io.StringIO(newline="")
    csv.writer(output, delimiter=separator, quotechar=quote, lineterminator=newline).writerows(rows)
    return output.getvalue()


def numbered_rows(space):
    """Native space enumeration is a bag; the explicit number restores file order."""
    return sorted((list(row)[1:] for row in space), key=lambda row: int(row[0]))


# CPython's CSV contract preserves field text and doubles embedded quotes.
# https://github.com/python/cpython/blob/823f0323ee6ec1402088b73bce1a38473cac36dc/Lib/test/test_csv.py
@settings(max_examples=180, deadline=None)
@given(ROWS, DIALECT, st.sampled_from(("\r\n", "\n", "\r")))
def test_generated_csv_agrees_with_python(cv, rows, dialect, newline):
    """Zero-width rows, NUL, arbitrary scalars and dialects cross both codecs."""
    separator, quote = dialect
    config = options(separator, quote, newline)
    expected = python_csv(rows, separator, quote, newline)
    encoded = cv.fn.csv_encode(string_rows(rows), config).one()
    assert encoded == expected
    assert [list(row) for row in cv.fn.csv_parse(G(expected), config).one()] == rows
    assert list(csv.reader(io.StringIO(encoded, newline=""), delimiter=separator,
                           quotechar=quote, strict=True)) == rows


@settings(max_examples=60, deadline=None)
@given(ROWS, DIALECT, st.integers(0, 10))
def test_generated_files_live_views_and_snapshots(cv, rows, dialect, skip):
    """Streams and both space forms preserve bags and physical record numbers."""
    separator, quote = dialect
    config = options(separator, quote, skip=skip)
    with TemporaryDirectory(prefix="metta-csv-property-") as directory:
        path = Path(directory) / "records.csv"
        path.write_bytes(python_csv(rows, separator, quote, "\r\n").encode("utf-8"))
        name = G(str(path))
        assert [list(row) for row in cv.fn["csv-read!"](name, config)] == rows[skip:]
        live = metta.space(cv.fn.csv_space(name, config).one())
        snapshot = metta.space(cv.fn["csv-snapshot!"](name, config).one())
        try:
            expected = [[number, *fields] for number, fields in enumerate(rows, 1) if number > skip]
            assert [list(row)[1:] for row in live] == rows[skip:]
            assert numbered_rows(snapshot) == expected
            assert cv.fn["csv-write!"](name, string_rows(rows), config).one() is True
            assert path.read_bytes().decode("utf-8") == python_csv(rows, separator, quote, "\r\n")
            assert cv.fn["csv-append!"](name, string_rows(rows), config).one() is True
            assert [list(row) for row in cv.fn["csv-read!"](name, config)] == (rows + rows)[skip:]
            assert [list(row)[1:] for row in live] == (rows + rows)[skip:]
            assert numbered_rows(snapshot) == expected
        finally:
            snapshot.drop()


def test_computed_options_and_quoted_literals_keep_option_names_as_data(cv):
    """The parameter can call an option producer without evaluating its result again."""
    cv.run('(= (csv-test-options $sep) (quote ((separator $sep) (quote ""))))')
    actual = cv.fn.csv_parse(G('a"b;c\n'), S["csv-test-options"](G(";"))).one()
    assert [list(row) for row in actual] == [['a"b', "c"]]
    assert [list(row) for row in cv.fn.csv_parse(G('a"b,c\n'), options(quote="")).one()] == [['a"b', "c"]]
    for rows in ([[""]], [["a,b"]], [["a\nb"]]):
        with pytest.raises(EngineError, match="csv_unquoted_field"):
            cv.fn.csv_encode(string_rows(rows), options(quote="")).one()


@pytest.mark.parametrize("payload", [b'\xc0\x80', b'\xc3', b'\xc3(', b'\xed\xa0\x80',
                                     b'\xf4\x90\x80\x80', b'\xff', b'\x80'])
def test_bad_utf8_is_refused_when_consumed_and_cursors_close(cv, tmp_path, payload):
    """A prefetched bad second row cannot invalidate the first bounded answer."""
    path = tmp_path / "bad.csv"
    path.write_bytes(b'first\n"' + payload + b'"\n')
    name = G(str(path))
    with pytest.raises(UnicodeDecodeError):
        payload.decode("utf-8")
    with cv.answers(S["csv-read!"](name)) as first:
        assert list(next(iter(first))) == ["first"]
        assert janus_swi.query_once("stream_property(_,file_name(P))", {"P": str(path)})["truth"]
    assert not janus_swi.query_once("stream_property(_,file_name(P))", {"P": str(path)})["truth"]
    with pytest.raises(EngineError, match="csv_malformed_row"):
        list(cv.fn["csv-read!"](name))
    assert not janus_swi.query_once("stream_property(_,file_name(P))", {"P": str(path)})["truth"]


def test_invalid_output_and_append_refusals_preserve_bytes(cv, tmp_path):
    """Conversion, width and quoting errors leave the old file and no staging."""
    path = tmp_path / "records.csv"
    name = G(str(path))
    original = b'"a",b\r\n'
    path.write_bytes(original)
    for operation, rows in (("csv-write!", ((G("first"),), (42,))),
                            ("csv-append!", ((G("one"),),))):
        with pytest.raises(EngineError):
            cv.fn[operation](name, rows).one()
        assert path.read_bytes() == original
        assert {item.name for item in tmp_path.iterdir()} == {"records.csv", "records.csv.metta-csv.lock"}
    path.write_bytes(b'a,b\n"broken')
    with pytest.raises(EngineError, match="csv_malformed_row"):
        cv.fn["csv-append!"](name, ((G("x"), G("y")),)).one()
    assert path.read_bytes() == b'a,b\n"broken'


def test_csv_concurrent_process_appends(cv, tmp_path):
    """Six independent processes append four transactions each behind one start barrier."""
    path = tmp_path / "shared.csv"
    goal = (
        "current_prolog_flag(argv,[Path,Id]),atom_number(Id,Worker),"
        "writeln(ready),flush_output,read_line_to_string(user_input,_),"
        "forall(between(1,4,N),(format(string(Text),'~d:~d',[Worker,N]),"
        "lib_csv:'csv-append!'(Path,[[Text]],true))),halt"
    )
    command = ["swipl", "--on-error=status", "-q", "-f", "none", "-s", "engine/qlf_boot.pl",
               "-s", "engine/metta.pl", "-s", "lib/lib_csv/lib_csv.pl", "-g", goal, "--"]
    children = []
    with ExitStack() as owned:
        try:
            children.extend(owned.enter_context(subprocess.Popen(
                [*command, str(path), str(worker)], cwd=ROOT,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )) for worker in range(6))
            ready = [child.stdout.readline().strip() for child in children]
        finally:
            for child in children:
                child.stdin.close()
                child.stdin = None
        results = [child.communicate() for child in children]
        assert ready == ["ready"] * 6, results
        for child, (output, error) in zip(children, results, strict=True):
            assert child.returncode == 0 and not output and not error, (output, error)
    actual = [row[0].value for row in cv.fn["csv-read!"](G(str(path)))]
    assert sorted(actual) == sorted(f"{worker}:{number}" for worker in range(6) for number in range(1, 5))
    assert {item.name for item in tmp_path.iterdir()} == {"shared.csv", "shared.csv.metta-csv.lock"}
