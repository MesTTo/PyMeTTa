"""Purpose: pin the network JSON codec, which is the engine's own
reader and writer behind a two-function Python surface.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import math

import pytest

from metta import _json


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
def test_json_codec_refuses_non_finite_numbers(value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError):
        _json.dumps({"number": value})
    with pytest.raises(ValueError):
        _json.loads(str(value).replace("inf", "Infinity").replace("nan", "NaN"))


def test_json_codec_refuses_non_json_objects():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError):
        _json.dumps({"object": object()})


def test_json_codec_refuses_duplicate_keys():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Stricter than Python's last-wins reading: a repeated key is a
    # malformed object, and silently dropping the first value would let
    # a wire peer smuggle one value past a reader that saw the other.
    with pytest.raises(ValueError):
        _json.loads('{"a": 1, "a": 2}')


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
