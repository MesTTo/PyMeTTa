r"""Purpose: lib_regex from Python: the engine's PCRE2 surface answers
through eval, composes as a query guard, and carries typed named
captures. A MeTTa string reads a doubled backslash as one, so a raw
Python string spelling "\\d" reaches PCRE as the digit class.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import S, V


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


def test_regex_guards_queries(rx, metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as m:
        m.add(S.person(S.Ada), S.person(S.alan), S.person(S.Alice))
        rows = m.match(S.person(V.name), where='(re-match "^A" $name)')
        assert [row.name for row in rows] == [S.Ada, S.Alice]
