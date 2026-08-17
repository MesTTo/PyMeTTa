"""Purpose: pin the network JSON codec, which is the engine's own
reader and writer behind a two-function Python surface.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import math

import pytest

from petta import _json


def test_json_codec_shares_bytes_round_trip():
    payload = {
        "command": "query",
        "unicode": "λ",
        "answers": [{"handle": "a", "score": 0.5}, None, True],
    }
    encoded = _json.dumps(payload)
    assert isinstance(encoded, bytes)
    assert _json.loads(encoded) == payload
    assert _json.loads(encoded.decode("utf-8")) == payload


def test_json_codec_preserves_wide_integers():
    payload = {"low": -(2**80), "high": 2**80}
    assert _json.loads(_json.dumps(payload)) == payload
    assert _json.loads(str(2**80)) == 2**80


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_json_codec_refuses_non_finite_numbers(value):
    with pytest.raises(ValueError):
        _json.dumps({"number": value})
    with pytest.raises(ValueError):
        _json.loads(str(value).replace("inf", "Infinity").replace("nan", "NaN"))


def test_json_codec_refuses_non_json_objects():
    with pytest.raises(TypeError):
        _json.dumps({"object": object()})


def test_json_codec_refuses_duplicate_keys():
    # Stricter than Python's last-wins reading: a repeated key is a
    # malformed object, and silently dropping the first value would let
    # a wire peer smuggle one value past a reader that saw the other.
    with pytest.raises(ValueError):
        _json.loads('{"a": 1, "a": 2}')


def test_json_codec_refuses_trailing_content():
    with pytest.raises(ValueError):
        _json.loads('{"a": 1} {"b": 2}')
    assert _json.loads('{"a": 1}  \n ') == {"a": 1}
