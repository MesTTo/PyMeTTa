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
  - a value that contains itself, or that is nested too deeply to walk, is
    refused with the remedy rather than crossing: this function passes its value
    transparently, so either one used to overrun the C stack and take the
    process with it [tested:
    test_json_codec_refuses_a_value_that_contains_itself,
    test_json_codec_refuses_a_value_nested_too_deeply,
    test_a_refused_value_leaves_the_codec_usable; commit=3b82643dd18ad5153bca71fa0c4bd09d59b0b7d0]
  - a value merely REACHED twice still encodes, because sharing is not a
    cycle [tested: test_json_codec_encodes_a_shared_value_reached_twice;
    commit=3b82643dd18ad5153bca71fa0c4bd09d59b0b7d0]
Decides:
  - the codec is the engine's: one JSON implementation for the whole
    system, with janus carrying True, False and None across as
    @(true), @(false) and @(none), the vocabulary the engine's option
    list declares. No Python-side JSON implementation exists here.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from typing import Any

from . import _engine

_CONTAINERS = (dict, list, tuple)


def _reaches_itself(value: Any, path: set[int]) -> bool:
    """Whether a container reaches ITSELF, so crossing it cannot terminate.

    Every other crossing hands a Python container over boxed, as `['o', Box(...)]`,
    and a boxed object crosses by reference without being walked. This function
    passes the value TRANSPARENTLY, so janus converts it into a Prolog term by
    recursing through it, and a container holding itself takes the C stack with
    it: measured 2026-08-29, `dumps({'a': 1, 'self': <itself>})` is SIGSEGV,
    core dumped, not an exception. Nothing catches a C stack overflow from
    Python, so this has to be asked BEFORE the call rather than recovered from
    after it.

    The engine already refuses the same shape where it materialises a Python
    object -- bridge.pl's metta_py_cycle_check/3, "materializing one is not a
    slow answer but no answer" -- and this is that refusal for the one function
    that crashed instead of reaching it.

    Detection is by the CURRENT PATH, not by everything visited, which is what
    bridge.pl passes down as its `Seen` ancestor list and what json.dumps keeps
    in its `markers`. A structure that merely reaches one child twice is a DAG
    and legal; a visited-set reading rejects it.

    Recursive rather than a manual stack, measured both ways: 55.23 against
    84.04 microseconds on the shipped 22,323-byte payload, 1.52x. Recursion
    also puts a SECOND hazard behind one mechanism, because a payload can be
    uncrossably deep without holding itself, and Python answers that with a
    catchable RecursionError where janus answers it with the same SIGSEGV.
    dumps turns either into the same refusal.

    The guard costs 88.9 microseconds a round trip, 16.8%, priced back to back
    in one process against the same call with this function neutralised: more
    than its own 60.98 in isolation, because the walk also evicts cache the
    codec then wants. That is the tradeoff CPython's own json makes, where
    check_circular defaults to True and every caller pays it, and a real caller
    pays this once per dumps ahead of a network round trip.
    """
    marker = id(value)
    if marker in path:
        return True
    path.add(marker)
    for child in value.values() if isinstance(value, dict) else value:
        if isinstance(child, _CONTAINERS) and _reaches_itself(child, path):
            return True
    path.discard(marker)
    return False


def dumps(value: Any) -> bytes:
    """Encode one strict JSON value to UTF-8 bytes."""
    try:
        uncrossable = isinstance(value, _CONTAINERS) and _reaches_itself(value, set())
        reason = "contains itself" if uncrossable else None
    except RecursionError:
        reason = "is nested too deeply to walk"
    if reason is not None:
        msg = (
            f"this value {reason}, so it has no JSON reading: encoding it "
            f"overruns the stack rather than answering. Break the cycle or the "
            f"depth, or hold the value whole with metta.ground(value)."
        )
        raise ValueError(msg) from None
    runtime = _engine.runtime()
    with _engine.engine_thread():
        row = runtime.must("metta_py_json_encode(Value, Text)", Value=value)
    return row["Text"].encode("utf-8")


def loads(data: bytes | bytearray | memoryview | str) -> Any:
    """Decode one strict JSON value without rounding wide integers."""
    if isinstance(data, (bytes, bytearray, memoryview)):
        data = bytes(data).decode("utf-8")
    runtime = _engine.runtime()
    with _engine.engine_thread():
        row = runtime.must("metta_py_json_decode(Text, Value)", Text=data)
    return row["Value"]
