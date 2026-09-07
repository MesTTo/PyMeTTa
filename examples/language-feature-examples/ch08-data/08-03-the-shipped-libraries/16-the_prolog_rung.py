"""examples/ch08-data/08-03-the-shipped-libraries/16-the_prolog_rung.metta in Python: the rung under five libraries.

Every underscore name here is a Prolog predicate a library imported, and the
hyphenated MeTTa name above it is one equation over it. Python's own map
turns an underscore into a hyphen, so every one of these comes through the
exact subscript door and the pairs that compare them are what says the two
spellings are one operation.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import G, S, lib

#: The provider the conformance kit is asked about, as a host path.
_REPO = Path(__file__).resolve().parents[6]
PROVIDER = _REPO / Path(
    "examples/ch08-data/08-03-the-shipped-libraries/_fixtures/demo_provider.pl"
)

#: What a healthy provider reports about itself, in the engine's own prose.
REPORT = (
    G("match: declared, seam:foreign_match/3 has clauses"),
    G("enumerate: declared, seam:foreign_atoms/2 has clauses"),
    G("match: over-approximation holds over 2 atoms and their pattern families"),
    G("source: repeated, two enumerations agree"),
    G(
        "round trip: not asked, the provider does not declare add, remove and "
        "enumerate together"
    ),
    G("pushdown: 0 of 2 patterns claimed exact, and are"),
    G("plan: not declared, so a conjunction takes the engine's split"),
)

TEXT_SHA256 = G("982d9e3eb996f559e633f4d194def3761d909f5a3b647d1a851fead67c32c9d1")


def twin(m):
    """Regex, hashes, dates and the conformance kit, called one rung down."""
    for library in (lib.string, lib.regex, lib.crypto, lib.datetime, lib.conformance):
        m += library

    # lib_regex's six. `re-match` is one equation over `regex_match`.
    assert m.fn["regex_match"](G("(?i)^needle"), G("Needle in a haystack")) == [True]
    assert m.fn["regex_match"](G("^x"), G("abc")) == m.fn["re-match"](G("^x"), G("abc"))
    assert m.fn["regex_find"](G(r"\d+"), G("a1 b22 c333")) == [G("1"), G("22"), G("333")]
    assert m.fn["regex_captures"](G(r"(?<y_I>\d+)"), G("n 42")) == [
        ((0, G("42")), S.y(42))
    ]
    assert m.fn["regex_split"](G(r":\s*"), G("Age: 33")) == [(G("Age"), G(": "), G("33"))]
    assert m.fn["regex_replace"](G("a"), G("X"), G("banana")) == [G("bXnana")]
    assert m.fn["regex_replace_all"](G("a"), G("X"), G("banana")) == [G("bXnXnX")]

    # lib_crypto's two. A digest is a content key.
    assert m.fn["crypto_hash"](S.sha256, G("text")) == [TEXT_SHA256]
    assert m.fn["crypto_hash"](S.sha256, G("text")) == m.fn["crypto-hash"](
        S.sha256, G("text")
    )
    assert m.fn["crypto_hash"](S.sha256, G("other")) != [TEXT_SHA256]

    # Randomness is the other way round: two hex characters per byte asked
    # for, and never the same ones twice.
    assert m.fn["string-length"](m.fn["crypto-random-hex"](8)[0]) == [16]
    assert m.fn["string-length"](m.fn["crypto_random_hex"](16)[0]) == [32]
    assert m.fn["crypto-random-hex"](16) != m.fn["crypto-random-hex"](16)

    # lib_datetime's two, over Unix time. The epoch is a Thursday, which is
    # the one date this can assert without asking what day it is.
    assert m.fn["day_of_week"](0) == [S.Thursday]
    assert m.fn["format_date"](0, G("%Y-%m-%d")) == [S["1970-01-01"]]
    assert m.fn["day_of_week"](0) == m.fn["day-of-week"](0)
    assert m.fn["format_date"](0, G("%H:%M:%S")) == m.fn["format-date"](0, G("%H:%M:%S"))

    # lib_conformance's one, which is the whole library.
    m.register_prolog(path=PROVIDER)
    provider = m.metta.space(S["demo_provider"])
    assert m.fn["metta_check_space_provider"](provider) == [REPORT]
    assert m.fn["metta_check_space_provider"](provider) == m.fn[
        "check-space-provider"
    ](provider)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 131980 inferences, 0.9699x the example's 136076; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 131980
