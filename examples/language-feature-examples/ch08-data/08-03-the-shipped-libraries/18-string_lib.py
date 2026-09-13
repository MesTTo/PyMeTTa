"""Purpose: use every String head through Python values and the typed library.

Guarantees: this twin preserves every example claim and both optional forms
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/18-string_lib.metta; commit=WORKTREE].
"""

from metta import G, S, V, lib


def twin(m):
    """Combine text recipes and native boundaries through their typed face."""
    m += lib.string
    fn = m.fn
    assert fn.string_length(G("a🦊é")).one() == 3
    assert fn.string_slice(G("a🦊é"), 1, 99) == [G("🦊é")]
    assert list(fn.string_split(G(",;"), G("a,b;;c")).one()) == [G("a"), G("b"), G(""), G("c")]
    assert list(fn.string_split_exact(G("::"), G("::a::::")).one()) == [G(""), G("a"), G(""), G("")]
    assert fn.string_join(G(" / "), (G("a"), G("b"))) == [G("a / b")]
    assert fn.string_trim(G(" \ta\r\n")) == [G("a")]
    assert fn.string_upper(S.hello) == [G("HELLO")]
    assert fn.string_lower(G("HELLO")) == [G("hello")]
    assert fn.string_starts_with(G("a🦊é"), G("a🦊")).one() is True
    assert fn.string_ends_with(G("a🦊é"), G("é")).one() is True
    assert fn.string_contains(G("a🦊é"), G("🦊")).one() is True
    assert fn.string_index_of(G("banana"), G("ana")).one() == 1
    assert fn.string_last_index_of(G("banana"), G("ana")).one() == 3
    assert fn.string_count(G("aaaaa"), G("aa")).one() == 2
    assert fn.string_count(G("aaaaa"), G("aa"), True).one() == 4  # noqa: FBT003 -- MeTTa calls take positional arguments.
    assert fn.string_replace(G("aaaaa"), G("aa"), G("X")) == [G("XXa")]
    assert fn.string_replace(G("abc"), G(""), G("X")) == [G("abc")]
    assert fn.string_last_index_of(G("a🦊"), G("")).one() == 2
    assert fn.string_count(G("a🦊"), G("")).one() == 3

    assert list(fn.string_chars(G("a🦊")).one()) == [G("a"), G("🦊")]
    assert fn.string_from_chars((G("ab"), S.c, 42)) == [G("abc42")]
    assert list(fn.string_codes(G("a🦊")).one()) == [97, 129418]
    assert fn.string_from_codes((97, 129418)) == [G("a🦊")]
    text = fn.string_from_codes((97, 0, 129418)).one()
    assert list(fn.string_codes(G(text)).one()) == [97, 0, 129418]
    assert fn.string_repeat(G("ab"), 3) == [G("ababab")]
    assert fn.string_pad_left(G("x"), 4, G("ab")) == [G("abax")]
    assert fn.string_pad_right(G("x"), 4, G("ab")) == [G("xaba")]
    assert fn.string_center(G("x"), 6, G("ab")) == [G("abxaba")]

    assert list(fn.string_lines(G("a\n\nb\n")).one()) == [G("a"), G(""), G("b")]
    assert fn.string_unlines((G("a"), G(""), G("b"))) == [G("a\n\nb\n")]
    assert fn.string_dedent(G("  a\n  b\n")) == [G("a\nb\n")]
    assert fn.string_indent(G("> "), G("a\n \nb\n")) == [G("> a\n \n> b\n")]
    assert fn.string_wrap(G("one two three"), 7) == [G("one two\nthree")]
    assert fn.string_wrap(G("a b c d"), 4, S.justify) == [G("a  b\nc d")]
    values = S.quote(((S.Name, G("Ada")), (S.Value, (S.age, 3))))
    assert fn.string_template(G("Dear {Name}: {Value}. {Missing,none}"), values) == [G("Dear Ada: (age 3). none")]

    assert fn.string_edit_distance(G("kitten"), G("sitting")).one() == 3
    assert fn.string_similarity(G("ab"), G("ac")).one() == 0.5
    assert fn.string_isub(G("language"), G("language")).one() == 1.0
    options = ((S.normalize, True), (S.zero_to_one, True), (S.substring_threshold, 0))
    assert fn.string_isub(G("A.B"), G("ab"), options).one() == 1.0
    assert fn.parse_number(G("0x10")).one() == 16
    assert fn.number_to_string(42) == [G("42")]
    assert list(fn.parse_number(G("not a number"))) == []

    assert fn.string_repeat(42, 2) == [G("4242")]
    assert fn.string_repeat(G(""), 10**24) == [G("")]
    assert fn.string_center(12, 7, 3) == [G("3312333")]
    assert fn.string_center(G("x"), 10**24, G("")) == [G("x")]
    assert fn.string_ends_with(G("ab"), G("abc")).one() is False
    assert fn.if_error(S.catch(S.string_repeat(G(""), 1.5)), True, False).one() is True  # noqa: FBT003 -- MeTTa calls take positional arguments.
    assert fn.string_repeat(G("x"), S.superpose((0, 2))) == [G(""), G("xx")]
    row = m.match(S["="](S.string_repeat(V.value, V.n), V.body)).one()
    recipe = m.eval(S["|->"]((row.value, row.n), row.body))[0]
    assert m.eval((recipe, G("ab"), 2)) == [G("abab")]


#: All thirty-four String heads and thirty-seven typed arities preserve the
#: example's fifty claims through values, function calls and reflected equations.
#: [measured 2026-09-11: 126928 inferences, minimum of three serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/18-string_lib.metta;
#: fixture=String library and warm native provider; commit=3aaad3435292e4c7d5cc3a01bfda39430aacc6e8].
#: RE-PINNED 2026-09-13, 126928 to 127459 (+531), File exports its staged
#: publisher to Compression; the shared native builder accepts the private
#: archive provider recipe. All consumers are remeasured after those dependency
#: changes [measured 2026-09-13: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-14, 127459 to 329461 (+202002), String now derives nine
#: text recipes through MeTTa equations, with one function parameter for
#: padding and complete validation before empty construction; all import
#: consumers are measured after the provider change [measured 2026-09-14: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 329461
