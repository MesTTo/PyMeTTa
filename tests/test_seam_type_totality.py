"""Purpose: pin the seam behaviour Phase 5 item P5.15 asked for, which
measurement shows already holds: a heterogeneous list crosses with every
element carrying a type fact, the opaque element included, and get-type
over the encoded list is total. Nothing pinned it, so it could regress to
the %Undefined% reading the item was filed against without a test moving.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose


class _Payload:
    """An object no codec knows, so it crosses opaquely."""


def test_get_type_over_an_encoded_heterogeneous_list_is_total(metta):
    """Measured 2026-08-19: (1 <_Payload> 2) answers (Number _Payload
    Number). The opaque element names its own Python type rather than
    %Undefined%, which is the difference between "the seam does not know"
    and "the seam knows it is foreign and says what it is".

    `let` runs the op and get-type inspects the RESULT. Written as
    `(get-type (seam-hetero))` this passed only because get-type used to
    evaluate its argument, so it was reading the property off a call the
    inspection itself made. Both arbiters answer %Undefined% for that
    spelling, since seam-hetero is undeclared and an undeclared head types
    nothing, measured 2026-08-19 on hyperon 0.2.10 and on LeaTTa alike. The
    property this file exists for is about the ENCODED VALUE, so the value
    is produced first and then asked about, which is the arbiter's own
    idiom [source: LeaTTa tests/semantics/types-meta/30_evaluation_control.metta,
    "`let` evaluates the sum first, then substitutes"].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.register_op(lambda: [1, _Payload(), 2], name="seam-hetero", typed=False)
    [[types]] = metta.run("!(let $crossed (seam-hetero) (get-type $crossed))")
    rendered = [str(t) for t in types]
    assert rendered == ["Number", "_Payload", "Number"], rendered
    assert "%Undefined%" not in rendered
