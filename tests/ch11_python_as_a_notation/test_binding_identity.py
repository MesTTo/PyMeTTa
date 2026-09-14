"""Purpose: preserve Python binding identity through native variable scopes.

Guarantees:
  - ordinary underscore bindings and explicit anonymous patterns have distinct
    behavior [tested: test_python_underscore_bindings_retain_their_values,
    test_native_underscore_patterns_remain_anonymous; commit=WORKTREE]
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import reduce
from typing import TypeVar

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Expression, S, Space, V, convert, equation
from metta._catalog.annotations import annotation_atom_for, type_atom_for
from metta._errors.errors import CompileError


def _parameter(_):
    return _ + _


def _local(value):
    _ = value
    return _  # noqa: RET504 -- exercise an actual local binding


def _rebound(value):
    _ = value
    _ += 9
    return _


def _unpacked(value):
    _, _ = value, value + 1
    return _


def _starred(value):
    first, *_ = (1, value, 3)
    return first + sum(_)


def _lambda(value):
    return (lambda _: _ + 1)(value)  # noqa: PLC3002 -- exercise a computed native lambda


def _lambda_shadow(value):
    _ = 17
    callback = lambda _: _ + 1  # noqa: E731 -- exercise a stored native lambda
    result = callback(value)
    return _, result


def _ordinary_shadow(value):
    item = 17
    callback = lambda item: item + 1  # noqa: E731 -- exercise a stored native lambda
    result = callback(value)
    return item, result


def _comprehension_shadow(value):
    item = 17
    result = [item + value for item in (1, 2, 3)]
    return item, sum(result)


def _container_shadow(value):
    items = [1, 2]
    callback = lambda items: items + 1  # noqa: E731 -- a parameter shadows a proved list
    return sum(items), callback(value)


def _dictionary_shadow(value):
    items = {"x": 9}
    callback = lambda items: items[0]  # noqa: E731 -- a parameter shadows a dict-space
    return items["x"], callback((value,))


def _lambda_rebound(value):
    return (lambda _: ((_ := _ + 1), _))(value)  # noqa: PLC3002 -- exercise the nested scope refusal


def _reduce(value):
    _ = 17
    result = reduce(lambda _, item: _ + item, (1, 2, 3), value)
    return _, result


def _nested(value):
    def inner(_):
        return _ + 2
    return inner(value)


def _lifted(value):
    _ = value
    def inner(amount):
        return _ + amount
    _ += 1
    return inner(2)


def _comprehension(value):
    return [_ + value for _ in (1, 2, 3) if _ > 1]


def _loop_state(value):
    _ = value
    i = 0
    while i < 3:
        _ += i
        i += 1
    return _


def _for_target(value):
    total = value
    for _ in (1, 2, 3):
        total += _
    return total


def _for_state(value):
    _ = value
    for item in (1, 2, 3):
        _ += item
    return _


def _try_state(value):
    _ = value
    try:
        _ += 1
    except ValueError:
        _ = 0
    return _


def _walrus(value):
    return (_ := value), _ + 1


def _wildcard(value):
    _ = value
    match (1, 2):
        case (_, _):
            return _


@pytest.mark.parametrize("function", [
    _parameter, _local, _rebound, _unpacked, _starred, _lambda, _lambda_shadow,
    _nested, _lifted, _comprehension, _loop_state, _for_target, _for_state,
    _try_state, _walrus, _wildcard, _ordinary_shadow, _comprehension_shadow,
    _reduce, _container_shadow, _dictionary_shadow,
])
def test_python_underscore_bindings_retain_their_values(scratch_space, function):
    """Source binders preserve Python results across ordinary compiler scopes."""
    compiled = scratch_space.define(function)

    @given(st.integers(min_value=-20, max_value=20))
    def check(value):
        assert list(compiled(value)) == [convert.project(function(value)).atom]

    check()


def test_nested_walrus_binding_keeps_its_scope_refusal(scratch_space):
    """Renaming native binders does not claim support for nested walrus scopes."""
    with pytest.raises(CompileError, match="a walrus inside a nested scope"):
        scratch_space.define(_lambda_rebound)


def test_generator_underscore_bindings_cross_branches_and_iterations(scratch_space):
    """A helper parameter and a yielded loop target carry their source values."""
    @scratch_space.define
    def stream(value):
        _ = value
        if value > 0:
            yield _
            _ += 1
        else:
            _ = 9
        yield _
        for _ in (2, 3):
            yield _

    for value in (-1, 0, 1, 4):
        assert list(stream(value)) == list(stream.py(value))


def test_native_underscore_patterns_remain_anonymous(scratch_space):
    """Two explicit native wildcards impose no equality on their positions."""
    m = scratch_space
    m.add(S["="](S["anonymous-pair"](V._, V._), S.Accepted))
    assert m.eval(S["anonymous-pair"](1, 2)) == [S.Accepted]

    @m.rules
    def repeated(_):
        yield equation(S["named-pair"](_, _)).to(_)

    assert m.eval(S["named-pair"](3, 3)) == [3]
    assert m.eval(S["named-pair"](1, 2)) == []


def test_underscore_type_parameters_retain_shared_constraints(scratch_space):
    """A type parameter links occurrences; two native wildcards do not."""
    _ = TypeVar("_")
    for project in (annotation_atom_for, type_atom_for):
        pair = Expression([project(_), project(_)])
        assert scratch_space.eval(S.unify(pair, (S.Number, S.Number), S.Yes, S.No)) == [S.Yes]
        assert scratch_space.eval(S.unify(pair, (S.Number, S.String), S.Yes, S.No)) == [S.No]


def test_underscore_callable_parameters_keep_python_keyword_labels(scratch_space):
    """The native binder is hygienic while the public parameter stays underscore."""
    compiled = scratch_space.define(_parameter)
    value = convert.build(convert.project(compiled).atom, Callable[[int], int], space=scratch_space)
    assert value(_=7) == 14


def test_stacked_underscore_parameters_retain_order_and_binding(scratch_space):
    """Case materialization renames a clause's head and body together."""
    @scratch_space.define(name="underscore-clauses")
    def choose(_=0):
        return 11

    assert list(choose(0)) == [11]

    @scratch_space.define(name="underscore-clauses")
    def choose(_):
        return _ + 2

    for value in (0, 1, 3):
        assert list(choose(value)) == [choose.py(value)]
        assert scratch_space.eval(S["underscore-clauses"](value)) == [choose.py(value)]


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
@pytest.mark.parametrize("generated", [True, False])
def test_class_underscore_fields_receivers_and_packed_parameters(scratch_space, grain, generated):
    """Class construction and every method argument use the same binding law."""
    m = scratch_space

    class UnderscoreReceiver(Space if grain == "prototype" else object):
        _: int

        if not generated:
            def __init__(self, _: int):
                object.__setattr__(self, "_", _)

        def read(_):  # noqa: N805 -- the receiver spelling is the regression
            return _._

        def positional(self, *_):
            return self._ + sum(_)

        def keyword(self, **_):
            return self._ + _["bonus"]

    cls = dataclass(frozen=grain == "value")(UnderscoreReceiver) if grain != "prototype" else UnderscoreReceiver
    m.define(cls)
    value = cls(_=7)
    assert value._ == value.read() == value.read.py() == 7
    assert value.positional(2, 3) == value.positional.py(2, 3) == 12
    assert value.keyword(bonus=4) == value.keyword.py(bonus=4) == 11
    assert all("_host-" not in getattr(value, name).source() for name in ("read", "positional", "keyword"))
