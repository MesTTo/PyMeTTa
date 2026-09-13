"""Purpose: compose grammar values and inspect their ordinary parser functions.

A grammar is a built term, so every form is `S.<name>(...)` and the whole grammar
is an ordinary Python value that can be named and reused. The grammar parameter
is held, which is what lets the term through unevaluated; text is `G("...")`
because these operations are about TEXT. A parse that matches many ways is many
answers, so `list()` is the example's `collapse` and `.one()` the single answer.

`letter?`, `double`, `sum`, `field` and `row` are `@m.define` functions, and the
two that answer a GRAMMAR return the built term, which is what `ref` evaluates
when the parse reaches it.

Guarantees: the same claims as 27-parsing_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/27-parsing_lib.metta; commit=3c1d074a2069bc150a95cedc1946e0627a17a132].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, V, fn, lib
from metta._errors.errors import MettaError


def twin(m):
    """Build grammars, run them whole and by prefix, and refuse a bad one."""
    m += lib.parsing
    # lib_unicode is beside it for the one primitive that takes a FUNCTION: the
    # classes here are ASCII, and a Unicode class is (char-if f) over unicode-is.
    m += lib.unicode

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def values(answers):
        """Every answer of a parse, as a list."""
        return list(answers)

    def elements(answers):
        """One answer's expression, as a list."""
        return list(answers.one())

    def rows(answers):
        """One answer's expression of expressions, as a list of tuples."""
        return [tuple(row) for row in answers.one()]

    parse, prefix = m.fn.grammar_parse, m.fn.grammar_parse_prefix
    forms, is_grammar = m.fn.grammar_forms, m.fn.grammar_is

    # A grammar is an expression, and grammar-parse runs it over the whole text.
    # Every way it matches is an answer, so a grammar that does not match answers
    # NOTHING rather than raising, which is what makes the combinators compose.
    assert parse(S.lit(G("ab")), G("ab")) == [G("ab")]
    assert values(parse(S.lit(G("ab")), G("ax"))) == []
    assert values(parse(S.lit(G("ab")), G("abc"))) == []

    # The primitives. A leaf answers the text it matched, except the two numbers,
    # which answer the number, and eos, which answers ().
    assert parse(S.any(), G("x")) == [G("x")]
    assert parse(S.char_in(G("aeiou")), G("e")) == [G("e")]
    assert values(parse(S.char_in(G("aeiou")), G("z"))) == []
    assert parse(S.char_not_in(G("aeiou")), G("z")) == [G("z")]
    assert parse(S.digits(), G("1024")) == [G("1024")]
    assert parse(S.integer(), G("-42")) == [-42]
    assert parse(S.number(), G("3.5")) == [3.5]
    assert parse(S.nonblanks(), G("word")) == [G("word")]
    assert parse(S.blanks(), G("  ")) == [G("  ")]
    assert parse(S.blanks(), G("")) == [G("")]
    assert parse(S.until(G(",")), G("ab")) == [G("ab")]
    assert parse(S.quoted(), G('"a\\nb"')) == [G("a\nb")]
    assert parse(S.rest(), G("whatever")) == [G("whatever")]
    assert elements(parse(S.eos(), G(""))) == []

    # char-if takes a FUNCTION, applied where the grammar was written, so a class
    # the primitives do not have is one line: this is Unicode's own letter class,
    # which holds for a letter no ASCII test would accept.
    @m.define(name="letter?")
    def letter(c):
        return fn.unicode_is(c, S.letter)

    assert elements(parse(S.many1(S.char_if(S["letter?"])), G("héllo"))) == [
        G("h"), G("é"), G("l"), G("l"), G("o"),
    ]
    assert values(parse(S.char_if(S["letter?"]), G("1"))) == []

    # cat runs its parts in turn and answers their values; skip drops one, so a
    # separator contributes nothing to the answer.
    assert elements(parse(S.cat(S.digits(), S.lit(G("-")), S.digits()), G("12-34"))) == [
        G("12"), G("-"), G("34"),
    ]
    assert elements(parse(S.cat(S.digits(), S.skip(S.lit(G("-"))), S.digits()), G("12-34"))) == [
        G("12"), G("34"),
    ]
    assert elements(parse(S.cat(S.skip(S.lit(G("#"))), S.rest()), G("#tag"))) == [G("tag")]

    # alt answers once per branch that matches, which is a superposition and not a
    # first-match choice: a grammar that is ambiguous says so. Both branches match
    # "12" here.
    assert values(parse(S.alt(S.digits(), S.nonblanks()), G("12"))) == [G("12"), G("12")]
    assert values(parse(S.alt(S.lit(G("a")), S.lit(G("b"))), G("a"))) == [G("a")]
    assert values(parse(S.alt(S.any(), S.rest()), G("x"))) == [G("x"), G("x")]
    assert values(parse(S.alt(S.lit(G("a")), S.lit(G("b"))), G("c"))) == []

    # many and many1 repeat, longest match first; optional answers (V) or ().
    assert elements(parse(S.many(S.char_in(G("ab"))), G("aab"))) == [G("a"), G("a"), G("b")]
    assert elements(parse(S.many(S.char_in(G("ab"))), G(""))) == []
    assert values(parse(S.many1(S.char_in(G("ab"))), G(""))) == []
    # The optional's own value is a collection, so a cat over it answers a
    # collection and a string side by side: (("-") "7") signed, (() "7") not.
    signed = list(parse(S.cat(S.optional(S.lit(G("-"))), S.digits()), G("-7")).one())
    assert [list(signed[0]), signed[1]] == [[G("-")], G("7")]
    unsigned = list(parse(S.cat(S.optional(S.lit(G("-"))), S.digits()), G("7")).one())
    assert [list(unsigned[0]), unsigned[1]] == [[], G("7")]

    # sep-by is the list a separator holds, and its values are the parts only.
    assert elements(parse(S.sep_by(S.digits(), S.lit(G(","))), G("1,2,3"))) == [
        G("1"), G("2"), G("3"),
    ]
    assert elements(parse(S.sep_by(S.digits(), S.lit(G(","))), G("1"))) == [G("1")]
    assert elements(parse(S.sep_by(S.digits(), S.lit(G(","))), G(""))) == []

    # between drops both ends and token eats the blanks around a part, which is
    # what a language with free whitespace needs.
    assert parse(S.between(S.lit(G("(")), S.digits(), S.lit(G(")"))), G("(5)")) == [G("5")]
    assert parse(S.token(S.digits()), G("  5 ")) == [G("5")]
    assert elements(parse(S.sep_by(S.token(S.digits()), S.lit(G(","))), G(" 1 , 2 "))) == [
        G("1"), G("2"),
    ]

    # map applies a function to a value and as tags one, so a grammar builds the
    # parse TREE rather than a list of strings to read again.
    @m.define
    def double(n):
        return fn.mul(2, n)

    assert parse(S.map(S.double, S.integer()), G("21")) == [42]
    assert elements(parse(S["as"](S.amount, S.integer()), G("7"))) == [S.amount, 7]
    assert rows(parse(S.many(S["as"](S.digit, S.char_in(G("12")))), G("12"))) == [
        (S.digit, G("1")), (S.digit, G("2")),
    ]

    # A grammar refers to itself through ref, which evaluates a function of no
    # arguments when the parse reaches it, so a nested language is expressible.
    # This one is a parenthesised sum of numbers.
    # The text inside a COMPILED body is a plain Python string literal, not
    # G("("): a G(...) there is a host object the grammar check refuses, where a
    # literal lowers to the String the form wants.
    @m.define
    def sum_():
        return S.alt(
            S.integer(),
            S.between(S.lit("("), S.sep_by(S.ref(S.sum_), S.lit("+")), S.lit(")")),
        )

    assert parse(S.ref(S.sum_), G("7")) == [7]
    assert elements(parse(S.ref(S.sum_), G("(1+2)"))) == [1, 2]
    # A number is a leaf and a nested sum is a collection, so the nesting is read
    # by asking each part whether it holds anything.
    nested = list(parse(S.ref(S.sum_), G("(1+(2+3))")).one())
    assert nested[0] == 1
    assert list(nested[1]) == [2, 3]
    assert values(parse(S.ref(S.sum_), G("(1+)"))) == []

    # A prefix parse answers the value with the unread rest, which is how a reader
    # takes one construct at a time. The longest match comes first.
    assert elements(prefix(S.digits(), G("12ab"))) == [G("12"), G("ab")]
    # The first answer is the greedy one, taken without draining the rest.
    longest = next(iter(prefix(S.many(S.char_in(G("ab"))), G("aab!"))))
    assert [list(longest[0]), longest[1]] == [[G("a"), G("a"), G("b")], G("!")]
    assert elements(prefix(S.rest(), G("all"))) == [G("all"), G("")]
    assert values(prefix(S.lit(G("z")), G("ab"))) == []

    # A real format, in seven forms: a CSV row of quoted or bare fields. The bare
    # field stops at a QUOTE as well as at a comma, which is what makes the
    # grammar unambiguous.
    @m.define
    def field():
        return S.alt(S.quoted(), S.until(',"'))

    @m.define
    def row():
        return S.cat(S.sep_by(S.ref(S.field), S.lit(",")), S.skip(S.eos()))

    assert [list(part) for part in parse(S.ref(S.row), G("a,b,c")).one()] == [
        [G("a"), G("b"), G("c")],
    ]
    assert [list(part) for part in parse(S.ref(S.row), G('"x,y",z')).one()] == [
        [G("x,y"), G("z")],
    ]

    # The vocabulary is data, and a value that is not a grammar is refused BEFORE
    # any text is read, naming the form that is wrong rather than answering
    # nothing.
    assert len(forms().one()) == 26
    assert is_grammar(S.cat(S.digits(), S.eos())) == [True]
    assert is_grammar(S.lit(7)) == [False]
    assert is_grammar(S.many()) == [False]
    assert is_grammar(7) == [False]
    assert refused(S.grammar_parse(S.nosuch(), G("a")))
    assert refused(S.grammar_parse(S.cat(S.digits(), S.nosuch()), G("1")))
    # A number where the text belongs is refused by the DECLARATION rather than by
    # the head, so it answers the engine's own BadArgType; if-error reads both the
    # same way.
    assert list(m.eval(S.grammar_parse(S.digits(), 7))) == [
        S.Error(S.grammar_parse(S.digits(), 7), S.BadArgType(2, S.String, S.Number)),
    ]

    assert is_grammar(S.alt()) == [True]
    assert values(parse(S.alt(), G(""))) == []
    assert parse(S.cat(), G("")) == [()]
    assert prefix(S.many(S.any()), G("ab")) == [
        ((G("a"), G("b")), G("")), ((G("a"),), G("b")), ((), G("ab")),
    ]
    assert parse(S.many(S.skip(S.lit(G("x")))), G("xx")) == [((), ())]
    literal = S["+"](1, 2)
    callback = S["|->"]((V.text,), S.quote(literal))
    assert parse(S.map(callback, S.any()), G("x")) == [literal]
    error = S.Error(S.data, S.code)
    callback = S["|->"]((V.text,), S.quote(error))
    assert parse(S.map(callback, S.any()), G("x")) == [error]
    callback = S["|->"]((V.text,), S.quote(S.Empty))
    assert parse(S.map(callback, S.any()), G("x")) == [S.Empty]
    callback = S["|->"]((V.text,), S.quote((V.x, V.y, V.x)))
    assert m.eval(S["=="](S.grammar_parse(S.map(callback, S.any()), G("x")),
                          S.quote((V.x, V.y, V.x)))) == [True]

    parser = m.fn.grammar_parser(S.any()).one()
    assert m.fn.apply_to(parser, S.quote(((literal, S.Empty),))) == [((literal,), (S.Empty,))]
    parser = m.fn.grammar_parser(S.lit(G("x"))).one()
    assert m.fn.get_metatype(parser) == [S.Expression]
    recipe = m.match(S["="](S.grammar_parser(V.grammar), V.body)).one()
    compile_grammar = m.eval(S["|->"]((recipe.grammar,), recipe.body))[0]
    parser = m.fn.apply_to(compile_grammar, (S.digits(),)).one()
    assert m.fn.apply_to(parser, ((G("1"), G("2"), G("!")),)) == [((G("12"),), (G("!"),))]

    m.add(S.parsing_form(S.pure_value, (S.Atom,), S.parsing_example_value))
    m.add(S[":"](S.parsing_example_value, S["->"](S.Atom, S.Atom, S.Expression)))
    m.add(S["="](S.parsing_example_value(V.value, V.input), S.quote(((V.value,), V.input))))
    assert parse(S.pure_value(literal), G("")) == [literal]
    assert len(forms().one()) == 27
    # This assertion is literal code: grammar-is must not execute the ref target.
    never = (S["|->"], (), (S.assertEqual, False, True))
    assert is_grammar(S.ref(never)) == [True]
    assert refused(S.grammar_parse(S.many(S.cat()), G("")))


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 58 claims cover the fourteen primitives, the
#: eleven combinators, the recursion through ref, the prefix parse and the
#: refusals, and the two sides cost almost exactly the same: a grammar is a TERM,
#: so building one in Python and writing one in MeTTa are the same work, and the
#: five compiled definitions are what the twin pays extra for
#: [measured 2026-09-12: 90024 inferences against the example's 89803, minimum of
#: three serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/27-parsing_lib.metta;
#: fixture=lib_parsing at its functional commit, artifacts purged before the run;
#: commit=7bdd5ace3f8272c2806ac0b925e56a78dc0894a8].
#: RE-PINNED 2026-09-12, 90024 to 89855 (-169), the greedy prefix answer taken
#: through next(iter(...)) rather than a list slice, which stops draining the
#: rest [measured 2026-09-12: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7bdd5ace3f8272c2806ac0b925e56a78dc0894a8].
#: RE-PINNED 2026-09-14, 89855 to 4666804 (+4576949), Parsing derives written
#: callable grammars and literal contributions in MeTTa, adding sixteen
#: executable claims [measured 2026-09-14: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=3c1d074a2069bc150a95cedc1946e0627a17a132].
#: RE-PINNED 2026-09-14, 4666804 to 4666705 (-99), The parsing twin uses
#: shared-context identity comparison and holds the ref assertion as literal
#: code [measured 2026-09-14: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3c1d074a2069bc150a95cedc1946e0627a17a132].
#: RE-PINNED 2026-09-14, 4666705 to 4701005 (+34300), String now derives nine
#: text recipes through MeTTa equations, with one function parameter for
#: padding and complete validation before empty construction; all import
#: consumers are measured after the provider change [measured 2026-09-14: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4701005
