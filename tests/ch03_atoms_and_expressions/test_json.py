"""Purpose: pin the network JSON codec, which is the engine's own
reader and writer behind a two-function Python surface.
Guarantees:
  - a refusal arrives as the engine's OWN sentence rather than the reserved
    envelope around it, on both reader paths and for text and bytes alike
    [tested: test_json_codec_refuses_duplicate_keys,
    test_json_codec_refuses_non_finite_numbers,
    test_a_refusal_reads_the_same_through_both_reader_paths; commit=490cd97c382e5cafd0cf7b7ba2fc1aeecbf10b44]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import math
import os
import subprocess
import sys

import pytest

import metta._binding.json as _json

#: What a child process runs to print one refusal's rendered sentence, so the
#: two reader paths can be compared without two engines in one process:
#: engine/json_codec.pl decides between the C reader and library(json) at LOAD
#: time, reading METTA_C_JSON once.
_REFUSAL_PROBE = '\nimport sys\nimport metta._binding.json as _json\nfor source in (sys.argv[1], sys.argv[1].encode("utf-8")):\n    try:\n        _json.loads(source)\n    except ValueError as refused:\n        print(f"{type(refused).__name__}: {refused}")\n    else:\n        print("no refusal")\n'


def _refusal_through(reader, document, repo_root):
    """The refusal `document` draws, read through the named codec path."""
    environment = {
        **os.environ,
        "METTA_C_JSON": "on" if reader == "c" else "off",
        "PYTHONPATH": str(repo_root / "extensions" / "python"),
    }
    done = subprocess.run(
        [sys.executable, "-c", _REFUSAL_PROBE, document],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        env=environment,
    )
    return done.stdout.splitlines()


def test_json_codec_shares_bytes_round_trip():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    payload = {
        "command": "query",
        "unicode": "λ",
        "answers": [{"handle": "a", "score": 0.5}, None, True],
    }
    encoded = _json.dumps(payload)
    assert isinstance(encoded, bytes)
    assert _json.loads(encoded) == payload
    assert _json.loads(encoded.decode("utf-8")) == payload


def test_json_codec_preserves_wide_integers():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    payload = {"low": -(2**80), "high": 2**80}
    assert _json.loads(_json.dumps(payload)) == payload
    assert _json.loads(str(2**80)) == 2**80


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_json_codec_refuses_non_finite_numbers(value):
    """JSON has no spelling for these, and the refusal says which number."""
    with pytest.raises(ValueError) as written:
        _json.dumps({"number": value})
    assert str(written.value).startswith("JSON cannot carry the non-finite number")
    with pytest.raises(ValueError) as read:
        _json.loads(str(value).replace("inf", "Infinity").replace("nan", "NaN"))
    assert str(read.value).startswith("not valid JSON: ")


def test_json_codec_refuses_non_json_objects():
    """A live host object is not JSON data, and the refusal says so."""
    with pytest.raises(TypeError) as refused:
        _json.dumps({"object": object()})
    assert "JSON cannot carry" in str(refused.value)
    assert "which is not a json_term" in str(refused.value)


def test_json_codec_refuses_duplicate_keys():
    """A repeated key is refused, and the refusal NAMES the key.

    Stricter than Python's last-wins reading: a repeated key is a malformed
    object, and silently dropping the first value would let a wire peer smuggle
    one value past a reader that saw the other.

    The sentence is asserted, not just the class. shim.pl's
    metta_py_json_rethrow/1 has composed it since the codec existed, but the
    reserved control envelope carrying it was classified by kind and not by
    detail, so what a caller actually read was `metta: Unknown error term:
    metta_control_signal(value,"JSON object repeats the key a") (value)` --
    right class, no sentence. Nothing failed: every test here asked only for
    ValueError [measured 2026-09-07 on 97c96e91, fixed by 8d673074].
    """
    for document in ('{"a": 1, "a": 2}', b'{"a": 1, "a": 2}'):
        with pytest.raises(ValueError) as refused:
            _json.loads(document)
        assert str(refused.value) == "JSON object repeats the key a"

    # The comparison is on the DECODED key, so an escaped spelling of the same
    # key is the same key, and two sibling objects each naming one are not.
    with pytest.raises(ValueError) as escaped:
        _json.loads('{"a": 1, "\\u0061": 2}')
    assert str(escaped.value) == "JSON object repeats the key a"
    with pytest.raises(ValueError) as nested:
        _json.loads('{"outer": {"b": 1, "b": 2}}')
    assert str(nested.value) == "JSON object repeats the key b"
    assert _json.loads('[{"a": 1}, {"a": 2}]') == [{"a": 1}, {"a": 2}]


def test_a_refusal_reads_the_same_through_both_reader_paths(repo_root):
    """The C reader and library(json) refuse in one voice, text and bytes.

    engine/json_codec.pl picks between them at load time, so each path needs
    its own process. The codec's own differential compares the two
    implementations' TERMS over a corpus that includes this document
    [tested: json_codec_differential:every_document_reads_the_same_through_both_paths];
    what this adds is that the term becomes the same SENTENCE at the Python
    door, which is where the envelope used to swallow it.
    """
    expected = ["ValueError: JSON object repeats the key a"] * 2
    assert _refusal_through("c", '{"a": 1, "a": 2}', repo_root) == expected
    assert _refusal_through("prolog", '{"a": 1, "a": 2}', repo_root) == expected


def test_json_codec_refuses_trailing_content():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError):
        _json.loads('{"a": 1} {"b": 2}')
    assert _json.loads('{"a": 1}  \n ') == {"a": 1}


def test_json_codec_keeps_a_key_named_py():
    """A document is data, and no key of it belongs to the codec.

    The decoder passed `tag(py)` to json_read_dict/3 under a comment about
    crossing janus, but that option names the object KEY whose value becomes
    the dict's tag: a document with a "py" key lost it, silently, in both
    directions of a round trip.
    """
    assert _json.loads('{"py": "x", "a": 1}') == {"py": "x", "a": 1}
    payload = {"py": {"py": ["py"]}, "other": 1}
    assert _json.loads(_json.dumps(payload)) == payload


def test_json_codec_refuses_a_key_that_is_not_a_string():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # JSON has no spelling for a non-string key, and inventing "1" for the
    # integer 1 would make two different objects encode to one document.
    with pytest.raises(TypeError):
        _json.dumps({1: "int key"})


@pytest.mark.parametrize(
    "text",
    [
        '{"a": "\\ud83d\\ude00"}',
        '{"a": "\\u00e9"}',
        '{"a": "</script>"}',
        '{"a": "\\u0000\\u001f"}',
        '{"a": 1.7976931348623157e308}',
        '{"a": 5e-324}',
        '{"a": -0.0}',
        '{"a": 123456789012345678901234567890}',
        '{"a": {"b": [1, {"c": []}]}}',
        "{}",
        "[]",
    ],
)
def test_json_codec_round_trips_the_hazard_corpus(text):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    value = _json.loads(text)
    assert _json.loads(_json.dumps(value)) == value


@pytest.mark.parametrize(
    "text",
    ['{"a": "\\ud800"}', '{"a": "\\udc00"}', '{"a": "\\ud800\\u0041"}'],
)
def test_json_codec_refuses_a_lone_surrogate(text):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises((ValueError, TypeError)):
        _json.loads(text)


def test_json_codec_refuses_a_value_that_contains_itself():
    """A cycle is refused, where it used to take the process down.

    Every other door hands a container over boxed, by reference; this one
    passes it transparently, so janus converts it by recursing and a container
    holding itself takes the C stack with it. Measured 2026-08-29 before the
    guard: SIGSEGV, core dumped, exit 139 -- not an exception, so nothing
    downstream could have caught it.
    """
    payload = {"a": 1}
    payload["self"] = payload
    with pytest.raises(ValueError, match="contains itself"):
        _json.dumps(payload)


def test_json_codec_refuses_a_value_nested_too_deeply():
    """The same crash without a cycle: depth alone overruns the stack."""
    deep: list = []
    cursor = deep
    for _ in range(20_000):
        nested: list = []
        cursor.append(nested)
        cursor = nested
    with pytest.raises(ValueError, match="nested too deeply"):
        _json.dumps(deep)


def test_json_codec_encodes_a_shared_value_reached_twice():
    """Sharing is not a cycle, and a guard that says otherwise is worse.

    A visited-set reading of the same question rejects this ordinary payload;
    only a current-path reading gets it right, which is what bridge.pl's
    metta_py_cycle_check/3 carries as its `Seen` ancestor list.
    """
    shared = [1, 2]
    assert _json.loads(_json.dumps({"a": shared, "b": shared})) == {
        "a": [1, 2],
        "b": [1, 2],
    }


def test_a_refused_value_leaves_the_codec_usable():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    payload = {"a": 1}
    payload["self"] = payload
    with pytest.raises(ValueError):
        _json.dumps(payload)
    assert _json.loads(_json.dumps({"ok": 1})) == {"ok": 1}
