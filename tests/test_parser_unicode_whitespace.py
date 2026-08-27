"""Purpose: prove the reader separates atoms on every Unicode whitespace
character, and on nothing that merely looks like one.

MeTTa's grammar ends a word at `c.is_whitespace()`, `(`, `)` or `;` [source:
hyperon-experimental v0.2.10-25-g0559a5e2, lib/src/metta/text.rs,
parse_word], and `char::is_whitespace` is the Unicode `White_Space` property
exactly [source: https://www.unicode.org/Public/UCD/latest/ucd/PropList.txt,
PropList-17.0.0, "Total code points: 25"]. The reader used to end a token at
seven ASCII characters, so `(1<NBSP>2)` read as the single symbol `1<NBSP>2`
and `!(superpose (1<NBSP>2))` answered one atom where it should answer two
[measured 2026-08-19: NBSP, EN QUAD, LINE SEPARATOR, IDEOGRAPHIC SPACE and
FORM FEED each left `1<sep>2` whole]. The failure is silent rather than an
error, and NO-BREAK SPACE is what HTML's `&nbsp;` renders to, so it arrives
by the most ordinary route there is, copy and paste.

The class below is derived from Python's own character database rather than
transcribed, which makes it a second authority: the engine's table is
written out code by code and `tests/prolog/suites/reader/parser.plt` checks it against a
transcription of PropList's ranges, so three readings of one file have to
agree before this suite is green.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from metta import Symbol, parse
from metta import testing as pt

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

# The White_Space property is the three separator categories together with
# the six C0 and C1 controls PropList lists beside them, 0009 to 000D and
# 0085. Deriving it beats transcribing it: a transcription cannot disagree
# with itself, and this one is checked against PropList's own total below.
WHITE_SPACE = frozenset(
    {c for c in range(sys.maxunicode + 1) if unicodedata.category(chr(c))[0] == "Z"}
    | {0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x85}
)

# Characters that look like whitespace and are not, so the fix cannot be a
# blanket widening. The first four are `str.isspace()` in Python, which adds
# the ASCII record separators to the property; U+180E was White_Space until
# Unicode 6.3.0 and is a format character now; the last two have zero width.
NOT_WHITE_SPACE = frozenset({0x1C, 0x1D, 0x1E, 0x1F, 0x180E, 0x200B, 0xFEFF})

REPO_ROOT = Path(__file__).resolve().parents[3]

_names = pt.names()
_runs = st.text(alphabet=sorted(chr(c) for c in WHITE_SPACE), min_size=0, max_size=3)


@given(left=_names, right=_names, run=_runs)
@settings(max_examples=25, deadline=None)
def test_every_unicode_whitespace_separates_atoms(left, right, run):
    """Every character in the class, in every generated run of the class,
    between any two names the tokeniser reads back whole.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for code in sorted(WHITE_SPACE):
        source = f"({left}{chr(code)}{run}{right})"
        assert list(parse(source)) == [Symbol(left), Symbol(right)], f"U+{code:04X}"


def test_the_reader_separates_on_the_property_and_nothing_else():
    """Closed in both directions: the class is the 25 code points PropList
    counts, and a character outside it stays inside the token.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert len(WHITE_SPACE) == 25
    for code in sorted(NOT_WHITE_SPACE):
        assert list(parse(f"(a{chr(code)}b)")) == [Symbol(f"a{chr(code)}b")], f"U+{code:04X}"


@pytest.mark.parametrize(
    "code",
    [0x00A0, 0x2000, 0x2028, 0x3000, 0x000C],
    ids=["nbsp", "en_quad", "line_separator", "ideographic", "form_feed"],
)
def test_the_measured_separators_split_a_superpose(metta, code):
    """The reproduction as it was measured: two answers, not one symbol."""
    assert metta.run(f"!(superpose (1{chr(code)}2))") == [[1, 2]]


def test_every_unicode_whitespace_separates_top_level_forms(metta, tmp_path):
    """The file loader scans between forms with its own grammar, so a file
    proves the class reaches further than `parse` does. It did not:
    `(= (a) 1)<IDEOGRAPHIC SPACE>(= (b) 2)` loaded while the same file with a
    NO-BREAK SPACE raised `expected '(' or '!('`.

    The 50 equations land in a scratch space, which is what `load()` itself
    recommends for a load that should not accumulate. `&self` is process
    global, so every later test file the same xdist worker runs would
    otherwise see them.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with metta._new_space() as scratch:
        for code in sorted(WHITE_SPACE):
            # Each file defines its own pair of names, so one space can hold
            # them all without a query answering 25 times over.
            left, right = f"a{code:04x}", f"b{code:04x}"
            source = tmp_path / f"ws{code:04x}.metta"
            source.write_text(f"(= ({left}) 1){chr(code)}(= ({right}) 2)\n", encoding="utf-8")
            scratch.load(str(source))
            assert scratch.run(f"!({left})") == [[1]], f"U+{code:04X}"
            assert scratch.run(f"!({right})") == [[2]], f"U+{code:04X}"


@pytest.mark.parametrize("locale", ["C", "en_AU.UTF-8"])
def test_the_class_does_not_move_with_the_locale(locale):
    """Which characters separate atoms is a property of the language, not of
    the environment the process starts in. It used to be both: `code_type(C,
    space)` reads the C library's tables and answers 21 codes under a UTF-8
    locale and 6 under LC_ALL=C, so a leading IDEOGRAPHIC SPACE parsed under
    one and raised under the other [measured 2026-08-19, same source, same
    engine, two locales]. The suite runs in-process under one locale, so this
    is the only place the other one is exercised.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    done = subprocess.run(
        ["swipl", "-g", "run_tests(parser_unicode_layout)", "-t", "halt",
         "suites/reader/parser.plt"],
        cwd=REPO_ROOT / "tests" / "prolog",
        env=os.environ | {"LC_ALL": locale},
        capture_output=True,
        text=True,
        timeout=290,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_whitespace_inside_a_string_literal_stays_data():
    """A string literal ends at its closing quote, never at layout, so
    widening what separates atoms must not reach inside one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for code in sorted(WHITE_SPACE):
        text = f"a{chr(code)}b"
        assert list(parse(f'(s "{text}")')) == [Symbol("s"), text], f"U+{code:04X}"
