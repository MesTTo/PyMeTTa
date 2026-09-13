"""Purpose: check String operations against independent Unicode and edit oracles.

Guarantees: generated scalar strings include NUL and supplementary characters;
all native header dependencies and distributed checksums are verified
[tested: test_string_unicode_oracles, test_string_exact_distance_oracle,
test_string_native_manifest_covers_the_include_closure; commit=WORKTREE].
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from metta import G, S, V, lib, library
from metta._errors.errors import MettaError

ROOT = Path(__file__).resolve().parents[4]
SCALAR = st.characters(blacklist_categories=("Cs",))
TEXT = st.text(SCALAR, max_size=60)


@pytest.fixture(scope="module")
def string_space(metta):
    """Keep the engine-owned library available throughout the generated cases."""
    metta += lib.string
    return metta


@settings(max_examples=120, deadline=None)
@example("a\0🦊a\0", "\0", "é")
@example("aaaaa", "aa", "🦊")
@example("", "", "x")
@given(TEXT, st.text(SCALAR, max_size=10), st.text(SCALAR, max_size=20))
def test_string_unicode_oracles(string_space, text, part, replacement):
    """Python's explicit text operations agree with every literal boundary."""
    fn = string_space.fn
    assert fn.string_length(G(text)).one() == len(text)
    assert fn.string_index_of(G(text), G(part)).one() == text.find(part)
    assert fn.string_last_index_of(G(text), G(part)).one() == text.rfind(part)
    assert fn.string_contains(G(text), G(part)).one() is (part in text)
    assert fn.string_starts_with(G(text), G(part)).one() is text.startswith(part)
    assert fn.string_ends_with(G(text), G(part)).one() is text.endswith(part)
    assert fn.string_count(G(text), G(part)).one() == text.count(part)
    overlap = sum(text.startswith(part, index) for index in range(len(text) + 1))
    assert fn.string_count(G(text), G(part), True).one() == overlap  # noqa: FBT003 -- MeTTa calls take positional arguments.
    expected = text.replace(part, replacement) if part else text
    assert fn.string_replace(G(text), G(part), G(replacement)).one() == expected
    if part:
        assert list(fn.string_split_exact(G(part), G(text)).one()) == text.split(part)
    split = re.split(f"[{re.escape(part)}]", text) if part else [text]
    assert list(fn.string_split(G(part), G(text)).one()) == split
    assert fn.string_trim(G(text)).one() == text.strip(" \t\n\r")
    assert list(fn.string_codes(G(text)).one()) == list(map(ord, text))
    assert fn.string_from_codes(tuple(map(ord, text))).one() == text
    assert list(fn.string_chars(G(text)).one()) == list(text)
    assert fn.string_from_chars(tuple(G(char) for char in text)).one() == text
    assert fn.string_template(G("a{Value}b"), S.quote(((S.Value, G(text)),))).one() == f"a{text}b"


@settings(max_examples=80, deadline=None)
@example("  a\0\n  🦊\n", "> ")
@example(" \t\n\t\n", "\0")
@given(st.text(st.sampled_from(["a", "b", " ", "\t", "\n", "\r", "\0", "🦊"]), max_size=100), TEXT)
def test_string_line_oracles(string_space, text, prefix):
    """LF line operations preserve data and match the standard dedent contract."""
    fn = string_space.fn
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    assert list(fn.string_lines(G(text)).one()) == lines
    assert fn.string_unlines(tuple(G(line) for line in lines)).one() == "".join(f"{line}\n" for line in lines)
    indented = "\n".join(prefix + line if line.strip(" \t") else line for line in text.split("\n"))
    assert fn.string_indent(G(prefix), G(text)).one() == indented
    # Python 3.14 treats CR-only lines as blank. The String contract retains
    # CR as data; U+E000 is outside this fixture's alphabet and protects it.
    protected = text.replace("\r", "\ue000")
    expected = textwrap.dedent(protected).replace("\ue000", "\r")
    assert fn.string_dedent(G(text)).one() == expected


def edit_distance(left, right):
    """Compute the unit edit recurrence independently of the bit-vector provider."""
    previous = list(range(len(right) + 1))
    for row, first in enumerate(left, 1):
        current = [row]
        for column, second in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (first != second)))
        previous = current
    return previous[-1]


@settings(max_examples=80, deadline=None)
@example("é", "é")
@example("a\0b", "a")
@example("a" * 129 + "b", "b" + "a" * 129)
@example("🦊ab\0" * 40, "\0ba🦊" * 38)
@given(st.text(st.sampled_from(["a", "b", "c", "\0", "🦊", "é"]), max_size=160),
       st.text(st.sampled_from(["a", "b", "c", "\0", "🦊", "é"]), max_size=160))
def test_string_exact_distance_oracle(string_space, left, right):
    """Short and multiword bit-vector paths equal the full edit recurrence."""
    expected = edit_distance(left, right)
    assert string_space.fn.string_edit_distance(G(left), G(right)).one() == expected
    assert string_space.fn.string_edit_distance(G(right), G(left)).one() == expected
    maximum = max(len(left), len(right))
    score = 1 - expected / maximum if maximum else 1.0
    assert string_space.fn.string_similarity(G(left), G(right)).one() == pytest.approx(score)


@settings(max_examples=100, deadline=None)
@example("🦊\0", 7, "é\0", 3)
@example("x", 6, "ab", -2)
@example("", 3, "", 0)
@given(TEXT, st.integers(-4, 72), st.text(SCALAR, max_size=7), st.integers(-3, 8))
def test_string_padding_oracles(string_space, text, width, pad, times):
    """Codepoint construction agrees with an independent cyclic filler oracle."""
    missing = max(0, width - len(text))
    fill = "".join(pad[index % len(pad)] for index in range(missing)) if pad else ""
    left = missing // 2
    before = "".join(pad[index % len(pad)] for index in range(left)) if pad else ""
    after = "".join(pad[index % len(pad)] for index in range(missing - left)) if pad else ""
    fn = string_space.fn
    assert fn.string_pad_left(G(text), width, G(pad)).one() == fill + text
    assert fn.string_pad_right(G(text), width, G(pad)).one() == text + fill
    assert fn.string_center(G(text), width, G(pad)).one() == before + text + after
    assert fn.string_repeat(G(text), times).one() == text * times


@pytest.mark.parametrize("count", [V.n, 1.0, 1.5])
def test_string_empty_construction_validates_counts(string_space, count):
    """Empty results cannot conceal an invalid integer count or width."""
    for program in (S.string_repeat(G(""), count), S.string_center(G("x"), count, G(""))):
        with pytest.raises(MettaError):
            string_space.eval(program)


@pytest.mark.parametrize("count,kind", [(True, S.Bool), (G("2"), S.String)])
def test_string_wrong_count_types_use_the_engine_error_value(string_space, count, kind):
    """Declared argument types refuse literal nonnumbers before recipe evaluation."""
    for program in (S.string_repeat(G(""), count), S.string_center(G("x"), count, G(""))):
        assert string_space.eval(program) == [S.Error(program, S.BadArgType(2, S.Number, kind))]


@pytest.mark.parametrize("value", [V.x, S.quote(S.code(1)), S.quote(S["+"](1, 2))])
def test_string_empty_construction_validates_literal_text(string_space, value):
    """Quoted code and variables remain nontext even when no output is needed."""
    for program in (S.string_repeat(value, 0), S.string_pad_left(G("x"), 0, value)):
        with pytest.raises(MettaError):
            string_space.eval(program)


def test_string_from_chars_preserves_literal_contents(string_space):
    """Joining cannot execute code inside a quoted item expression."""
    with pytest.raises(MettaError):
        string_space.fn.string_from_chars(S.quote((S["+"](1, 2),))).one()
    assert string_space.fn.string_from_chars((G("ab"), S.c, 42, G(""))).one() == "abc42"


def test_string_empty_construction_accepts_arbitrary_integer_counts(string_space):
    """Empty inputs need no enumeration, regardless of the validated count."""
    assert string_space.fn.string_repeat(G(""), 1 << 100).one() == ""
    assert string_space.fn.string_center(G("x"), 1 << 100, G("")).one() == "x"


def test_string_recipe_equations_are_reconstructible(string_space):
    """The stored repeat body composes as a function and with alternative counts."""
    row = string_space.match(S["="](S.string_repeat(V.value, V.n), V.body)).one()
    recipe = string_space.eval(S["|->"]((row.value, row.n), row.body))[0]
    assert string_space.eval((recipe, G("ab"), 3)) == [G("ababab")]
    assert string_space.fn.string_repeat(G("x"), S.superpose((0, 2))) == [G(""), G("xx")]


@pytest.mark.parametrize("program", [
    S.string_repeat(G("x"), 2), S.string_pad_left(G("x"), 3, G(".")),
    S.string_pad_right(G("x"), 3, G(".")), S.string_center(G("x"), 3, G(".")),
])
def test_string_construction_recording_remains_conservative(string_space, program):
    """Construction validation can print diagnostics and cannot promise replay."""
    recording = string_space.record(program)
    assert recording.replayable is False
    assert recording.reason
    with pytest.raises(MettaError, match="not replayable"):
        recording.replay(string_space)


def test_string_card_keeps_every_public_head():
    """Recipes and native boundaries share the existing complete library card."""
    card = library.card("lib_string")
    assert len(card.heads) == len(card.documented) == 34


def test_string_native_manifest_covers_the_include_closure():
    """The build manifest covers every transitive vendor include and exact bytes."""
    owner = ROOT / "lib/lib_string"
    vendor = owner / "vendor"
    declared = {}
    for line in (vendor / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        checksum, name = line.split("  ", 1)
        path = (vendor / name).resolve()
        assert path.is_relative_to(vendor.resolve())
        assert path not in declared
        assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum, name
        declared[path] = checksum
    pending = [owner / "support/string_native.cpp"]
    visited = set()
    while pending:
        path = pending.pop().resolve()
        if path in visited:
            continue
        visited.add(path)
        for delimiter, name in re.findall(r'#\s*include\s*([<"])([^>"]+)[>"]',
                                           path.read_text(encoding="utf-8")):
            if name.startswith("rapidfuzz/"):
                dependency = vendor / name
            elif delimiter == '"':
                dependency = path.parent / name
            else:
                continue
            dependency = dependency.resolve()
            assert dependency in declared, dependency
            pending.append(dependency)
    headers = {path for path in visited if path.suffix == ".hpp"}
    assert headers == {path for path in declared if path.suffix == ".hpp"}
