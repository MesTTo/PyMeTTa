"""Purpose: validate custom matcher thresholds and returned degrees in both
scoring and generation modes.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import math

import pytest
from petta import EngineError, S, matching


@pytest.mark.parametrize("threshold", [-0.1, 1.1, math.inf, math.nan])
def test_matcher_refuses_an_invalid_threshold(metta, threshold):
    with pytest.raises(ValueError, match=r"finite.*\[0, 1\]"):
        matching.matcher(
            metta,
            "invalid-threshold",
            score=lambda query, candidate: 0.5,
            threshold=threshold,
        )


@pytest.mark.parametrize("degree", [-0.1, 1.1, math.inf, math.nan])
def test_matcher_validates_every_scored_degree(metta, degree):
    name = f"invalid-score-{str(degree).replace('.', 'p').replace('-', 'n')}"
    matching.matcher(metta, name, score=lambda query, candidate: degree)
    with pytest.raises(EngineError, match=r"finite.*\[0, 1\]"):
        metta.run(f"!({name} query candidate)")


@pytest.mark.parametrize("degree", [-0.1, 1.1, math.inf, math.nan])
def test_matcher_validates_every_generated_degree(metta, degree):
    name = f"invalid-generated-{str(degree).replace('.', 'p').replace('-', 'n')}"
    matching.matcher(
        metta,
        name,
        score=lambda query, candidate: 0.5,
        generate=lambda query: [(S.candidate, degree)],
    )
    with pytest.raises(EngineError, match=r"finite.*\[0, 1\]"):
        metta.run(f"!(collapse ({name} query $answer))")
