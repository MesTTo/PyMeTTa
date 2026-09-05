"""Purpose: preserve case duals and tail calls through compiled conditionals."""

import pytest

from metta import S


def test_compiled_nested_cases_negate_every_selected_arm(metta):
    """A wildcard stays a wildcard when the dual reads nested case rows."""
    m = metta._new_space()

    @m.define
    def selected(key):
        match key:
            case 1:
                return True
            case remaining:
                match remaining:
                    case 2:
                        return False
                    case 3:
                        return True
                    case _:
                        return False

    for key, expected in ((1, False), (2, True), (3, False), (4, True)):
        assert m.fn.not_provable(S.selected(key)) == [expected]


def test_compiled_case_without_matching_arm_is_not_provable(metta):
    """No matching arm produces no answer and therefore has a true dual."""
    m = metta._new_space()

    @m.define
    def band(key):
        match key:
            case 90:
                return True
            case 40:
                return False

    assert band(55) == []
    assert m.fn.not_provable(S.band(90)) == [False]
    assert m.fn.not_provable(S.band(40)) == [True]
    assert m.fn.not_provable(S.band(55)) == [True]


def test_compiled_case_capture_is_bound_before_its_body_is_negated(metta):
    """A captured field is supplied by the selected pattern's key."""
    m = metta._new_space()

    @m.define
    def tagged(key):
        match key:
            case (S.Tag, payload):
                return S.eq(payload, 2)
            case _:
                return False

    assert m.fn.not_provable(S.tagged(S.Tag(2))) == [False]
    assert m.fn.not_provable(S.tagged(S.Tag(3))) == [True]
    assert m.fn.not_provable(S.tagged(S.Other)) == [True]


@pytest.mark.parametrize("spelling", ("expression", "statement", "nested"))
def test_compiled_conditional_tail_calls_fit_a_fixed_stack(metta, spelling):
    """Two hundred thousand recursive branches fit an eight-megabyte stack."""
    m = metta._new_space()

    @m.define
    def expression(n: int, acc: int):
        return expression(n - 1, acc + 1) if n > 0 else acc

    @m.define
    def statement(n: int, acc: int):
        if n > 0:
            next_n = n - 1
            next_acc = acc + 1
            return statement(next_n, next_acc)
        return acc

    @m.define
    def nested(n: int, acc: int):
        if n > 0:
            return nested(n - 1, acc + 1) if n > 1 else nested(0, acc + 1)
        return acc

    chosen = {"expression": expression, "statement": statement, "nested": nested}[spelling]
    with m.limits(stack=8_000_000):
        assert chosen(200_000, 0) == [200_000]
