"""Purpose: exercise the public typing and policy contracts introduced by P3.
Guarantees:
  - type faults remain ordinary Error values that ``if-error`` can observe.
  [tested: test_an_argument_type_fault_is_a_value_a_program_can_catch; commit=WORKTREE]
"""

from petta import MeTTa


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one query group's atoms in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


def test_an_argument_type_fault_is_a_value_a_program_can_catch():
    metta = MeTTa(verbose=False)
    metta.run("(: p32-f (-> Number Number))")
    metta.run("(= (p32-f $x) $x)")

    assert _answers(metta, '!(if-error (p32-f "wrong") caught missed)') == [
        "caught"
    ]
    assert _answers(metta, "!(if-error (p32-f 1 2) caught missed)") == [
        "caught"
    ]
    assert _answers(
        metta, '!(if-error (type-cast "wrong" Number &self) caught missed)'
    ) == ["caught"]

