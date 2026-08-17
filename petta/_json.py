"""Purpose: encode and decode strict UTF-8 JSON for network wire paths
through the engine's own reader and writer, library(json).
Guarantees:
  - dumps always returns bytes and loads accepts text or bytes [tested
    test_json_codec_shares_bytes_round_trip]
  - wide integers are exact in both directions, because SWI-Prolog
    integers are unbounded [tested test_json_codec_preserves_wide_integers]
  - non-finite numbers are refused in both directions [tested
    test_json_codec_refuses_non_finite_numbers]
  - an object that repeats a key, and text that continues past one JSON
    value, are refused [tested test_json_codec_refuses_duplicate_keys,
    test_json_codec_refuses_trailing_content]
Decides:
  - the codec is the engine's: one JSON implementation for the whole
    system, with janus carrying True, False and None across as
    @(true), @(false) and @(none), the vocabulary the engine's option
    list declares. No Python-side JSON implementation exists here.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from . import _engine


def dumps(value: Any) -> bytes:
    """Encode one strict JSON value to UTF-8 bytes."""
    runtime = _engine.runtime()
    with _engine.engine_thread():
        row = runtime.must("petta_py_json_encode(Value, Text)", Value=value)
    return row["Text"].encode("utf-8")


def loads(data: bytes | bytearray | memoryview | str) -> Any:
    """Decode one strict JSON value without rounding wide integers."""
    if isinstance(data, (bytes, bytearray, memoryview)):
        data = bytes(data).decode("utf-8")
    runtime = _engine.runtime()
    with _engine.engine_thread():
        row = runtime.must("petta_py_json_decode(Text, Value)", Text=data)
    return row["Value"]
