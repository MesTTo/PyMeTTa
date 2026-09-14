"""Purpose: preserve literal head parameters as values inside compiled bodies.

Guarantees:
  - matched literals remain readable across local scopes and each generator
    equation [tested: test_literal_head_values_reach_compiled_bodies;
    test_each_generator_equation_binds_its_literal_head; commit=WORKTREE]
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import S


def _number(value: int = 3):
    return value + 4


def _none(value=None):
    return value


def _boolean(value=True):  # noqa: FBT002 -- exercise a boolean literal head
    return value


def _text(value="held"):
    return value


def _underscore(_=3):
    return _ + 4


def _rebound(value: int = 3):
    value += 4
    return value


def _loop(value: int = 3):
    total = 0
    for offset in range(value):
        total += offset
    return total


def _nested(value: int = 3):
    def inner(offset):
        return value + offset

    return inner(4)


def _anonymous(value: int = 3):
    return (lambda offset: value + offset)(4)  # noqa: PLC3002 -- native capture


def _sequence(value: int = 3):
    yield value
    yield value + 1


def _offset(delta: int, value: int = 3):
    return value + delta


def _unused(value=3):  # noqa: ARG001 -- the parameter constrains the head
    return 7


@pytest.mark.parametrize(
    ("source", "argument"),
    [(_number, 3), (_none, None), (_boolean, True), (_text, "held"),
     (_underscore, 3), (_rebound, 3), (_loop, 3), (_nested, 3), (_anonymous, 3)],
)
def test_literal_head_values_reach_compiled_bodies(scratch_space, source, argument):
    """The equation head constrains the input while its body can read it."""
    compiled = scratch_space.define(source, name="literal-body")
    assert compiled(argument).one() == compiled.py(argument)
    assert scratch_space.fn["literal-body"].equations[0].args[0] == S["literal-body"](argument)


def test_each_generator_equation_binds_its_literal_head(scratch_space):
    """Independent yield equations each receive the matched parameter value."""
    compiled = scratch_space.define(_sequence, name="literal-sequence")
    assert list(compiled(3)) == list(compiled.py(3)) == [3, 4]
    assert len(scratch_space.fn["literal-sequence"].equations) == 2


def test_literal_head_binding_preserves_other_parameter_values(scratch_space):
    """Binding the matched literal never captures another supplied parameter."""
    compiled = scratch_space.define(_offset, name="literal-offset")

    @given(delta=st.integers())
    def compare(delta):
        assert compiled(delta, 3).one() == compiled.py(delta, 3) == delta + 3

    compare()


def test_unused_literal_head_does_not_add_body_bindings(scratch_space):
    """Unused patterns keep their literal head and unchanged body."""
    compiled = scratch_space.define(_unused, name="literal-unused")
    assert compiled.source() == "(= (literal-unused 3) 7)"
    assert compiled(3).one() == 7
    with pytest.raises(LookupError, match="no clause"):
        compiled.py(4)
