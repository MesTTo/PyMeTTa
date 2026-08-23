"""Purpose: the numeric boundary past binary64, both sides, and the float
text seam. Engine arithmetic saturates to the IEEE value the way the
reader's literals already do, a printed answer spells a non-finite float
the arbiter's way (inf, -inf, NaN), and a finite float prints the
arbiter's LAYOUT over the shortest-round-trip digits: 1e16, 0.00001 and
1.5e300 rather than SWI's 1.0e+16, 1.0e-05 and 1.5e+300. Grounded's own
renderer implements the same law, so one atom has one text in both hosts.
Computed string operands are refused at every numeric math position before the
host can reinterpret one character as its code [tested:
test_a_string_operand_to_math_refuses_instead_of_answering_its_char_code].
Guarantees:
  - numeric print probes collect text through a shape-preserving capture scope
    [tested: test_finite_floats_print_the_arbiters_layout,
    test_gnd_str_spells_numbers_the_engines_way; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import math
import subprocess

import pytest

from metta import ground


def test_a_string_operand_to_math_refuses_instead_of_answering_its_char_code(metta):
    """Every math position rejects a computed one-character string.

    A literal is already caught by translated-call type filtering. The helper
    equation makes the String arrive only after evaluation and therefore pins
    the operation's own door, where SWI otherwise treats ``"s"`` as 115.
    """
    metta.run('(= (p1-string) "s")')
    operations = {
        "pow-math": 2,
        "sqrt-math": 1,
        "abs-math": 1,
        "log-math": 2,
        "exp-math": 1,
        "trunc-math": 1,
        "ceil-math": 1,
        "floor-math": 1,
        "round-math": 1,
        "sin-math": 1,
        "cos-math": 1,
        "tan-math": 1,
        "asin-math": 1,
        "acos-math": 1,
        "atan-math": 1,
        "isnan-math": 1,
        "isinf-math": 1,
        "exp": 1,
    }
    for operation, arity in operations.items():
        for position in range(1, arity + 1):
            arguments = ["2"] * arity
            arguments[position - 1] = "(p1-string)"
            answer = str(metta.run(f'!({operation} {" ".join(arguments)})')[0][0])
            assert answer == (
                f'(Error ({operation} '
                + " ".join('"s"' if index == position else "2"
                           for index in range(1, arity + 1))
                + f") (BadArgType {position} Number String))"
            ), (operation, position, answer)


def test_arithmetic_overflow_agrees_with_the_literal_side(metta):
    """A result past binary64 is the infinity the literal side already reads.

    Hyperon saturates, its arithmetic being plain Rust f64 [source:
    hyperon-experimental arithmetics.rs; "1e400".parse::<f64>() answers
    Ok(inf)], and the reader here saturates literals the same way, so an
    erroring operation side left the two halves of one boundary
    disagreeing: 1e400 read as inf, then (+ 1e400 1) raised
    float_overflow, SWI's error mode rejecting any non-finite RESULT even
    when an operand was already a legally read infinity.
    """
    assert metta.run("!(+ 1e400 1)")[0] == [math.inf]
    assert metta.run("!(- 1e400 1)")[0] == [math.inf]
    assert metta.run("!(* -1e400 2)")[0] == [-math.inf]
    assert metta.run("!(* 1e308 10.0)")[0] == [math.inf]
    assert metta.run("!(pow-math 10.0 400)")[0] == [math.inf]
    assert metta.run("!(exp-math 1000)")[0] == [math.inf]


def test_real_valued_math_treats_integer_and_float_operands_alike(metta):
    """Real-valued math promotes integers before applying binary64 math.

    LeaTTa's ``toFloat?``-based ``floatUn`` and ``floatBin`` paths govern
    sqrt, log, trig, and pow. Its ``powMath`` additionally limits an integer
    exponent to signed i32 while permitting an unbounded Float exponent and
    always returning Float. ``exp-math`` is covered separately by PeTTa's
    existing real-valued doctrine because LeaTTa's floatUn table excludes it.
    """
    unary_pairs = {
        "sqrt-math": (4, 2.0),
        "sin-math": (0, 0.0),
        "cos-math": (0, 1.0),
        "tan-math": (0, 0.0),
        "asin-math": (0, 0.0),
        "acos-math": (1, 0.0),
        "atan-math": (0, 0.0),
    }
    for operation, (integer, expected) in unary_pairs.items():
        integer_answer = metta.run(f"!({operation} {integer})")[0][0].value
        float_answer = metta.run(f"!({operation} {float(integer)})")[0][0].value
        assert isinstance(integer_answer, float), operation
        assert isinstance(float_answer, float), operation
        assert integer_answer == float_answer == expected, operation

    assert metta.run("!(log-math 10 100)")[0] == [2.0]
    assert metta.run("!(log-math 10.0 100.0)")[0] == [2.0]
    for integer_form, float_form in (
        ("!(sqrt-math -1)", "!(sqrt-math -1.0)"),
        ("!(log-math 10 -5)", "!(log-math 10.0 -5.0)"),
        ("!(asin-math 2)", "!(asin-math 2.0)"),
        ("!(acos-math 2)", "!(acos-math 2.0)"),
    ):
        integer_answer = metta.run(integer_form)[0][0].value
        float_answer = metta.run(float_form)[0][0].value
        assert math.isnan(integer_answer), integer_form
        assert math.isnan(float_answer), float_form

    assert metta.run("!(pow-math 2 3)")[0] == [8.0]
    assert metta.run("!(pow-math 1 -2147483648)")[0] == [1.0]
    assert metta.run("!(pow-math 1 2147483647)")[0] == [1.0]
    assert metta.run("!(pow-math 0 -1)")[0] == [math.inf]
    assert metta.run("!(pow-math 1 2147483648.0)")[0] == [1.0]
    reason = "power argument is too big, try using float value"
    for exponent in (2147483648, -2147483649):
        answer = str(metta.run(f"!(pow-math 2 {exponent})")[0][0])
        assert answer == f'(Error (pow-math 2 {exponent}) "{reason}")'

    assert metta.run("!(exp-math 1)")[0] == metta.run("!(exp-math 1.0)")[0]


def test_integer_division_past_binary64_saturates_instead_of_escaping(metta):
    """A promoted power can still overflow before an integer division.

    ``pow-math`` promotes its base to Float and saturates the result before
    division sees it. Dividing that infinity by an integer remains infinity.
    """
    assert metta.run("!(/ (pow-math 10 400) 3)")[0] == [math.inf]


def test_non_finite_floats_print_the_arbiters_spellings(repo_root, tmp_path):
    """Printed answers spell inf, -inf and NaN, never 1.0Inf or 1.5NaN.

    The spellings are the arbiter's own: hyperon prints Rust f64 Display
    forms and LeaTTa's Pretty.lean pins infinity by sign and an unsigned
    NaN. The NaN answer arrives through the host, the one door the seam
    documents for non-finite construction.
    """
    program = tmp_path / "nonfinite.metta"
    program.write_text(
        "!(+ 1e400 1)\n"
        "!(* -1e400 2)\n"
        "!(py-atom \"float('nan')\")\n",
        encoding="utf-8",
    )
    done = subprocess.run(
        ["swipl", "-q", "-s", str(repo_root / "engine" / "main.pl"),
         "--", "silent", str(program)],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
    )
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    assert lines[-3:] == ["inf", "-inf", "NaN"]
    assert "1.0Inf" not in done.stdout
    assert "1.5NaN" not in done.stdout


def test_the_seam_still_refuses_what_arithmetic_can_now_make(metta):
    """Saturation widens what arithmetic ANSWERS, not what the seam STORES.

    A digest of a space holding an arithmetic infinity refuses exactly as
    the constructor-built one always did: the printed spelling reads back
    as a symbol of that name, upstream's included, so the round-trip law
    still rules it out.
    """
    with metta._new_space() as m:
        m.run("!(let $x (+ 1e400 1) (add-atom &self (nf $x)))")
        with pytest.raises(ValueError, match=r"reads back as a symbol"):
            m.digest()


def test_float_zero_division_and_nan_agree_with_the_arbiter(metta):
    """Float IEEE non-trapping: division by 0.0 is an infinity, the NaN
    family is NaN.

    Hyperon's float arm is raw Rust f64 arithmetic with no guard, so the
    values are the arbiter's answers, and the engine already ships
    isnan-math and isinf-math to observe them. Integer division by zero
    stays an error here: the arbiter's answer THERE is the Error atom, a
    different shape owned by the error-answer story, and this pins that an
    integer zero answers the contained DivisionByZero atom rather than
    leaking an infinity.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert metta.run("!(/ 1.0 0.0)")[0] == [math.inf]
    assert metta.run("!(/ -1.0 0.0)")[0] == [-math.inf]
    for form in (
        "!(/ 0.0 0.0)",
        "!(- 1e400 1e400)",
        "!(sqrt-math -1.0)",
        "!(log-math 10 -5.0)",
        "!(asin-math 2.0)",
    ):
        answers = metta.run(form)[0]
        assert len(answers) == 1 and math.isnan(answers[0]), form
    assert metta.run("!(isnan-math (- 1e400 1e400))")[0] == [True]
    assert metta.run("!(isinf-math (/ 1.0 0.0))")[0] == [True]


def test_integer_division_by_zero_answers_what_d1_decides(metta):
    """Integer zero division is an operation answer, not a host exception.

    LeaTTa's regression/division_convention.metta pins the direct Error atom;
    collapse then contains that one answer as its one-element expression.
    """
    direct = metta.run("!(/ 7 0)")
    assert str(direct[0][0]) == "(Error (/ 7 0) DivisionByZero)"
    collapsed = metta.run("!(collapse (/ 7 0))")
    assert str(collapsed[0][0]) == "((Error (/ 7 0) DivisionByZero))"
    remainder = metta.run("!(% 7 0)")
    assert str(remainder[0][0]) == "(Error (% 7 0) DivisionByZero)"


def test_finite_floats_print_the_arbiters_layout(metta):
    """A finite float's printed text is the arbiter's layout, not SWI's.

    The digits always agreed, both sides printing the shortest decimal
    that reads back to the same binary64; the LAYOUT did not: SWI's
    number_codes writes 1.0e+16, 1.0e-05 and 1.5e+300 where the arbiter
    writes 1e16, 0.00001 and 1.5e300 [source: LeaTTa
    RyuLean4/Runtime.lean:371-396, Decimal.formatMeTTa, ryu's pretty
    layout, its fallback proved dead]. The pins are the four measured
    divergence witnesses plus one row per layout branch, each driven
    through the public print surface, and each spelling reads back to
    the same value through the public reader.
    """
    pins = [
        ("1e16", 1.0e16),
        ("0.00001", 0.00001),
        ("1.5e300", 1.5e300),
        ("1e26", 1.0e26),
        ("1230.0", 1230.0),
        ("3.8", 3.8),
        ("0.0001", 0.0001),
        ("1e-6", 0.000001),
        ("-1e16", -1.0e16),
        ("5e-324", 5.0e-324),
    ]
    for want, value in pins:
        with metta.capture() as output:
            metta.run(f"!(println! {want})")
        assert output.text.strip() == want, f"{value!r} printed {output.text.strip()}"
        assert metta.run(f"!(min-atom ({want}))") == [[value]], want


def test_gnd_str_spells_numbers_the_engines_way(metta):
    """One atom, one text: str(Grounded(x)) equals the engine's printed answer.

    Grounded rendered numbers with Python's repr, a second number writer that
    split from swrite/2 on the plus sign (1e+16), the exponent padding
    (1e-05), the positional threshold (1e-05 where the law says 0.00001)
    and nan against NaN. Both writers implement the arbiter's layout law
    now; this drives a value through both and demands byte equality, plus
    the non-finite spellings engine-free.
    """
    values = [
        0.0, -0.0, 5.0, 1230.0, 3.8, 0.30000000000000004,
        1e16, 1e15, 1234567890123456.0, 0.0001, 0.00001, 0.000001,
        1.5e-7, 1e26, 1e20, 1.5e300, 5e-324, -5e-324,
        2.2250738585072014e-308, 1.7976931348623157e308, -1e16,
        7, -3, 9223372036854775808,
    ]
    source = "".join(f"!(println! {value!r})\n" for value in values)
    with metta.capture() as output:
        metta.run(source)
    engine_lines = output.text.splitlines()
    assert len(engine_lines) == len(values)
    for value, engine_text in zip(values, engine_lines, strict=True):
        assert str(ground(value)) == engine_text, (
            f"{value!r}: python {str(ground(value))!r} engine {engine_text!r}"
        )
    assert str(ground(math.inf)) == "inf"
    assert str(ground(-math.inf)) == "-inf"
    assert str(ground(math.nan)) == "NaN"
