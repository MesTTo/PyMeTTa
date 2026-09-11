r"""Purpose: lib_regex from Python: the engine's PCRE2 surface answers
through eval, composes as a query guard, and carries typed named
captures. A MeTTa string reads a doubled backslash as one, so a raw
Python string spelling "\\d" reaches PCRE as the digit class.
Guarantees: compiled patterns survive the wire and agree with text patterns;
Unicode scans agree with Python re over their common syntax
[tested: test_compiled_regex_values_cross_the_wire,
test_match_progression_agrees_with_python_re; commit=WORKTREE].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Expression, G, S, V, convert


@pytest.fixture(scope="module")
def rx(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(import! &self (library lib_regex))")
    return metta


def test_regex_matching_finding_and_replacing(rx):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert rx.eval('(re-match "(?i)^needle" "Needle in a haystack")') == [True]
    assert rx.eval('(re-match "^x" "abc")') == [False]
    assert rx.eval(r'(re-find "\\d+" "a1 b22 c333")') == ["1", "22", "333"]
    (parts,) = rx.eval(r'(re-split ":\\s*" "Age: 33")')
    assert list(parts) == ["Age", ": ", "33"]
    assert rx.eval('(re-replace-all "a+" "X" "banana")') == ["bXnXnX"]
    assert rx.eval(r'(re-replace "(?<y>\\d+)" "[$y]" "n 42 n")') == ["n [42] n"]


def test_regex_captures_are_typed(rx):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (groups,) = rx.eval(
        r'(re-captures "(?<year_I>\\d\\d\\d\\d)-(?<month_I>\\d\\d)" "2017-04-20")'
    )
    assert str(groups) == '((0 "2017-04") (month 4) (year 2017))'
    pairs = {str(pair[0]): pair[1] for pair in groups}
    assert pairs["year"] == 2017  # the _I suffix answered an integer
    assert pairs["month"] == 4
    assert rx.eval('(re-captures "^x" "abc")') == []  # no match, no answer


def test_compound_captures_keep_their_functor_in_every_seat(rx):
    """Native minus terms retain their functor even with Janus tuple support."""
    [groups] = rx.fn.re_captures(G("(?<span_R>é)(?<term_T>1-2)"), G("é1-2"))
    assert groups == Expression((Expression((0, G("é1-2"))),
                                 S.span(S["-"](0, 1)), S.term(S["-"](1, 2))))
    assert rx.eval('(index-atom (index-atom (index-atom '
                   '(re-captures "(?<x_R>.)" "é") 1) 1) 0)') == [S["-"]]


def test_regex_guards_queries(rx, metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as m:
        m.add(S.person(S.Ada), S.person(S.alan), S.person(S.Alice))
        rows = m.match(S.person(V.name), where='(re-match "^A" $name)')
        assert [row.name for row in rows] == [S.Ada, S.Alice]


def test_compiled_regex_values_cross_the_wire(rx):
    """The compiled handle remains the same usable value after wire transport."""
    [pattern] = rx.fn.re_compile(G(r"(?<n_I>\d+)"))
    restored = convert.atom_from_wire(pattern.to_wire())
    try:
        assert restored == pattern
        assert "_NativeHandle(" in repr([restored])
        assert rx.fn.re_match(restored, G("x007 y8")) == [True]
        assert rx.fn.re_fullmatch(restored, G("007")) == [True]
        assert rx.fn.re_fullmatch(restored, G("x007")) == [False]
        assert rx.fn.re_find(restored, G("x007 y8")) == ["007", "8"]
        assert rx.fn.re_count(restored, G("x007 y8")) == [2]
        assert str(rx.fn.re_captures(restored, G("x007"))[0]) == '((0 "007") (n 7))'
        assert [str(row) for row in rx.fn.re_scan(restored, G("x007 y8"))] == [
            '((0 "007") (n 7))', '((0 "8") (n 8))',
        ]
        assert [list(row) for row in rx.fn.re_ranges(restored, G("x007 y8"))] == [[1, 3], [6, 1]]
        assert list(rx.fn.re_split(restored, G("x007 y8"))[0]) == ["x", "007", " y", "8", ""]
        assert rx.fn.re_replace(restored, G("[$n]"), G("x007 y8")) == ["x[7] y8"]
        assert rx.fn.re_replace_all(restored, G("[$n]"), G("x007 y8")) == ["x[7] y[8]"]
    finally:
        restored.release()
        pattern.release()


@settings(deadline=None)
@given(pattern=st.sampled_from(("", "a*?", "(?:a|)", "(?=a)", "(a)?b", "(a|b)+", "^|$", "(?s).", "é*")),
       text=st.text(alphabet=("a", "b", "é", "🦊", "\n", "\r", "\u0301", "\0"), max_size=40))
def test_match_progression_agrees_with_python_re(rx, pattern, text):
    """An independent regex engine checks empty alternatives and Unicode spans."""
    expected = list(re.finditer(pattern, text))
    [compiled] = rx.fn.re_compile(G(pattern))
    try:
        for source in (G(pattern), compiled):
            assert rx.fn.re_find(source, G(text)) == [match.group() for match in expected]
            assert [list(row) for row in rx.fn.re_ranges(source, G(text))] == [
                [match.start(), match.end() - match.start()] for match in expected
            ]
            assert rx.fn.re_count(source, G(text)) == [len(expected)]
    finally:
        compiled.release()


@settings(deadline=None)
@given(st.text(alphabet=("a", "é", "🦊", "\n", "\0", "\\", "E", "Q", "[", "]", "$", "#", " "), max_size=40))
def test_quoted_literal_round_trips(rx, text):
    """Literal quoting covers NUL, quote terminators and extended-mode text."""
    [quoted] = rx.fn.re_escape(G(text))
    assert rx.fn.re_fullmatch(quoted, G(text)) == [True]
    assert rx.fn.re_fullmatch(G("(?x)" + quoted.value), G(text)) == [True]
