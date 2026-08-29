"""Purpose: a call whose inputs the engine cannot accept fails on ITS OWN
call, by kind, and leaves the engine fit for the next one.

Assumes:
  - an unpaired surrogate is reachable ordinary input, not a contrivance:
    every surrogateescape decode makes them, so os.listdir over a filename
    whose bytes are not UTF-8 hands one straight to a caller
Guarantees:
  - text with no UTF-8 encoding is refused as ValueError, naming where in the
    input it sits, rather than arriving as janus's bare SystemError
    [tested: test_text_with_no_utf8_encoding_is_refused_by_kind,
    test_the_refusal_says_where_in_the_input_the_text_sits]
  - the call AFTER a refused one is unaffected, on every door
    [tested: test_a_refused_crossing_does_not_fail_the_next_call,
    test_no_door_leaves_the_next_call_carrying_the_refusal]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa, _json

# What a surrogateescape decode leaves behind. UTF-8 has no encoding for a
# lone surrogate, so this is the smallest input the seam genuinely cannot
# carry, as opposed to one it merely dislikes.
UNPAIRED_SURROGATE = "\ud800"


@pytest.fixture
def space():  # noqa: D103  -- pytest fixture; the name is the contract
    handle = MeTTa().space()
    yield handle
    handle.drop()


def test_text_with_no_utf8_encoding_is_refused_by_kind(space):
    """The refusal is a ValueError about the caller's data.

    It used to be `SystemError: <built-in function call> returned NULL
    without setting an exception`, which names neither the input nor the
    caller and is not a kind anything catches on purpose.
    """
    with pytest.raises(ValueError, match="unpaired surrogate"):
        space.run(f'!(+ 1 {UNPAIRED_SURROGATE})')


def test_a_refused_crossing_does_not_fail_the_next_call(space):
    """The regression this file exists for.

    A failed input conversion left the Python exception pending inside the
    engine, and the NEXT call raised it as its own: measured 2026-08-29, one
    unrelated call was consumed every time, and the one after that was clean.
    On a server that is one peer's malformed payload failing a different
    peer's request.
    """
    with pytest.raises(ValueError):
        space.run(f'!(+ 1 {UNPAIRED_SURROGATE})')
    assert space.run("!(+ 1 2)") == [[3]]


def test_the_refusal_says_where_in_the_input_the_text_sits():
    """A server rejecting a payload needs the position, not just the fact."""
    with pytest.raises(ValueError, match=r"\['answers'\]\[1\]\['x'\]"):
        _json.dumps({"answers": [{"x": "fine"}, {"x": UNPAIRED_SURROGATE}]})


def test_no_door_leaves_the_next_call_carrying_the_refusal(space):
    """Every door recovers, not just the one that happened to be measured.

    The goal-string door and the predicate door are different janus entry
    points and were both unguarded; a fix to either alone would leave the
    other poisoning its successor.
    """
    for _ in range(3):
        with pytest.raises(ValueError):
            _json.dumps({"a": UNPAIRED_SURROGATE})
        assert _json.dumps({"a": 1}) == b'{"a":1}'
        with pytest.raises(ValueError):
            space.run(f'!(foo "{UNPAIRED_SURROGATE}")')
        assert space.run("!(+ 2 2)") == [[4]]
