"""Purpose: compare literal MeTTa rewriting with independent Python term models.

Guarantees: generated trees exercise root precedence, duplicate alternatives,
numeric key kinds, shared variables and literal syntax through the public
library [tested: test_reflect_terms.py; commit=505ce25b9384e782afa26f621527d4b1fd695924].
"""

from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Expression, S, V, Variable, lib
from metta._errors.errors import MettaError


@pytest.fixture(scope="module")
def reflect(metta):
    """Keep the library declarations in one owned space."""
    with metta._new_space() as space:
        space += lib.reflect
        yield space


LEAF = st.sampled_from([S.a, S.b, S["+"], S.Error, S.Empty, S.empty, V.x, V.y, 1, 1.0, "text"])
TERM = st.recursive(LEAF, lambda inner: st.lists(inner, max_size=3).map(tuple), max_leaves=5)


def identical(left, right):
    """Compare written structure, keeping integer and float keys distinct."""
    if type(left) is not type(right):
        return False
    if isinstance(left, tuple):
        return len(left) == len(right) and all(
            identical(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def replaced(term, rules):
    """A root match is final; unmatched expressions branch over child products."""
    hits = [value for key, value in rules if identical(term, key)]
    if hits:
        return hits
    if isinstance(term, tuple):
        return list(product(*(replaced(child, rules) for child in term)))
    return [term]


def written_variables(term):
    """Inspect leaves in order and retain the first occurrence of each variable."""
    variables = []
    pending = [term]
    while pending:
        item = pending.pop()
        if isinstance(item, (tuple, Expression)):
            pending.extend(reversed(item))
        elif isinstance(item, Variable) and item not in variables:
            variables.append(item)
    return tuple(variables)


def assert_replacements(reflect, term, rules, expected):
    """Carry the input variables beside each result to check sharing after decoding."""
    context = written_variables((term, tuple(rules)))
    result = V.result
    # An eager lambda argument propagates Error before its body can package it.
    # Binding the produced value keeps that literal error beside its context.
    actual = reflect.eval(S.let(result, S.atom_replace(term, tuple(rules)), S.noeval((result, context))))
    assert len(actual) == len(expected)
    assert all(
        item.alpha_eq(Expression((value, context)))
        for item, value in zip(actual, expected, strict=True)
    ), (actual, expected, context)


@settings(max_examples=80, deadline=None)
@given(TERM, st.lists(st.tuples(TERM, TERM), max_size=3))
def test_generated_replacement_bags(reflect, term, rules):
    """Compare every answer in order, including duplicates and fresh variables."""
    assert_replacements(reflect, term, rules, replaced(term, rules))
    assert reflect.eval(S["=="](S.atom_variables(term), S.quote(written_variables(term)))) == [True]


@settings(max_examples=60, deadline=None)
@given(TERM, TERM, TERM)
def test_root_precedence_and_duplicate_rows(reflect, term, first, second):
    """Even an expression root is replaced before its children are considered."""
    assert_replacements(reflect, term, ((term, first), (term, second)), [first, second])
    assert_replacements(reflect, term, ((term, first), (term, first)), [first, first])


@pytest.mark.parametrize("rules", [S.invalid, (S.invalid,), ((S.a,),), ((S.a, S.b, S.c),), (V.row,), V.rows])
def test_malformed_relations_are_refused(reflect, rules):
    """The complete relation is checked even when an early root could match."""
    with pytest.raises(MettaError):
        reflect.fn.atom_replace(S.a, rules).one()


def test_literal_code_and_shared_variables(reflect):
    """Held parameters inspect executable syntax and retain variable relations."""
    term = S["+"](V.x, S.Error(S.data, V.y))
    assert_replacements(reflect, term, ((V.x, S["+"](1, 2)),), [
        S["+"](S["+"](1, 2), S.Error(S.data, V.y)),
    ])
    assert reflect.eval(S["=="](S.atom_variables(term), S.quote((V.x, V.y)))) == [True]
    assert_replacements(reflect, (S.a, S.a), ((S.a, (V.x, V.x)),), [
        ((V.x, V.x), (V.x, V.x)),
    ])
    assert_replacements(reflect, S.p(V.x), ((S.p(V.y), S.wrong),), [S.p(V.x)])


def test_empty_symbol_is_a_literal_rewrite(reflect):
    """Only an absent answer declines; no symbol is reserved as a result marker."""
    assert reflect.fn.strategy_apply(S.id, S.Empty) == [S.Empty]
    assert_replacements(reflect, (S.a, S.a), ((S.a, S.Empty), (S.a, S.b)), [
        (S.Empty, S.Empty), (S.Empty, S.b), (S.b, S.Empty), (S.b, S.b),
    ])


@pytest.mark.parametrize("count", [0, 1, 2, 3, 12, 24])
def test_variadic_plans_and_numeric_repeat(reflect, count):
    """Numeric repetition and rewrite composition share a space without overlap."""
    term = S["+"](1, 2)
    assert reflect.fn.seq(*([S.id] * count), term) == [term]
    assert reflect.fn.strategy_apply(S.seq(*([S.id] * count)), term) == [term]
    assert reflect.fn.repeat(count, S.noeval(S.token)) == [S.token] * count


def test_lambda_and_partial_application_operands_stay_literal(reflect):
    """A callable expression becomes a function while its subject stays data."""
    reflect.run("(= (reflect-prefix $tag $value) (noeval ($tag $value)))")
    term = S["+"](1, 2)
    assert reflect.fn.strategy_apply(S.reflect_prefix(S.marked), term) == [S.marked(term)]
    callback = S["|->"]((V.node,), S.noeval(S.marked(V.node)))
    assert reflect.fn.strategy_apply(callback, term) == [S.marked(term)]
    assert reflect.fn.all(callback, (term, S.Error(S.data, S.code))) == [
        (S.marked(term), S.marked(S.Error(S.data, S.code))),
    ]


def test_reconstructed_inspection_equation(reflect):
    """The library's source relation supplies a callable inspection recipe."""
    row = reflect.match(S["="](S.atom_variables(V.term), V.body)).one()
    inspect = reflect.eval(S["|->"]((row.term,), row.body))[0]
    assert reflect.eval(S["=="]((inspect, S.quote((V.x, V.y, V.x))), S.quote((V.x, V.y)))) == [True]
