"""Purpose: pin the signed-i64 boundary between Number and BigInt, the
declared-type compatibility rule, exact arithmetic, and integer equality.
Guarantees:
  - every integer literal and result has one numeric type at the boundary
    [tested test_bigint_and_number_type_the_numeric_tower,
    test_integer_type_follows_the_signed_i64_boundary]
  - a Number parameter admits BigInt while a BigInt parameter stays narrow
    [tested test_number_parameters_accept_bigint_without_retyping_number]
  - integer equality remains exact when its operands have different numeric
    types [tested test_mixed_bigint_number_equality_uses_exact_values]
  - Janus and the tagged n form carry BigInt values in both directions
    without changing a digit [tested test_janus_carries_bigint_losslessly]
Open Obligations:
  To Do: Re-verify these rules when LeaTTa adds its announced BigInt type.
  Hacks: None
  Future Enhancements: None
"""

from typing import get_args

from hypothesis import given, settings
from hypothesis import strategies as st

from petta import parse
from petta.vocabularies import NUMERIC_TYPE, NumericType

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


def _answers(metta, form: str) -> list[str]:
    return [str(atom) for group in metta.run(form) for atom in group]


def test_bigint_and_number_type_the_numeric_tower(metta):
    assert _answers(metta, f"!(get-type {I64_MIN})") == ["Number"]
    assert _answers(metta, f"!(get-type {I64_MAX})") == ["Number"]
    assert _answers(metta, f"!(get-type {I64_MIN - 1})") == ["BigInt"]
    assert _answers(metta, f"!(get-type {I64_MAX + 1})") == ["BigInt"]
    assert _answers(metta, "!(get-type 1.0)") == ["Number"]

    assert _answers(
        metta, f"!(let $value (+ {I64_MAX} 1) (get-type $value))"
    ) == ["BigInt"]
    assert _answers(
        metta, f"!(let $value (- {I64_MAX + 1} 1) (get-type $value))"
    ) == ["Number"]

    wide = 4_611_686_018_427_387_904 * 4
    assert metta.run("!(* 4611686018427387904 4)") == [[wide]]
    assert _answers(
        metta, "!(let $value (* 4611686018427387904 4) (get-type $value))"
    ) == ["BigInt"]


@settings(max_examples=50)
@given(st.integers(min_value=-(2**256), max_value=2**256))
def test_integer_type_follows_the_signed_i64_boundary(metta, value):
    expected = "Number" if I64_MIN <= value <= I64_MAX else "BigInt"
    assert _answers(metta, f"!(get-type {value})") == [expected]


def test_number_parameters_accept_bigint_without_retyping_number(metta):
    for form in (
        "(: p145-number (-> Number Atom))",
        "(= (p145-number $value) (number-accepted $value))",
        "(: p145-bigint (-> BigInt Atom))",
        "(= (p145-bigint $value) (bigint-accepted $value))",
        "(: p145-declared-bigint BigInt)",
    ):
        metta.run(form)

    wide = I64_MAX + 1
    assert metta.run(f"!(p145-number {wide})") == [
        [parse(f"(number-accepted {wide})")]
    ]
    assert metta.run(f"!(p145-bigint {wide})") == [
        [parse(f"(bigint-accepted {wide})")]
    ]
    assert _answers(metta, "!(p145-bigint 1)") == [
        "(Error (p145-bigint 1) (BadArgType 1 BigInt Number))"
    ]
    assert _answers(metta, "!(get-type p145-declared-bigint)") == ["BigInt"]


def test_mixed_bigint_number_equality_uses_exact_values(metta):
    wide = I64_MAX + 1
    assert metta.run(f"!(== {wide} {wide})") == [[True]]
    assert metta.run(f"!(== {wide} {I64_MAX})") == [[False]]
    assert metta.run(f"!(!= {wide} {I64_MAX})") == [[True]]


def test_numeric_types_are_published_from_the_catalog(metta):
    assert metta.run(
        "!(match &petta (vocabulary numeric-type $first $second) "
        "($first $second))"
    ) == [[parse("(Number BigInt)")]]
    assert NUMERIC_TYPE == ("Number", "BigInt")
    assert get_args(NumericType) == NUMERIC_TYPE


def test_janus_carries_bigint_losslessly(metta):
    values = (
        I64_MIN - 1,
        I64_MAX + 1,
        2**127 + 12_345,
        -(2**127 + 12_345),
    )
    for value in values:
        assert metta.runtime.must("Y = X", X=value)["Y"] == value

        wire = metta.runtime.must("petta_py_encode(X, W)", X=value)["W"]
        assert wire == ["n", value]
        assert metta.runtime.must(
            "petta_py_decode_shared(W, Y, _)", W=wire
        )["Y"] == value
