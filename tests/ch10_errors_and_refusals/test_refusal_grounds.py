"""Purpose: pin structured grounds and remedies on semantic refusals.

Guarantees:
  - atom/plain ordering refuses in both operand directions with Python's rich
    comparison ground, while atom/atom and grounded/plain ordering remain
    lawful [tested: extensions/python/tests/ch10_errors_and_refusals/test_refusal_grounds.py; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - comparison-term truthiness names Python 6.10 and the explicit conjunction
    remedy required by GG5-019 [tested:
    test_comparison_truthiness_names_python_6_10_and_the_conjunction_remedy;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - compiler refusals carry their Python-reference ground as data without
    rewriting the sibling-owned unknown-callee message [tested:
    test_compile_refusals_derive_a_python_reference_ground; commit=acb40f1912f131ae088083d1af29b4b283019bea]
"""

from __future__ import annotations

import pytest

from metta import G, S, V
from metta.errors import CompileError


@pytest.fixture()
def m(metta):
    """Give compiler-refusal scenarios an isolated destination."""
    with metta._new_space() as space:
        yield space


def _assert_python_ground(error: BaseException, section: str) -> None:
    ground = error.ground
    assert ground.kind == "python-reference"
    assert f"Python Language Reference section {section}" in ground.citation


@pytest.mark.parametrize(
    "comparison",
    (
        lambda: S.atom < 1,
        lambda: 1 < S.atom,
    ),
)
def test_atom_plain_order_refuses_in_both_directions_with_its_python_ground(
    comparison,
):
    """P11 and P12 refuse at Python's unsupported-rich-comparison boundary."""
    with pytest.raises(TypeError) as caught:
        comparison()

    _assert_python_ground(caught.value, "3.3.1")
    assert "unwrap a grounded primitive with .value" in str(caught.value)


def test_atom_and_grounded_order_controls_remain_allowed():
    """The ground does not broaden the refusal beyond unlike representations."""
    assert isinstance(S.a < S.b, bool)
    assert G(1) < 2


def test_comparison_truthiness_names_python_6_10_and_the_conjunction_remedy():
    """GG5-019's reference, failure mechanism, and exact remedy stay visible."""
    with pytest.raises(TypeError) as caught:
        bool(S.le(1, V.x))

    message = str(caught.value)
    assert "Python Language Reference section 6.10" in message
    assert "a chained comparison uses truthiness between its terms" in message
    assert "S.le(1, V.x) & S.le(V.x, 10)" in message
    assert "or use a named predicate" in message
    _assert_python_ground(caught.value, "6.10")


def test_an_ordinary_expression_remains_truthy():
    """Only comparison and Boolean terms own the truthiness refusal."""
    assert bool(S.Record(S.value)) is True


def test_compile_refusals_derive_a_python_reference_ground(m):
    """The central constructor grounds both unknown calls and arithmetic fences."""
    with pytest.raises(CompileError) as unknown:
        @m.define(name="refusal-ground-unknown")
        def unknown_call(value):
            return unregistered_host_call(value)  # noqa: F821 -- refused scenario

    with pytest.raises(CompileError) as floor:
        @m.define(name="refusal-ground-floor")
        def floor_division(left, right):
            return left // right

    _assert_python_ground(unknown.value, "6")
    _assert_python_ground(floor.value, "6.7")
    assert "unregistered_host_call" in str(unknown.value)
    assert "floor_math(a / b)" in str(floor.value)
