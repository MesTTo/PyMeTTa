"""Purpose: preserve Python None values through compiled return and yield paths.

Guarantees: a None answer survives calls, bindings, branches and cleanup,
while an exhausted generator has zero answers [tested: test_none_results.py;
commit=WORKTREE].
Owns resources: each scenario closes its MeTTa context and owned spaces.
"""

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Expression, Grounded, MeTTa, S, Space, V


def _explicit_none() -> None:
    return None


def _bare_return() -> None:
    return


def _fallthrough() -> None:
    pass


@pytest.mark.parametrize("function", [_explicit_none, _bare_return, _fallthrough])
def test_none_return_spellings_have_one_typed_answer(function):
    """All three ordinary Python return forms denote the same singleton."""
    with MeTTa() as context:
        compiled = context.self.define(function, name="none-result")
        expression = S["none-result"]()
        assert context.self.eval(expression) == [Grounded(None)]
        assert compiled().one() is None
        assert context.self.eval(S["get-type"](Grounded(None))) == [S.NoneType]
        assert compiled.py() is None


def test_a_void_call_does_not_end_its_callers_bindings():
    """The write happens once and both subsequent Python bindings execute."""
    with MeTTa() as context:
        m = context.self
        target = context.space()

        @m.define
        def record_void(target: Space, value: int) -> None:
            target += S.observed(value)

        @m.define
        def after_void(target: Space):
            result = record_void(target, 7)
            following = 8
            return result, following

        assert after_void(target).one() == Expression([Grounded(None), 8])
        assert target.eval(S.match(target, S.observed(V.value), V.value)) == [7]


@given(st.integers(min_value=-3, max_value=7))
def test_none_returns_preserve_conditional_and_loop_exits(size):
    """A bare return exits its function, including from a lifted loop body."""
    with MeTTa() as context:
        m = context.self

        @m.define  # noqa: RET503 -- implicit fallthrough is the compiler input under test
        def nullable_tail(n: int) -> int | None:
            if n > 0:
                return n

        @m.define
        def nullable_loop(n: int) -> int | None:
            total = 0
            for index in range(n):
                if index == 2:
                    return  # noqa: RET502 -- a bare return inside the lifted loop is the compiler input under test
                total += index
            return total

        assert nullable_tail(size).one() == nullable_tail.py(size)
        assert nullable_loop(size).one() == nullable_loop.py(size)


def test_none_return_runs_finally_and_preserves_the_answer():
    """The singleton return remains live while the cleanup writes its fact."""
    with MeTTa() as context:
        m = context.self
        target = context.space()

        @m.define
        def closed_void(target: Space) -> None:
            try:
                return
            finally:
                target += S.closed()

        assert closed_void(target).one() is None
        assert target.eval(S.match(target, S.closed(), 7)) == [7]


def test_yielded_none_is_an_answer_and_exhaustion_is_not():
    """Equal singleton answers retain bag multiplicity and iteration order."""
    with MeTTa() as context:
        m = context.self

        @m.define
        def none_choices() -> Iterator[None]:
            yield
            yield None

        @m.define
        def no_choices():
            if False:
                yield None

        assert list(none_choices()) == [None, None]
        assert list(no_choices()) == []
        assert list(none_choices.py()) == [None, None]


def test_nullable_annotations_keep_both_result_alternatives():
    """The None branch is a type contract alongside the numeric branch."""
    with MeTTa() as context:
        m = context.self

        @m.define
        def nullable_contract(positive: int) -> int | None:
            if positive:
                return 5
            return None

        assert nullable_contract(1).one() == 5
        assert nullable_contract(0).one() is None
        types = m.eval(S["get-type"](S.nullable_contract))
        assert S["->"](S.Number, S.Number) in types
        assert S["->"](S.Number, S.NoneType) in types

        @m.define
        def wrong_none_contract(value: int) -> None:
            return value

        @m.define
        def checked_none_contract() -> None:
            return wrong_none_contract(5)

        assert m.eval(S.checked_none_contract()) == []


def test_none_literal_is_also_a_default_head_pattern():
    """Function defaults keep their pattern meaning for the singleton value."""
    with MeTTa() as context:
        m = context.self

        @m.define
        def none_pattern(_value=None):
            return "none"

        assert none_pattern(None).one() == "none"
        assert none_pattern.py(None) == "none"
