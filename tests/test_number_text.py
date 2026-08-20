"""Purpose: the numeric boundary past binary64, both sides, and the float
text seam. Engine arithmetic saturates to the IEEE value the way the
reader's literals already do, a printed answer spells a non-finite float
the arbiter's way (inf, -inf, NaN), and a finite float prints the
arbiter's LAYOUT over the shortest-round-trip digits: 1e16, 0.00001 and
1.5e300 rather than SWI's 1.0e+16, 1.0e-05 and 1.5e+300. Gnd's own
renderer implements the same law, so one atom has one text in both hosts.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import math
import subprocess

import pytest

from petta import MettaOperationError, val


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


def test_integer_division_past_binary64_saturates_instead_of_escaping(metta):
    """An all-integer division can still overflow, in the float conversion.

    (/ (pow-math 10 400) 3) is exact unbounded-integer work until the
    non-divisible pair converts to float, and that conversion overflowed on
    the CATCHLESS integer fast path, so the raw is/2 error escaped without
    even the operation context the float arms attach.
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
    with metta.new_space() as m:
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
    integer zero keeps raising rather than leaking an infinity.
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
    with pytest.raises(MettaOperationError):
        metta.run("!(/ 1 0)")


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
        _, text = metta.run(f"!(println! {want})", capture=True)
        assert text.strip() == want, f"{value!r} printed {text.strip()}"
        assert metta.run(f"!(min-atom ({want}))") == [[value]], want


def test_gnd_str_spells_numbers_the_engines_way(metta):
    """One atom, one text: str(Gnd(x)) equals the engine's printed answer.

    Gnd rendered numbers with Python's repr, a second number writer that
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
    _, printed = metta.run(source, capture=True)
    engine_lines = printed.splitlines()
    assert len(engine_lines) == len(values)
    for value, engine_text in zip(values, engine_lines, strict=True):
        assert str(val(value)) == engine_text, (
            f"{value!r}: python {str(val(value))!r} engine {engine_text!r}"
        )
    assert str(val(math.inf)) == "inf"
    assert str(val(-math.inf)) == "-inf"
    assert str(val(math.nan)) == "NaN"
