"""Purpose: encode and decode strict UTF-8 JSON for network wire paths.
Guarantees:
  - dumps always returns bytes and loads accepts text or bytes [tested
    test_json_codecs_share_bytes_round_trip]
  - installing orjson changes speed, not JSON data semantics [tested
    test_json_codecs_share_bytes_round_trip,
    test_json_codecs_preserve_wide_integers]
  - non-finite numbers are refused by both implementations [tested
    test_json_codecs_refuse_non_finite_numbers]
  - the accelerated DAS-shaped round trip uses 45.57% fewer instructions
    than stdlib alone [measured 2026-08-14: minimum of three perf stat
    instructions:u runs over 2,000 round trips]
Decides:
  - orjson accelerates supported payloads when installed; stdlib json is the
    required implementation and the compatibility path for values outside
    orjson's 64-bit integer range [source
    https://github.com/ijl/orjson#int]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import re
from typing import Any

try:
    import orjson as _orjson
except ModuleNotFoundError as error:
    if error.name != "orjson":
        raise
    _orjson = None

_POSSIBLE_WIDE_BYTES = re.compile(rb"(?:-[0-9]{19,}|[0-9]{20,})")
_POSSIBLE_WIDE_TEXT = re.compile(r"(?:-[0-9]{19,}|[0-9]{20,})")


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON number {value}")


def _stdlib_dumps(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _stdlib_loads(data: bytes | bytearray | memoryview | str) -> Any:
    if isinstance(data, memoryview):
        data = data.tobytes()
    return json.loads(data, parse_constant=_reject_constant)


def dumps(value: Any) -> bytes:
    """Encode one strict JSON value to UTF-8 bytes."""
    if _orjson is None:
        return _stdlib_dumps(value)
    options = (
        _orjson.OPT_PASSTHROUGH_DATACLASS
        | _orjson.OPT_PASSTHROUGH_DATETIME
        | _orjson.OPT_PASSTHROUGH_SUBCLASS
    )
    try:
        encoded = _orjson.dumps(value, option=options)
    except TypeError:
        # orjson intentionally caps integers at 64 bits. Python and the
        # existing wire contract do not, so stdlib retains that capability.
        return _stdlib_dumps(value)
    if b"null" in encoded:
        # orjson maps NaN and infinities to null. The stdlib check preserves
        # real nulls but refuses those invalid JSON numbers.
        return _stdlib_dumps(value)
    return encoded


def loads(data: bytes | bytearray | memoryview | str) -> Any:
    """Decode one strict JSON value without rounding wide Python integers."""
    if _orjson is None:
        return _stdlib_loads(data)
    possible_wide = (
        _POSSIBLE_WIDE_TEXT.search(data)
        if isinstance(data, str)
        else _POSSIBLE_WIDE_BYTES.search(bytes(data))
    )
    if possible_wide is not None:
        # orjson converts integers outside its range to float on input. A
        # cheap lexical guard sends the uncommon candidate to exact parsing.
        return _stdlib_loads(data)
    return _orjson.loads(data)
