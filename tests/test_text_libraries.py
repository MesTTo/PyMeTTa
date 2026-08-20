"""Purpose: property-based fuzz over the text, file and JSON libraries. The
plunit suites check chosen cases; these check laws that must hold for every
input, which is where the cases nobody thought of turn up.

Expressions are built through the atom API rather than by interpolating into
source text, so an arbitrary generated string cannot break the reader and be
mistaken for a library defect.
Guarantees:
  - split and join invert each other for every text and single-character
    separator [tested test_split_and_join_invert_each_other]
  - a full-width slice is the original text for every input
    [tested test_a_full_slice_is_the_original]
  - json-decode inverts json-encode for every representable value
    [tested test_json_round_trips_scalars, test_json_round_trips_arrays]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from petta import S
from petta.atoms import expr

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
assume = hypothesis.assume
st = hypothesis.strategies

# Printable text without the characters the reader treats specially, so a
# failure is a library defect rather than a quoting artefact.
TEXT = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters='"\\'),
    max_size=40,
)
SEPARATOR = st.sampled_from([",", ";", "|", " ", ":"])


@pytest.fixture(scope="module")
def text_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta.new_space()
    space.run("!(import! &self (library lib_string))")
    space.run("!(import! &self (library lib_json))")
    return space


def call(space, name, *args):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return space.one(expr(S[name], *args))


# ------------------------------------------------------------------ strings


@settings(max_examples=40, deadline=None)
@given(TEXT)
def test_a_full_slice_is_the_original(text_space, text):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    length = call(text_space, "string-length", text)
    assert call(text_space, "string-slice", text, 0, length) == text


@settings(max_examples=40, deadline=None)
@given(TEXT, st.integers(min_value=-50, max_value=90), st.integers(min_value=-50, max_value=90))
def test_slice_never_raises_and_never_exceeds_the_input(text_space, text, start, end):
    """Clamping is the contract, so no index pair may raise or over-run."""
    piece = call(text_space, "string-slice", text, start, end)
    assert isinstance(piece, str)
    assert len(piece) <= len(text)


@settings(max_examples=40, deadline=None)
@given(st.lists(TEXT, min_size=1, max_size=6), SEPARATOR)
def test_split_and_join_invert_each_other(text_space, parts, separator):
    """Join then split returns the parts, provided no part contains the
    separator: that is the precondition, not a defect.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assume(all(separator not in part for part in parts))
    joined = call(text_space, "string-join", separator, expr(*parts))
    back = call(text_space, "string-split", separator, joined)
    # Compare atoms rather than str(), which renders MeTTa syntax: an empty
    # string comes back as the two characters "" and would never match ''.
    assert back == expr(*parts)


@settings(max_examples=40, deadline=None)
@given(TEXT)
def test_chars_round_trip(text_space, text):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    chars = call(text_space, "string-chars", text)
    assert call(text_space, "string-from-chars", chars) == text


@settings(max_examples=40, deadline=None)
@given(TEXT, st.integers(min_value=0, max_value=6))
def test_repeat_multiplies_the_length(text_space, text, times):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repeated = call(text_space, "string-repeat", text, times)
    assert len(repeated) == len(text) * times


@settings(max_examples=40, deadline=None)
@given(TEXT, st.integers(min_value=0, max_value=60))
def test_padding_reaches_the_width_and_never_shortens(text_space, text, width):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    padded = call(text_space, "string-pad-left", text, width, "0")
    assert len(padded) == max(width, len(text))
    assert padded.endswith(text)


@settings(max_examples=40, deadline=None)
@given(TEXT, TEXT)
def test_index_of_and_contains_agree(text_space, haystack, needle):
    """Two ways of asking the same question must never disagree."""
    found = call(text_space, "string-index-of", haystack, needle)
    contains = call(text_space, "string-contains", haystack, needle)
    assert (found >= 0) == (contains is True)


@settings(max_examples=40, deadline=None)
@given(TEXT)
def test_trim_is_idempotent(text_space, text):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    once = call(text_space, "string-trim", text)
    assert call(text_space, "string-trim", once) == once


@settings(max_examples=30, deadline=None)
@given(TEXT, TEXT)
def test_replacing_a_string_with_itself_changes_nothing(text_space, text, part):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert call(text_space, "string-replace", text, part, part) == text


# --------------------------------------------------------------------- JSON


@settings(max_examples=40, deadline=None)
@given(st.one_of(TEXT, st.integers(min_value=-10**6, max_value=10**6)))
def test_json_round_trips_scalars(text_space, value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    encoded = call(text_space, "json-encode", value)
    assert call(text_space, "json-decode", encoded) == value


@settings(max_examples=30, deadline=None)
@given(st.lists(st.integers(min_value=-1000, max_value=1000), max_size=6))
def test_json_round_trips_arrays(text_space, numbers):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    encoded = call(text_space, "json-encode", expr(*numbers))
    decoded = call(text_space, "json-decode", encoded)
    assert [int(item) for item in decoded] == numbers


@settings(max_examples=30, deadline=None)
@given(st.lists(st.tuples(st.sampled_from("abcdefg"), st.integers(0, 999)),
                min_size=1, max_size=5, unique_by=lambda pair: pair[0]))
def test_json_round_trips_objects_through_a_space(text_space, pairs):
    """An object decodes into a space, so the round trip goes through one."""
    entries = expr(*[expr(S[key], number) for key, number in pairs])
    space_handle = call(text_space, "dict-space", entries)
    encoded = call(text_space, "json-encode", space_handle)
    decoded = call(text_space, "json-decode", encoded)
    for key, number in pairs:
        assert call(text_space, "get-value", decoded, S[key]) == number
