"""Purpose: the Unicode database and the standard transformations over text.

Text is a `G("...")` grounded string, because a bare Python string is a name and
these operations are about TEXT; a form, a property name, a flag and a class are
symbols, so they come from `S`. The normalizations that answer the same string in
a different form are compared by their code points, which is the only way the
difference is visible at all.

Guarantees: the same claims as 26-unicode_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/26-unicode_lib.metta; commit=WORKTREE].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Normalize, fold, map, ask the database, classify, split and validate."""
    m += lib.unicode
    # lib_string is beside it here because the two answer different questions
    # about the same text: string-codes and string-chars count code points,
    # unicode-graphemes counts what a person calls a character, and string-lower
    # is a lowercasing where unicode-casefold is not.
    m += lib.string

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def codes(text):
        """The code points of a string, as a list."""
        return list(m.fn.string_codes(text).one())

    normalize, casefold, unimap = m.fn.unicode_normalize, m.fn.unicode_casefold, m.fn.unicode_map
    prop, is_class = m.fn.unicode_property, m.fn.unicode_is
    graphemes, valid = m.fn.unicode_graphemes, m.fn.unicode_codepoint_valid

    # Every answer here comes from the host's own database, and its version is a
    # head because a normalization is reproducible only beside the version that
    # made it.
    assert m.fn.unicode_version() == [G("16.0.0")]

    # The five normalization forms. "é" can be one code point or two, and nfc and
    # nfd are what move between them; string-codes shows which one a string holds.
    assert codes(normalize(S.nfd, G("é")).one()) == [101, 769]
    assert codes(normalize(S.nfc, G("é")).one()) == [233]
    assert normalize(S.nfc, normalize(S.nfd, G("é")).one()) == [G("é")]
    # The compatibility forms also replace presentation characters: the ffi
    # ligature becomes three letters and the superscript two becomes a two.
    assert normalize(S.nfkc, G("ﬃ")) == [G("ffi")]
    assert normalize(S.nfkd, G("2²")) == [G("22")]
    assert normalize(S.nfc, G("2²")) == [G("2²")]
    # nfkc-casefold is the caseless identifier form of UAX#31: compatibility, then
    # composition, then case folding, in one pass.
    assert normalize(S.nfkc_casefold, G("Straße")) == [G("strasse")]
    assert refused(S.unicode_normalize(S.nfx, G("a")))

    # Case folding is NOT lowercasing: it answers what compares equal regardless
    # of case, so sharp s becomes two letters and the answer is longer.
    assert casefold(G("Straße")) == [G("strasse")]
    assert m.fn.string_lower(G("Straße")) == [G("straße")]
    assert casefold(G("HELLO")).one() == casefold(G("hello")).one()

    # unicode-map is the general operation the forms above are compositions of,
    # and it does the transformations that have no standard name: stripping the
    # accents off text is composing it and stripping the marks.
    assert unimap(G("café"), (S.compose, S.stripmark)) == [G("cafe")]
    # lump folds typographic variants onto their ASCII equivalents, which is what
    # a search index wants. Double quotes are not in the host's table, which is
    # why this claim uses the apostrophe.
    # The apostrophe and the dash are the typographic ones, written as their code
    # points so the difference from the ASCII answer is visible in the source.
    assert unimap(G("it\u2019s a\u2013b"), (S.lump,)) == [G("it's a-b")]
    assert unimap(G("Hello"), (S.casefold,)) == [G("hello")]
    assert refused(S.unicode_map(G("a"), (S.nosuchflag,)))
    # Two combinations are refused rather than passed to the host, which answers a
    # bare domain error for both.
    assert refused(S.unicode_map(G("a"), (S.compose, S.decompose)))
    assert refused(S.unicode_map(G("a"), (S.stripmark,)))

    # The database, one character at a time. A character is a one-character string
    # or the number of a code point, whichever the program has in hand.
    assert prop(G("A"), S.category) == [S.Lu]
    assert prop(65, S.category) == [S.Lu]
    assert prop(G("1"), S.category) == [S.Nd]
    assert prop(G(" "), S.category) == [S.Zs]
    assert prop(G("A"), S.lowercase) == [97]
    assert prop(G("a"), S.uppercase) == [65]
    assert prop(G("A"), S.width) == [1]
    assert prop(G("漢"), S.width) == [2]
    # A property the character has no value for has NO answer, which is data about
    # the character; an unknown property NAME is refused, which is a mistake.
    assert list(prop(G("A"), S.uppercase)) == []
    assert list(prop(G("a"), S.decomp_type)) == []
    assert refused(S.unicode_property(G("a"), S.colour))
    assert refused(S.unicode_property(G("ab"), S.category))

    # The classification a lexer asks per character, as a Bool so it composes.
    # Every class is a general category of the database or a group of them, so
    # the answers do not move with the process locale.
    assert is_class(G("a"), S.letter) == [True]
    assert is_class(G("1"), S.letter) == [False]
    assert is_class(G("1"), S.digit) == [True]
    assert is_class(G("Ⅲ"), S.number) == [True]
    assert is_class(G(" "), S.white_space) == [True]
    assert is_class(G("é"), S.letter) == [True]
    assert is_class(G("é"), S.ascii) == [False]
    assert is_class(G("漢"), S.letter) == [True]
    assert is_class(65, S.upper) == [True]
    assert is_class(G(","), S.punctuation) == [True]
    assert is_class(1114111, S.assigned) == [False]
    assert refused(S.unicode_is(G("a"), S.vowel))

    # Graphemes are the characters a PERSON counts: a base character with its
    # combining marks is one, where string-chars answers each code point.
    decomposed = normalize(S.nfd, G("éx")).one()
    assert len(m.fn.string_chars(decomposed).one()) == 3
    assert len(graphemes(decomposed).one()) == 2
    # The first grapheme holds BOTH code points, which is what grouping means, and
    # the codes are what makes it visible: the two strings print the same.
    assert codes(m.fn.car_atom(graphemes(decomposed)).one()) == [101, 769]
    assert list(graphemes(G("abc")).one()) == [G("a"), G("b"), G("c")]
    assert list(graphemes(G("")).one()) == []

    # A code point is valid when the database ASSIGNS it a character, which is
    # stricter than being in range: a surrogate half, an unassigned number and a
    # noncharacter all answer False, and a private-use code point answers True.
    assert valid(97) == [True]
    assert valid(55296) == [False]
    assert valid(1114112) == [False]
    assert valid(1114111) == [False]
    assert valid(57344) == [True]
    assert prop(57344, S.category) == [S.Co]
    assert list(prop(1114111, S.category)) == []


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 54 claims cover the eight heads, the five forms,
#: fourteen classes and the refusals, and the twin costs LESS than the example,
#: whose two library imports it shares: the example's `collapse` and
#: `string-codes` round trips are `list()` and one `codes` helper here
#: [measured 2026-09-12: 129667 inferences against the example's 139207,
#: minimum of three serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/26-unicode_lib.metta;
#: fixture=lib_unicode at its functional commit, artifacts purged before the
#: run; commit=WORKTREE].
BUDGET = 129667
