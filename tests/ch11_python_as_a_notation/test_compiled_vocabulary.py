"""Purpose: exercise structural bindings, answer collection, and case continuations.

Owns resources:
  - tests unregister their process-wide source, operand and accept callbacks in
    finally blocks; dropping scratch_space releases stored equations, not ops
    [tested: test_as_pattern_or_retry_commits_only_the_complete_selected_alternative
    followed by test_public_space_add_observes_every_pre_add_verdict;
    commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67].
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Expression, Grounded, S, V, Variable, match, py, superpose
from metta._errors.errors import CompileError


@pytest.fixture
def m(scratch_space):
    """Use an isolated definition space for each compiler scenario."""
    return scratch_space


def test_list_collects_engine_answers_and_preserves_host_lists(m):
    """A known answer stream collapses, while a host iterable stays a host list."""
    @m.define
    def alternatives():
        yield 1
        yield 2
        yield 2

    @m.define
    def collect():
        return list(alternatives())

    @m.define
    def empty_collection():
        return list(superpose())

    @m.define
    def host_collection(n):
        return list(range(n))

    @m.define
    def explicit_host(n):
        return py(list(range(n)))

    assert "(collapse (alternatives))" in collect.source()
    assert list(collect()) == [Expression([1, 2, 2])]
    assert list(empty_collection()) == [Expression([])]
    for function in (host_collection, explicit_host):
        result = list(function(3))
        assert len(result) == 1
        assert isinstance(result[0], Grounded)
        assert result[0].value == [0, 1, 2]


def test_list_collects_matching_answers_without_splicing_their_terms(m):
    """Collection retains each matched expression as one answer."""
    m.add(S.edge(S.a, S.b), S.edge(S.a, S.c))

    @m.define
    def collect():
        return list(match(S.edge(V.x, V.y), (V.x, V.y)))

    assert list(collect()) == [Expression([S.a(S.b), S.a(S.c)])]


def test_structural_assignments_share_pattern_binding_and_ssa(m):
    """Nested unpacking binds once, and repeated targets retain the last value."""
    @m.define
    def unpack(value):
        left, (middle, right) = value
        left, right = right, left
        return left, middle, right

    @m.define
    def repeated(value):
        item, item = value
        return item

    assert "(let* ((($left ($middle $right)) $value))" in unpack.source()
    assert list(unpack((1, (2, 3)))) == [Expression([3, 2, 1])]
    assert list(unpack((1, 2))) == []
    assert list(repeated((1, 2))) == [2]

    @given(st.tuples(st.integers(-100, 100), st.integers(-100, 100), st.integers(-100, 100)))
    def check(values):
        left, middle, right = values
        assert list(unpack((left, (middle, right)))) == [Expression([right, middle, left])]

    check()


def test_structural_assignment_preserves_literal_species(m):
    """Unpacking does not erase list concatenation or native numeric proofs."""
    @m.define
    def combine():
        xs, n = [1, 2], 3
        tail = [n]
        return xs + tail

    @m.define
    def add():
        left, right = 3, 4
        return left + right

    result = list(combine())
    assert result == [Expression([1, 2, 3])]
    assert list(add()) == [7]
    assert "(+ $left $right)" in add.source()


def test_structural_assignment_checks_errors_before_matching(m):
    """An error from the source reaches its handler before destructuring."""
    @m.define
    def fail():
        message = "failed"
        raise ValueError(message)

    @m.define
    def catch_source():
        try:
            left, right = fail()
        except ValueError:
            return S.Caught
        else:
            return left, right

    assert list(catch_source()) == [S.Caught]


def test_structural_assignment_preserves_dictionary_and_star_bindings(m):
    """A destructured dictionary keeps its space protocol and a star keeps its run."""
    @m.define
    def lookup():
        mapping, marker = {1: 9}, 0
        return mapping[1], marker

    @m.define
    def unpack(value):
        head, *tail = value
        return head, tail

    assert list(lookup()) == [Expression([9, 0])]
    assert "(get-value $mapping 1)" in lookup.source()
    assert list(unpack((1, 2, 3))) == [Expression([1, Expression([2, 3])])]
    assert list(unpack((1,))) == [Expression([1, Expression([])])]
    assert list(unpack(())) == []


def test_generator_match_preserves_captures_guards_and_continuations(m):
    """The selected arm's bindings flow into its yields and later statements."""
    @m.define
    def choose(value):
        match value:
            case (S.Left, item) | (S.Right, item) if item > 0:
                yield item
                item = item + 1
            case _:
                item = 0
        yield item

    assert list(choose(S.Left(3))) == [3, 4]
    assert list(choose(S.Right(4))) == [4, 5]
    assert list(choose(S.Left(-1))) == [0]
    assert list(choose(S.Other)) == [0]


def test_generator_match_handles_nested_matches_and_unmatched_fallthrough(m):
    """Unmatched subjects continue once, and nested branches retain their scope."""
    @m.define
    def choose(value):
        match value:
            case (S.Box, item):
                match item:
                    case 1:
                        yield 10
                    case _:
                        yield 20
            case S.Skip:
                pass
        yield 30

    assert list(choose(S.Box(1))) == [10, 30]
    assert list(choose(S.Box(2))) == [20, 30]
    assert list(choose(S.Skip)) == [30]
    assert list(choose(S.Other)) == [30]


def test_generator_match_raise_closes_only_its_selected_branch(m):
    """A raising arm delivers its earlier yields but never executes the tail."""
    @m.define
    def choose(value):
        match value:
            case 1:
                yield 10
                message = "stopped"
                raise ValueError(message)
            case _:
                yield 20
        yield 30

    assert list(choose(2)) == [20, 30]
    answers = list(choose(1))
    assert answers[0] == 10
    assert len(answers) == 2
    assert answers[1].head == S.Error
    assert "stopped" in str(answers[1])


def test_empty_match_subject_selects_only_the_empty_branch(m):
    """No answer and an unmatched answer have distinct control paths."""
    @m.define
    def absent():
        match superpose():
            case 1:
                return 2
            case S.Empty:
                return 42

    @m.define
    def unmatched():
        match 9:
            case 1:
                return 2
            case S.Empty:
                return 42

    @m.define
    def generator():
        match superpose():
            case S.Empty:
                yield 42
        yield 43

    assert list(absent()) == [42]
    assert list(unmatched()) == []
    assert list(generator()) == [42, 43]


def test_empty_match_subject_is_evaluated_once_and_keeps_all_answers(m):
    """The case scrutinee is never rerun to decide whether it was empty."""
    calls = []

    @m.op(effect="oracleIO")
    def source(n):
        calls.append(n)
        yield from range(n)

    try:
        @m.define
        def choose(n):
            match source(n):
                case S.Empty:
                    return S.Missing
                case value:
                    return value

        assert list(choose(0)) == [S.Missing]
        assert list(choose(3)) == [0, 1, 2]
        assert calls == [0, 3]
    finally:
        m.unregister_op("source")



def test_guarded_empty_generator_arm_falls_through_once(m):
    """A rejected Empty guard proceeds to later Empty arms or the continuation."""
    @m.define
    def choose():
        match superpose():
            case S.Empty if False:
                yield 1
        yield 3

    assert list(choose()) == [3]


def test_existing_conjunction_match_and_runtime_cases(m):
    """Conjunction and computed branch lists already have structural spellings."""
    m.add(S.edge(S.a, S.b), S.edge(S.b, S.c))

    @m.define
    def joined():
        return match(S[","](S.edge(V.x, V.y), S.edge(V.y, V.z)), (V.x, V.z))

    @m.define
    def choose(value, arms):
        return S.case(value, arms)

    @m.define
    def absent(arms):
        return S.case(superpose(), arms)

    assert list(joined()) == [S.a(S.c)]
    assert list(choose(2, ((1, S.one), (2, S.two)))) == [S.two]
    assert list(absent(((S.Empty, S.none),))) == [S.none]


def test_type_uses_engine_metatypes_with_an_explicit_host_boundary(m):
    """An unshadowed type query reads the engine; py(type(...)) reads Python."""
    @m.define
    def metatype(value):
        return type(value)

    @m.define
    def host_type(value):
        return py(type(value))

    for value, expected in ((S.a, S.Symbol), (S.a(1), S.Expression), (4, S.Grounded)):
        assert list(metatype(value)) == [expected]
    assert "(get-metatype $value)" in metatype.source()
    host_answers = list(host_type(4))
    assert host_answers[0].value is int


def test_destructuring_refusal_names_the_supported_remedy(m):
    """An attribute target is still refused with the structural binding remedy."""
    def bad(value):
        value.field, item = 1, 2
        return item

    with pytest.raises(CompileError, match=r"plain names.*tuple.*list"):
        m.define(bad)


def test_type_evaluates_computed_operands_before_querying_their_metatype(m):
    """The idiomatic query classifies its value, including explicit host values."""
    calls = []

    @m.op(effect="oracleIO")
    def operand():
        calls.append(1)
        return 3

    try:
        @m.define
        def computed():
            return type(1 + 2), type(py([1, 2])), type(operand())

        assert list(computed()) == [Expression([S.Grounded, S.Grounded, S.Grounded])]
        assert calls == [1]
    finally:
        m.unregister_op("operand")



def test_starred_assignment_preserves_prefix_and_suffix_value_proofs(m):
    """A variable-length middle does not hide the known fields on either side."""
    @m.define
    def prefix():
        mapping, *rest = {1: 9}, 0, 0
        return mapping[1], rest

    @m.define
    def suffix():
        *rest, mapping = 0, 0, {1: 9}
        return mapping[1], rest

    @m.define
    def empty_middle():
        first, *middle, last = 1, 3
        return first + last, middle

    assert list(prefix()) == [Expression([9, Expression([0, 0])])]
    assert list(suffix()) == [Expression([9, Expression([0, 0])])]
    assert list(empty_middle()) == [Expression([4, Expression([])])]
    assert "(+ $first $last)" in empty_middle.source()


def test_structural_global_targets_refuse_with_an_explicit_write_remedy(m):
    """A global target must never silently turn into a local capture."""
    def global_unpack():
        global vocabulary_global
        vocabulary_global, local = 1, 2
        return local

    with pytest.raises(CompileError, match=r"global.*local.*assign"):
        m.define(global_unpack)


def test_list_refuses_ambiguous_calls_and_names_both_value_doors(m):
    """A deterministic returned sequence is distinct from the callee's answers."""
    @m.define
    def data():
        return 1, 2

    def ambiguous():
        return list(data())

    with pytest.raises(CompileError, match=r"collapse.*bind the returned data"):
        m.define(ambiguous)

    @m.define
    def returned_data():
        value = data()
        return list(value)

    assert next(iter(returned_data())).value == [1, 2]


def test_simple_match_stores_the_direct_ordered_case_table(m):
    """A literal table keeps the engine form and its direct dispatch cost."""
    @m.define
    def absent():
        match S.empty():
            case 1:
                return 2
            case S.Empty:
                return 42

    assert absent.source() == "(= (absent) (case (empty) ((1 2) (Empty 42))))"
    assert list(absent()) == [42]


def test_nested_as_patterns_capture_their_own_subterm_and_retry_shape_failures(m):
    """An as-capture aliases the matched subterm before its guard sees it."""
    @m.define
    def selected(value):
        match value:
            case ((1, item) as pair, marker) if pair[0] == 1:
                yield pair, item, marker
            case ((2, item) as pair, marker) | ((3, item) as pair, marker):
                yield pair, item, marker
            case _:
                yield S.Miss

    assert list(selected(((1, 9), 7))) == [Expression([Expression([1, 9]), 9, 7])]
    assert list(selected(((2, 8), 6))) == [Expression([Expression([2, 8]), 8, 6])]
    assert list(selected(((3, 5), 4))) == [Expression([Expression([3, 5]), 5, 4])]
    assert list(selected(((4, 9), 7))) == [S.Miss]


def test_failed_as_pattern_rolls_back_all_source_variable_bindings(m):
    """A failed subpattern cannot retain a sibling's tentative constraints."""
    @m.define
    def selected(value):
        match value:
            case ((1, item) as pair, 2):
                return pair, item
            case _:
                return value

    (answer,) = selected(((3, 0), V.sibling))
    assert answer[0] == Expression([3, 0])
    assert isinstance(answer[1], Variable)
    (shared,) = selected(((1, V.shared), 2))
    assert isinstance(shared[1], Variable)
    assert shared[0][1] == shared[1]


def test_as_pattern_or_retry_commits_only_the_complete_selected_alternative(m):
    """The next alternative receives the original subject and binds its own alias."""
    calls = []

    @m.op(effect="oracleIO")
    def accept(value):
        calls.append(value)
        return True

    try:
        @m.define
        def selected(value):
            match value:
                case ((1, item) as pair, 2) | ((3, item) as pair, 3) if accept(item):
                    yield pair, item, value
                case _:
                    yield S.Miss

        assert list(selected(((3, 9), V.sibling))) == [
            Expression([Expression([3, 9]), 9, Expression([Expression([3, 9]), 3])])
        ]
        assert calls == [9]
    finally:
        m.unregister_op("accept")



def test_nested_star_aliases_share_one_pattern_decision(m):
    """Nested aliases retain their subterms and failed stars undo sibling bindings."""
    @m.define
    def selected(value):
        match value:
            case (((1, *rest) as inner, 2) as outer, 3):
                return inner, outer, rest
            case _:
                return value

    inner = Expression([1, 4, 5])
    outer = Expression([inner, 2])
    assert list(selected((outer, 3))) == [Expression([inner, outer, Expression([4, 5])])]
    (answer,) = selected((((4, 5), V.first), V.second))
    assert answer[0][0] == Expression([4, 5])
    assert isinstance(answer[0][1], Variable)
    assert isinstance(answer[1], Variable)
    assert answer[0][1] != answer[1]


def test_as_alias_preserves_a_held_evaluable_subterm(m):
    """Packing alias constraints must not evaluate a subterm supplied as data."""
    @m.define
    def selected(value):
        match value:
            case (S.Box, item as alias):
                return item, alias
            case _:
                return S.Miss

    term = S.add(1, 2)
    assert m.eval(S.selected(S.noeval(S.Box(term)))) == [Expression([term, term])]


def test_empty_alias_binds_the_absence_marker(m):
    """An absence branch has an Empty alias even though no subject value arrived."""
    @m.define
    def selected():
        match superpose():
            case S.Empty as absent:
                return S.Missing, absent

    assert list(selected()) == [S.Missing(S.Empty)]
