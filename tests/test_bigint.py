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
  - arithmetic keeps the exact unbounded result beyond Hyperon's i64 carrier
    [tested test_integer_arithmetic_is_unbounded_where_hyperon_checks_i64]
  - Janus and the tagged n form carry BigInt values in both directions
    without changing a digit [tested test_janus_carries_bigint_losslessly]
Open Obligations:
  To Do: Re-verify these rules when LeaTTa adds its announced BigInt type.
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose


from hypothesis import given, settings
from hypothesis import strategies as st

from metta import parse
from metta.vocabularies import NumericType

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


def _answers(metta, form: str) -> list[str]:
    return [str(atom) for group in metta.run(form) for atom in group]


def test_bigint_and_number_type_the_numeric_tower(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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

    assert _answers(
        metta, "!(let $value (* 4611686018427387904 4) (get-type $value))"
    ) == ["BigInt"]


def test_integer_arithmetic_is_unbounded_where_hyperon_checks_i64(metta):
    """The product past Hyperon's i64 boundary stays exact, per LeaTTa's unbounded integers."""
    assert metta.run("!(* 4611686018427387904 4)") == [
        [18_446_744_073_709_551_616]
    ]


@settings(max_examples=50)
@given(st.integers(min_value=-(2**256), max_value=2**256))
def test_integer_type_follows_the_signed_i64_boundary(metta, value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    expected = "Number" if I64_MIN <= value <= I64_MAX else "BigInt"
    assert _answers(metta, f"!(get-type {value})") == [expected]


def test_number_parameters_accept_bigint_without_retyping_number(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_mixed_bigint_number_equality_uses_exact_values(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    wide = I64_MAX + 1
    assert metta.run(f"!(== {wide} {wide})") == [[True]]
    assert metta.run(f"!(== {wide} {I64_MAX})") == [[False]]
    assert metta.run(f"!(!= {wide} {I64_MAX})") == [[True]]


def test_numeric_types_are_published_from_the_catalog(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert metta.run(
        "!(match &petta (vocabulary numeric-type $first $second) "
        "($first $second))"
    ) == [[parse("(Number BigInt)")]]
    assert tuple(NumericType) == ("Number", "BigInt")
    assert "BigInt" in NumericType


def test_janus_carries_bigint_losslessly(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
