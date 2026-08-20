"""Purpose: black-box acceptance for the fenced P4.31 amplitude rung.

Guarantees:
  - exact opposite paths cancel inside the finite, contractive, staged
    fragment and any missing fence capability is refused by name [tested:
    test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside;
    commit=1822ca53390b180e622f262b766f224ae7a9278f]
"""

import pytest

from petta import AlgebraRequirementError, Amplitude, S, decode


def test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside(metta):
    """Cancel two exact paths only after all three fence claims are present."""
    metta.register_op(
        lambda left, right: left + right,
        name="amplitude-add",
        raw=False,
    )
    metta.register_op(
        lambda left, right: left * right,
        name="amplitude-multiply",
        raw=False,
    )
    with metta.new_space() as program:
        with pytest.raises(
            AlgebraRequirementError,
            match="amplitude_fragment_refused",
        ):
            program.declare_annotations(program.space_name, "amplitude")
        program.add_tagged_fact(Amplitude(1), S.detect(S.dark_port))
        program.add_tagged_fact(Amplitude(-1), S.detect(S.dark_port))
        with pytest.raises(
            AlgebraRequirementError,
            match="amplitude_fragment_refused",
        ):
            program.evaluate_algebra(S.detect(S.dark_port), algebra="amplitude")

        program.declare_annotations(
            program.space_name,
            "amplitude",
            capabilities=("finite", "contractive", "staged"),
        )
        evaluation = program.evaluate_algebra(
            S.detect(S.dark_port), algebra="amplitude"
        )
        assert len(evaluation.answers) == 1
        assert decode(evaluation.answers[0].tag) == Amplitude(0)
        assert evaluation.plan[0].applied is True
