"""Purpose: pin both implementations of the network JSON codec.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import math

import pytest

from petta import _json


@pytest.fixture(params=["stdlib", "orjson"])
def codec(request, monkeypatch):
    if request.param == "stdlib":
        monkeypatch.setattr(_json, "_orjson", None)
    else:
        monkeypatch.setattr(_json, "_orjson", pytest.importorskip("orjson"))
    return _json


def test_json_codecs_share_bytes_round_trip(codec):
    payload = {
        "command": "query",
        "unicode": "λ",
        "answers": [{"handle": "a", "score": 0.5}, None, True],
    }
    encoded = codec.dumps(payload)
    assert isinstance(encoded, bytes)
    assert codec.loads(encoded) == payload
    assert codec.loads(encoded.decode("utf-8")) == payload


def test_json_codecs_preserve_wide_integers(codec):
    payload = {"low": -(2**80), "high": 2**80}
    assert codec.loads(codec.dumps(payload)) == payload
    assert codec.loads(str(2**80)) == 2**80


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_json_codecs_refuse_non_finite_numbers(codec, value):
    with pytest.raises(ValueError):
        codec.dumps({"number": value})
    with pytest.raises(ValueError):
        codec.loads(str(value).replace("inf", "Infinity").replace("nan", "NaN"))


def test_json_codecs_refuse_non_json_objects(codec):
    with pytest.raises(TypeError):
        codec.dumps({"object": object()})
