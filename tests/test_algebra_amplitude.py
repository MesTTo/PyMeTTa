"""Purpose: black-box acceptance for the fenced P4.31 amplitude rung.

Guarantees:
  - exact opposite paths cancel inside the finite, contractive, staged
    fragment and any missing fence capability is refused by name [tested:
    test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from metta import S, wire
from metta.algebra import AlgebraRequirementError, Amplitude


def test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside(metta):
    """Cancel two exact paths only after all three fence claims are present."""
    metta.op(
        lambda left, right: left + right,
        name="amplitude-add",
    )
    metta.op(
        lambda left, right: left * right,
        name="amplitude-multiply",
    )
    with metta._new_space() as program:
        with pytest.raises(
            AlgebraRequirementError,
            match="amplitude_fragment_refused",
        ):
            program.annotations(program.name, "amplitude")
        program.add_tagged_fact(Amplitude(1), S.detect(S.dark_port))
        program.add_tagged_fact(Amplitude(-1), S.detect(S.dark_port))
        with pytest.raises(
            AlgebraRequirementError,
            match="amplitude_fragment_refused",
        ):
            program.evaluate_algebra(S.detect(S.dark_port), algebra="amplitude")

        program.annotations(
            program.name,
            "amplitude",
            capabilities=("finite", "contractive", "staged"),
        )
        evaluation = program.evaluate_algebra(
            S.detect(S.dark_port), algebra="amplitude"
        )
        assert len(evaluation.answers) == 1
        assert wire.decode(evaluation.answers[0].tag) == Amplitude(0)
        assert evaluation.plan[0].applied is True
