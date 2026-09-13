"""Purpose: compare callable MeTTa parsers with independent finite Python models.

Guarantees: generated grammars preserve answer order and multiplicity, and held
callbacks, literal terms, metadata and reflected functions share the public
parser contract [tested: test_parsing_lib.py; commit=WORKTREE].
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Expression, G, S, V, lib
from metta._errors.errors import AssertionFailure, MettaError, MettaOperationError


@pytest.fixture(scope="module")
def parsing(metta):
    """Keep parser declarations and test callbacks in an owned space."""
    with metta._new_space() as space:
        space += lib.parsing
        yield space


LEAF = st.sampled_from([
    ("any",), ("lit", ""), ("lit", "a"), ("lit", "ab"), ("digits",),
    ("until", ","), ("eos",), ("rest",), ("many", ("any",)),
])
GRAMMAR = st.recursive(
    LEAF,
    lambda inner: st.one_of(
        st.tuples(st.sampled_from(["skip", "optional"]), inner),
        st.tuples(st.sampled_from(["cat", "alt"]), st.lists(inner, max_size=3))
        .map(lambda row: (row[0], *row[1])),
    ), max_leaves=6,
)
TEXT = st.text(alphabet="ab12,! é", max_size=6)


def grammar_term(grammar):
    """Turn the model's syntax into a held grammar expression."""
    head, *args = grammar
    return S[head](*(G(arg) if isinstance(arg, str) else grammar_term(arg) for arg in args))


def atom_value(value):
    """Expected parser strings are grounded text, including nested values."""
    if isinstance(value, str):
        return G(value)
    return tuple(atom_value(item) for item in value)


def parser_model(grammar, text):
    """Enumerate contribution/remainder pairs with Python sequences and slices."""
    head, *args = grammar
    if head == "lit":
        return [((args[0],), text[len(args[0]):])] if text.startswith(args[0]) else []
    if head == "any":
        return [((text[0],), text[1:])] if text else []
    if head == "rest":
        return [((text,), "")]
    if head == "eos":
        return [(((),), "")] if not text else []
    if head in ("digits", "until"):
        size = 0
        while size < len(text) and (text[size] in "0123456789" if head == "digits"
                                    else text[size] not in args[0]):
            size += 1
        return [((text[:size],), text[size:])] if size or head == "until" else []
    if head == "many":
        # This generated form repeats any, so each position contributes one token.
        return [((tuple(text[:size]),), text[size:]) for size in range(len(text), -1, -1)]
    if head == "alt":
        return [answer for part in args for answer in parser_model(part, text)]
    if head == "cat":
        answers = [((), text)]
        for part in args:
            answers = [(prior + given, rest) for prior, unread in answers
                       for given, rest in parser_model(part, unread)]
        return [((given,), rest) for given, rest in answers]
    answers = parser_model(args[0], text)
    if head == "skip":
        return [((), rest) for _, rest in answers]
    assert head == "optional"
    return [(((given[0] if given else (),),), rest) for given, rest in answers] + [(((),), text)]


@settings(max_examples=100, deadline=None)
@given(GRAMMAR, TEXT)
def test_generated_grammar_answers(parsing, grammar, text):
    """The text doors and ordinary function agree with an independent answer bag."""
    expected = parser_model(grammar, text)
    term = grammar_term(grammar)
    assert parsing.fn.grammar_is(term) == [True]
    assert parsing.fn.grammar_parse(term, G(text)) == [
        atom_value(given[0] if given else ()) for given, rest in expected if not rest
    ]
    assert parsing.fn.grammar_parse_prefix(term, G(text)) == [
        (atom_value(given[0] if given else ()), G(rest)) for given, rest in expected
    ]
    parser = parsing.fn.grammar_parser(term).one()
    assert parsing.fn.apply_to(parser, (tuple(G(char) for char in text),)) == [
        (atom_value(given), tuple(G(char) for char in rest)) for given, rest in expected
    ]


LITERAL = st.recursive(
    st.sampled_from([S.Empty, S.Error, S["$skip"], S["+"], V.x, V.y, 1, 1.0, G("text")]),
    lambda inner: st.lists(inner, max_size=3).map(tuple), max_leaves=5,
)


@settings(max_examples=60, deadline=None)
@given(LITERAL)
def test_literal_mapping_and_tags(parsing, value):
    """A mapped payload and its variable context retain identity after decoding."""
    callback = S["|->"]((V.input,), S.noeval(value))
    grammar = S.map(callback, S.any())
    actual = parsing.eval(S.let(V.result, S.grammar_parse(grammar, G("x")),
                               S.noeval((V.result, V.x, V.y))))
    assert len(actual) == 1
    assert actual[0].alpha_eq(Expression((value, V.x, V.y)))
    wrapped = parsing.eval(S.let(V.result, S.grammar_parse(S.cat(grammar), G("x")),
                                S.noeval((V.result, V.x, V.y))))
    assert wrapped[0].alpha_eq(Expression(((value,), V.x, V.y)))
    tagged = parsing.eval(S.let(V.result, S.grammar_parse(S["as"](value, S.integer()), G("7")),
                               S.noeval((V.result, V.x, V.y))))
    assert tagged[0].alpha_eq(Expression(((value, 7), V.x, V.y)))


def test_callbacks_are_normal_functions_and_keep_alternatives(parsing):
    """Lambda, partial and nondeterministic callbacks cross one value boundary."""
    parsing.run("(= (parsing-prefix-value $tag $value) (quote ($tag $value)))")
    callback = S.parsing_prefix_value(S.tag)
    assert parsing.fn.grammar_parse(S.map(callback, S.any()), G("x")) == [S.tag(G("x"))]
    branches = S["|->"]((V.value,), S.superpose((S.noeval(S.Empty), S.noeval(S.Empty))))
    assert parsing.fn.grammar_parse(S.map(branches, S.any()), G("x")) == [S.Empty, S.Empty]
    verdicts = S["|->"]((V.value,), S.superpose((True, False, S.noeval(S.Error), True)))
    assert parsing.fn.grammar_parse(S.char_if(verdicts), G("x")) == [G("x"), G("x")]
    no_answers = S["|->"]((V.value,), S.empty())
    assert parsing.fn.grammar_parse(S.map(no_answers, S.any()), G("x")) == []
    failure = S["|->"]((V.value,), S.assertEqual(False, True))
    with pytest.raises(AssertionFailure):
        parsing.fn.grammar_parse(S.char_if(failure), G("x")).one()


def test_grammar_checks_hold_constructors_and_callback_positions(parsing):
    """Checking a plan does not evaluate its head, callback, tag or ref target."""
    with parsing._new_space() as space:
        space += lib.parsing
        space.run('''
          (= (lit $text) (assertEqual False True))
          (= (parsing-unreachable) (assertEqual False True))
        ''')
        assert space.fn.grammar_is(S.lit(G("x"))) == [True]
        assert space.fn.grammar_parse(S.lit(G("x")), G("x")) == [G("x")]
        for term in [S.ref(S.parsing_unreachable), S.map(S.parsing_unreachable, S.any()),
                     S.char_if(S.parsing_unreachable), S["as"](S.nosuch(), S.any())]:
            assert space.fn.grammar_is(term) == [True]


def test_metadata_extends_the_same_callable_contract(parsing):
    """A new form supplies a function over values without a native integration."""
    with parsing._new_space() as space:
        space += lib.parsing
        space.run('''
          (parsing-form keep (Atom) parsing-keep)
          (: parsing-keep (-> Atom Atom Expression))
          (= (parsing-keep $value $input) (quote (($value) $input)))
        ''')
        assert space.fn.grammar_is(S.keep(S.Error(S.data, V.x))) == [True]
        parser = space.fn.grammar_parser(S.keep(S["+"](1, 2))).one()
        assert space.fn.apply_to(parser, ((S.Empty,),)) == [((S["+"](1, 2),), (S.Empty,))]
        assert space.fn.grammar_forms().one()[-1] == (S.keep, 1)
        space.run('''
          (parsing-form never () parsing-never)
          (= (parsing-never $input) (assertEqual False True))
        ''')
        assert space.fn.grammar_is(S.never()) == [True]
        with pytest.raises(AssertionFailure):
            space.fn.grammar_parse(S.never(), G("")).one()


@pytest.mark.parametrize("metadata,grammar,remedy", [
    ("(parsing-form bad (Unknown) id)", S.bad(S.x), "argument kinds"),
    ("(parsing-form bad ($kind) id)", S.bad(S.x), "argument kinds"),
    ("(parsing-form lit (Text) id)", S.lit(G("x")), "one metadata row"),
])
def test_malformed_metadata_refuses(parsing, metadata, grammar, remedy):
    """An invalid catalog cannot masquerade as an ordinary grammar mismatch."""
    with parsing._new_space() as space:
        space += lib.parsing
        space.run(metadata)
        with pytest.raises(MettaError, match=remedy):
            space.fn.grammar_is(grammar).one()


@pytest.mark.parametrize("result,error", [
    (S.bad, MettaOperationError), ((), AssertionFailure), (((),), AssertionFailure),
    (((), (), ()), AssertionFailure), (((1, 2), ()), AssertionFailure),
    ((1, ()), MettaOperationError), (((), S.bad), MettaOperationError),
])
def test_parser_result_shape_is_checked(parsing, result, error):
    """A user parsing function must return a pair with an optional contribution."""
    with parsing._new_space() as space:
        space += lib.parsing
        function = S["|->"]((V.input,), S.noeval(result))
        space.add(S.parsing_form(S.bad_result, (), function))
        parser = space.fn.grammar_parser(S.bad_result()).one()
        with pytest.raises(error):
            space.fn.apply_to(parser, ((),)).one()


@pytest.mark.parametrize("grammar", [S.nosuch(), S.cat(S.digits(), S.lit(7)), S.many(),
                                     S.lit((G("x"),)), S.many(S.any(), S.any()), V.grammar,
                                     (V.head, G("x"))])
def test_malformed_grammars_name_the_refusal(parsing, grammar):
    """Wrong kinds and arities are invalid before text consumption starts."""
    assert parsing.fn.grammar_is(grammar) == [False]
    with pytest.raises(MettaError, match="well-formed grammar from grammar-forms"):
        parsing.fn.grammar_parse(grammar, G("")).one()


@pytest.mark.parametrize("grammar", [S.many(S.cat()), S.many1(S.lit(G(""))),
                                     S.sep_by(S.cat(), S.cat())])
def test_nonprogressing_repetition_refuses(parsing, grammar):
    """Nullable repetition has a structural refusal with a consumption remedy."""
    with pytest.raises(MettaError, match="must consume input"):
        parsing.fn.grammar_parse(grammar, G("")).one()


def test_reflection_reconstructs_a_grammar_compiler(parsing):
    """Matching the public equation returns a body usable as an ordinary function."""
    row = parsing.match(S["="](S.grammar_parser(V.grammar), V.body)).one()
    compiler = parsing.eval(S["|->"]((row.grammar,), row.body))[0]
    parser = parsing.fn.apply_to(compiler, (S.any(),)).one()
    assert parsing.fn.apply_to(parser, S.quote(((S["+"](1, 2), S.Empty),))) == [
        ((S["+"](1, 2),), (S.Empty,)),
    ]


def test_callback_ownership_follows_each_caller_space(parsing):
    """The same grammar names the callback defined in its caller's space."""
    for result in (S.left, S.right):
        with parsing._new_space() as space:
            space += lib.parsing
            space.add(S["="](S.local_value(V.value), S.noeval(result)))
            assert space.fn.grammar_parse(S.map(S.local_value, S.any()), G("x")) == [result]
