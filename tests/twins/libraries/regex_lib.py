"""Purpose: examples/libraries/regex_lib.metta in Python: PCRE2 through lib_regex.

Every claim is about one of the library's six functions, so the twin names all
six through the function namespace. Two things are Python's: the patterns,
written as raw strings so a backslash is a backslash without the doubling
MeTTa's string reader needs, and the answer shapes, which are lists and plain
values.

`re-find` answers one match per solution, so the whole answer view is the list
of matches; `re-captures` answers whole-match, named and typed groups in one
expression, which stays an expression because that is what the library returns.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Match, find, capture, split and replace, all through lib_regex."""
    m.fn["import!"](m, S.library(S["lib_regex"]))

    # A boolean guard: (?i) is PCRE2's inline case-insensitivity flag.
    re_match = m.fn.re_match
    assert re_match(G("(?i)^needle"), G("Needle in a haystack")) == [True]
    assert re_match(G("^x"), G("abc")) == [False]

    # Enumeration: one answer per match, which is nondeterminism, not a list.
    found = m.fn.re_find(G(r"\d+"), G("a1 b22 c333"))
    assert found == [G("1"), G("22"), G("333")]

    # A capture name ending in _I asks for the group as a Number, so `month`
    # and `year` arrive as 4 and 2017 rather than as "04" and "2017".
    [captures] = m.fn.re_captures(
        G(r"(?<year_I>\d\d\d\d)-(?<month_I>\d\d)"), G("2017-04-20")
    )
    assert list(captures) == [Expression((0, G("2017-04"))), S.month(4), S.year(2017)]

    # Split keeps the separator it matched, so the pieces and the gaps alternate.
    [pieces] = m.fn.re_split(G(r":\s*"), G("Age: 33"))
    assert list(pieces) == [G("Age"), G(": "), G("33")]

    assert m.fn.re_replace_all(G("a+"), G("X"), G("banana")) == [G("bXnXnX")]
    assert m.fn.re_replace(G(r"(?<y>\d+)"), G("[$y]"), G("n 42 n")) == [G("n [42] n")]
