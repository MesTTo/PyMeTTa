"""Purpose: compare JSON values and UTF-8 files with Python's independent codec.

Guarantees: generated recursive documents and line records round-trip; duplicate
fields, special keys, cycles and malformed bytes keep their native contracts
[tested: test_recursive_documents_agree_with_python, test_lines_agree_with_python,
test_file_rejects_non_utf8_bytes, test_cycles_raise_and_aliases_round_trip; commit=5e212d77a567d6d6c118529e4a226e5047ec2cfd].
Owns resources: decoded object trees are dropped after each property case;
pytest owns file fixture directories.
"""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import metta
from metta import Expression, G, S, Symbol, V, lib
from metta._errors.errors import EngineError

TEXT = st.text(st.characters(blacklist_categories=("Cs",)), max_size=25)
SCALAR = st.one_of(st.none(), st.booleans(), st.integers(-(2**128), 2**128),
                   st.floats(allow_nan=False, allow_infinity=False), TEXT)
DOCUMENT = st.recursive(SCALAR, lambda values: st.one_of(
    st.lists(values, max_size=5), st.dictionaries(TEXT, values, max_size=5)), max_leaves=30)


@pytest.fixture(scope="module")
def js(metta):
    """Import the actual shipped face into the test's engine context."""
    metta += lib.json
    return metta


def drop_tree(value):
    """Release a decoded JSON tree, whose object nodes have no shared aliases."""
    if isinstance(value, Symbol) and value.name.startswith("&json-"):
        space = metta.space(value)
        children = [row[1] for row in space]
        space.drop()
        for child in children:
            drop_tree(child)
    elif isinstance(value, Expression):
        for child in value:
            drop_tree(child)


@settings(max_examples=100, deadline=None)
@given(DOCUMENT)
def test_recursive_documents_agree_with_python(js, document):
    """Python supplies documents containing arbitrary Unicode and nested containers."""
    text = json.dumps(document, ensure_ascii=False, allow_nan=False)
    value = js.fn.json_decode(G(text)).one()
    try:
        for answer in (js.fn.json_encode(value), js.fn.json_pretty(value),
                       js.fn.json_pretty(value, 1), js.fn.json_pretty(value, 0)):
            assert json.loads(answer.one()) == document
    finally:
        drop_tree(value)


@settings(max_examples=60, deadline=None)
@given(st.lists(DOCUMENT, max_size=6))
def test_lines_agree_with_python(js, records):
    """Every record may be any JSON value, including an empty object or array."""
    source = "".join(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
                     for record in records)
    values = list(js.fn.json_lines_decode(G(source)))
    try:
        text = js.fn.json_lines_encode(tuple(values)).one()
        assert [json.loads(line) for line in text.split("\n")[:-1]] == records
        assert text.endswith("\n") if records else text == ""
    finally:
        for value in values:
            drop_tree(value)


def test_special_keys_and_duplicate_paths_cross_the_wire(js):
    """Source-looking keys are ordinary fields and repeated paths keep their bag."""
    value = js.fn.json_decode(G('{"from":[1],"from":[2],"internal":3}')).one()
    try:
        assert js.fn.json_at(value, (S["from"], 0)) == [1, 2]
        assert js.fn.get_value(value, S.internal) == [3]
        pairs = json.loads(js.fn.json_encode(value).one(), object_pairs_hook=list)
        assert pairs == [("from", [1]), ("from", [2]), ("internal", 3)]
    finally:
        drop_tree(value)


def test_cycles_raise_and_aliases_round_trip(js):
    """The same object may appear twice; a reference back to itself raises."""
    value = js.fn.dict_space(((S.x, 1),)).one()
    space = metta.space(value)
    try:
        assert json.loads(js.fn.json_encode((value, value)).one()) == [{"x": 1}, {"x": 1}]
        space.add(S.self(value))
        with pytest.raises(EngineError, match="cyclic_json_value"):
            js.fn.json_encode(value).one()
    finally:
        space.drop()


def test_file_round_trips_utf8_and_json_lines(js, tmp_path):
    """Python reads the bytes MeTTa writes and MeTTa reads Python's documents."""
    path = tmp_path / "document.json"
    document = {"from": [1, {"x": "é🦊\u2028\n"}], "empty": {}}
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    value = js.fn["json-read!"](G(str(path))).one()
    returned = []
    try:
        assert js.fn["json-write!"](G(str(path)), value) == [True]
        assert json.loads(path.read_text(encoding="utf-8")) == document
        assert js.fn["json-lines-write!"](G(str(path)), (value, 7)) == [True]
        assert [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n")[:-1]] == [document, 7]
        returned = list(js.fn["json-lines-read!"](G(str(path))))
        assert [json.loads(js.fn.json_encode(item).one()) for item in returned] == [document, 7]
    finally:
        drop_tree(value)
        for item in returned:
            drop_tree(item)


@pytest.mark.parametrize("payload", [b'"\xc0\x80"', b'"\xc3"', b'"\xc3("',
                                     b'"\xed\xa0\x80"', b'"\xf4\x90\x80\x80"'])
def test_file_rejects_non_utf8_bytes(js, tmp_path, payload):
    """Malformed byte encodings are errors rather than replacement characters."""
    path = tmp_path / "invalid.json"
    with pytest.raises(UnicodeDecodeError):
        payload.decode("utf-8")
    path.write_bytes(payload)
    with pytest.raises(EngineError, match=r"utf8|unicode_scalar_value"):
        js.fn["json-read!"](G(str(path))).one()
    path.write_bytes(b"1\n" + payload + b"\n")
    with pytest.raises(EngineError, match="JSON Lines record 2"):
        list(js.fn["json-lines-read!"](G(str(path))))


def test_failed_serialization_preserves_file_and_removes_staging(js, tmp_path):
    """A valid first record does not truncate an existing file before a later error."""
    path = tmp_path / "records.jsonl"
    path.write_text("keep", encoding="utf-8")
    with pytest.raises(EngineError, match="not sufficiently instantiated"):
        js.fn["json-lines-write!"](G(str(path)), (1, V.unbound)).one()
    assert path.read_text(encoding="utf-8") == "keep"
    assert list(tmp_path.iterdir()) == [path]
