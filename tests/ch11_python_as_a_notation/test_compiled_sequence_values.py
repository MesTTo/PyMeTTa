"""Purpose: retain evaluated sequence elements as native values.

Guarantees:
  - a computed callable head remains an element and observes native source
    edits on the next construction [tested:
    test_computed_sequence_heads_remain_values_after_native_rewriting;
    commit=WORKTREE]
"""

import pytest

from metta import Expression, MeTTa, S


@pytest.mark.parametrize("shape", ("tuple", "list"))
def test_computed_sequence_heads_remain_values_after_native_rewriting(shape):
    """Building a sequence does not apply the function its first item returns."""
    with MeTTa() as context:
        space = context.self

        @space.define
        def returned_head():
            return S["+"]

        def tuple_value(value):
            return returned_head(), value, 1

        def list_value(value):
            return [returned_head(), value, 1]

        selected = space.define(tuple_value if shape == "tuple" else list_value)
        assert list(selected(2)) == [Expression([S["+"], 2, 1])]
        original = S["="](S["returned-head"](), S["+"])
        assert original in space
        space.remove(original)
        space.add(S["="](S["returned-head"](), S["*"]))
        assert list(selected(2)) == [Expression([S["*"], 2, 1])]


@pytest.mark.parametrize("shape", ("tuple", "list"))
def test_sequence_elements_run_once_in_source_order(shape):
    """Each computed element is evaluated before its value enters the sequence."""
    with MeTTa() as context:
        space = context.self
        seen = []

        @space.op(effect="writesState")
        def element(value: int) -> int:
            seen.append(value)
            return value

        def tuple_value():
            return element(1), element(2), element(3)

        def list_value():
            return [element(1), element(2), element(3)]

        selected = space.define(tuple_value if shape == "tuple" else list_value)
        assert list(selected()) == [Expression([1, 2, 3])]
        assert seen == [1, 2, 3]
