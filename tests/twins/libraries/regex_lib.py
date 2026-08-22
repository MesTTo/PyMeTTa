"""Purpose: examples/libraries/regex_lib.metta in Python: PCRE2 through lib_regex.

Every claim is about one of the library's six functions, so the twin names all
six. Two things are Python's: the patterns, written as raw strings so a
backslash is a backslash without the doubling MeTTa's string reader needs, and
the answer shapes, which are lists and plain values.

`re-find` answers one match per solution, so its Python door is `.all(...)`
rather than a `collapse` around it; `re-captures` answers whole-match, named
and typed groups in one expression, which stays an expression because that is
what the library returns.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 60456 to 55103, -5353 (-8.85%), by the idiomatic
#: rewrite: seven `test` wrappers and a `collapse` left the engine for
#: `assert` and `.all()`; the six PCRE2 calls remain. Measured min-of-three
#: with the MORK backend linked into this worktree, which the earlier figure
#: may not have been. Prior: 60456 was the last figure for the generator twin
#: that yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 55103


def twin(m):
    """Match, find, capture, split and replace, all through lib_regex."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_regex)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    # A boolean guard: (?i) is PCRE2's inline case-insensitivity flag.
    assert m.fn("re-match")(val("(?i)^needle"), val("Needle in a haystack")) is True
    assert m.fn("re-match")(val("^x"), val("abc")) is False

    # Enumeration: one answer per match, which is nondeterminism, not a list.
    found = m.fn("re-find").all(val(r"\d+"), val("a1 b22 c333"))
    assert found == [val("1"), val("22"), val("333")]

    # A capture name ending in _I asks for the group as a Number, so `month`
    # and `year` arrive as 4 and 2017 rather than as "04" and "2017".
    captures = m.fn("re-captures")(
        val(r"(?<year_I>\d\d\d\d)-(?<month_I>\d\d)"), val("2017-04-20")
    )
    assert list(captures) == [Expression((0, val("2017-04"))), S.month(4), S.year(2017)]

    # Split keeps the separator it matched, so the pieces and the gaps alternate.
    pieces = m.fn("re-split")(val(r":\s*"), val("Age: 33"))
    assert list(pieces) == [val("Age"), val(": "), val("33")]

    assert m.fn("re-replace-all")(val("a+"), val("X"), val("banana")) == val("bXnXnX")
    assert m.fn("re-replace")(val(r"(?<y>\d+)"), val("[$y]"), val("n 42 n")) == val("n [42] n")
