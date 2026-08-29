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
