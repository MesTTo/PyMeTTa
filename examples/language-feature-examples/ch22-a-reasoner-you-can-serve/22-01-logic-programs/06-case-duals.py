"""Purpose: negate each arm of a compiled case, including its final wildcard.

A selected True arm is provable. A False arm, or a key matching no arm,
is not provable. Nested case rows preserve these answers.
"""

from metta import S


def twin(m):
    """Check both truth values and the unmatched-key case under negation."""
    @m.define
    def case_band(key):
        match key:
            case 90:
                return True
            case remaining:
                match remaining:
                    case 40:
                        return False

    @m.define
    def case_default(key):
        match key:
            case 90:
                return True
            case remaining:
                match remaining:
                    case 40:
                        return False
                    case _:
                        return False

    assert m.fn.not_provable(S.case_band(90)) == [False]
    assert m.fn.not_provable(S.case_band(40)) == [True]
    assert m.fn.not_provable(S.case_band(55)) == [True]
    assert case_band(55) == []
    assert m.fn.not_provable(S.case_default(90)) == [False]
    assert m.fn.not_provable(S.case_default(40)) == [True]
    assert m.fn.not_provable(S.case_default(55)) == [True]


#: The final image includes the provisioned engine and MORK artifacts.
#: [measured 2026-09-05: 9510, 9510, 9510 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/06-case-duals.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
BUDGET = 9510
