"""Purpose: pin type-checker behaviour against LeaTTa's measured programs.
Assumes:
  - LEATTA_PATH names the local LeaTTa checkout, defaulting to the workstation
    path used by tests/conformance/leatta.py.
Guarantees:
  - a type variable bound by an earlier application constrains later arguments
    before those arguments are evaluated.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from petta import MeTTa

_ARBITER_ROOT = (
    Path(os.environ["LEATTA_PATH"])
    if "LEATTA_PATH" in os.environ
    else Path(__file__).resolve().parents[4] / "LeaTTa"
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
        groups, captured = isolated.run(source, capture=True)
    return [[str(atom) for atom in group] for group in groups], captured


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
