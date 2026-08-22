"""Purpose: pin the in-language halves of the error story, switch and throw.
Assumes: nothing beyond the ordinary MeTTa surface; both forms are engine
  vocabulary reachable with no import.
Guarantees:
  - switch matches its rows in source order and reads a key that answered
    nothing as no answer, which is the single point it differs from case.
  [tested: test_switch_reads_a_key_with_no_answers_as_no_answer; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
  - a thrown reason becomes a produced error atom, so it finishes the enclosing
    call the way an engine-raised one does, and an already-raised reason is
    handed on rather than wrapped twice.
  [tested: test_a_thrown_reason_travels_as_a_produced_error; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from petta import MeTTa

# The arbiter for switch is LeaTTa tests/semantics/control-stdlib/03_case_switch.metta,
# whose STATUS records switch as conforming against the pinned Hyperon 0.2.10
# binary and whose MEASURED block carries the five lines asserted below. case is
# in the same file and already answers its six lines; the pair is asserted
# together because the forms are defined against each other.
_KEY = "(= (control-key) second)"


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one runnable's answers in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


def test_switch_reads_a_key_with_no_answers_as_no_answer() -> None:
    """Switch is case except at the one point upstream says they differ."""
    metta = MeTTa("&errorcontrol-switch")
    metta.run(_KEY)

    # The key is evaluated, and rows are tried in the order they are written.
    assert _answers(
        metta,
        "!(switch (control-key) ((first wrong) (second specific) ($_ catchall)))",
    ) == ["specific"]
    assert _answers(metta, "!(switch second (($_ first-row) (second later)))") == [
        "first-row"
    ]
    # No row matches, so there is no answer and no fallback.
    assert _answers(metta, "!(switch absent ((first wrong) (second wrong)))") == []
    # A key that answered NOTHING selects nothing, not the Empty row. This is
    # the one point switch and case differ.
    assert _answers(
        metta, "!(switch (empty) ((Empty empty-row) ($_ variable-row)))"
    ) == []
    # The literal symbol Empty is an ordinary key, matched in row order.
    assert _answers(
        metta, "!(switch Empty (($_ variable-row) (Empty literal-row)))"
    ) == ["variable-row"]

    # case, for the contrast, reads the same no-answer key as the symbol Empty.
    assert _answers(
        metta, "!(case (empty) (($_ variable-row) (Empty empty-row)))"
    ) == ["empty-row"]
    assert _answers(metta, "!(case (empty) (($_ variable-row)))") == []
    assert _answers(
        metta, "!(case Empty (($_ variable-row) (Empty literal-row)))"
    ) == ["variable-row"]


def test_a_thrown_reason_travels_as_a_produced_error() -> None:
    """A raised reason finishes the enclosing call the way an engine error does."""
    metta = MeTTa("&errorcontrol-throw")
    metta.run("(= (control-guard $n) (if (< $n 0) (throw NegativeInput) $n))")
    raised = "(Error (throw NegativeInput) NegativeInput)"

    assert _answers(metta, "!(throw MyReason)") == [
        "(Error (throw MyReason) MyReason)"
    ]
    assert _answers(metta, "!(control-guard 5)") == ["5"]
    assert _answers(metta, "!(control-guard -1)") == [raised]

    # A produced error finishes the enclosing call, so a raise travels exactly
    # as an engine-raised BadArgType does.
    assert _answers(metta, "!(+ 1 (control-guard -1))") == [raised]
    assert _answers(metta, "!(== 4 (control-guard -1))") == [raised]
    assert _answers(metta, "!(if (< 0 (control-guard -1)) yes no)") == [raised]

    # And the railway combinators observe it.
    assert _answers(metta, "!(if-error (control-guard -1) caught missed)") == [
        "caught"
    ]
    assert _answers(metta, "!(return-on-error (control-guard -1) fallback)") == [
        raised
    ]
    assert _answers(metta, "!(collapse (control-guard -1))") == [f"({raised})"]

    # Re-raising hands an already-raised reason on rather than wrapping it.
    assert _answers(metta, "!(throw (Error somewhere BadThing))") == [
        "(Error somewhere BadThing)"
    ]

    # A WRITTEN error atom stays data, which is what makes throw the door that
    # changes anything: building the atom does not raise it.
    assert _answers(metta, "!(+ (Error somewhere BadThing) 1)") == [
        "(Error (+ (Error somewhere BadThing) 1) (BadArgType 1 Number ErrorType))"
    ]
