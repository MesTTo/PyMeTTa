"""Purpose: pin type-checker behaviour against LeaTTa's measured programs.
Assumes:
  - LEATTA_PATH names the local LeaTTa checkout, defaulting to the workstation
    path used by tests/conformance/leatta.py.
Guarantees:
  - a type variable bound by an earlier application constrains later arguments
    before those arguments are evaluated.
  - quote remains a value while let can evaluate before constructing that value.
  - corpus output is captured without changing the evaluated group shape
    [tested:
    test_a_type_variable_bound_through_an_application_constrains_the_next_argument;
    commit=6fbd5872cc0ff7abf9c99b90f915f8a31470a861]
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from petta import MeTTa

_ARBITER_ROOT = (
    Path(os.environ["LEATTA_PATH"])
    if "LEATTA_PATH" in os.environ
    else Path(__file__).resolve().parents[5] / "LeaTTa"
)
_TYPES_META = _ARBITER_ROOT / "tests" / "semantics" / "types-meta"

needs_arbiter = pytest.mark.skipif(
    not _TYPES_META.exists(),
    reason="the LeaTTa semantics corpus is a fixed local checkout outside this "
    "repository; agreement is enforced only where it exists",
)


def _run_file(metta, name: str) -> tuple[list[list[str]], str]:
    source = (_TYPES_META / name).read_text()
    with metta.new_space() as isolated:
        with isolated.capture() as output:
            groups = isolated.run(source)
    return [[str(atom) for atom in group] for group in groups], output.text


@needs_arbiter
def test_a_type_variable_bound_through_an_application_constrains_the_next_argument():
    metta = MeTTa(verbose=False)
    groups, _ = _run_file(metta, "11_atom_parameter_type_variable.metta")
    assert groups == [
        [],
        ["(Error (k pa (+ 1 2)) (BadArgType 2 Atom Number))"],
    ]
    groups, captured = _run_file(
        metta, "12_atom_parameter_type_variable_trace.metta"
    )
    assert groups == [
        ["(Error (k pa (probe)) (BadArgType 2 Atom Number))"],
    ]
    assert "PROBE-RAN" not in captured.splitlines(), (
        "type applicability ran the rejected probe"
    )


@needs_arbiter
def test_quote_survives_as_a_value():
    groups, _ = _run_file(
        MeTTa(verbose=False), "30_evaluation_control.metta"
    )
    assert groups == [
        ["(-> Atom Atom)"],
        ["(+ 1 2)"],
        ["Symbol"],
        ["(-> Atom Atom)"],
        ["(quote (+ 1 2))"],
        ["(quote 3)"],
        ["Symbol"],
        ["(-> Atom Atom ErrorType)"],
        ["ErrorType"],
        ["(Error (+ 2 3) (+ 4 5))"],
    ]
