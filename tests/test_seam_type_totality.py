"""Purpose: pin the seam behaviour Phase 5 item P5.15 asked for, which
measurement shows already holds: a heterogeneous list crosses with every
element carrying a type fact, the opaque element included, and get-type
over the encoded list is total. Nothing pinned it, so it could regress to
the %Undefined% reading the item was filed against without a test moving.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""


class _Payload:
    """An object no codec knows, so it crosses opaquely."""


def test_get_type_over_an_encoded_heterogeneous_list_is_total(metta):
    """Measured 2026-08-19: (1 <_Payload> 2) answers (Number _Payload
    Number). The opaque element names its own Python type rather than
    %Undefined%, which is the difference between "the seam does not know"
    and "the seam knows it is foreign and says what it is"."""
    metta.register_op(lambda: [1, _Payload(), 2], name="seam-hetero", typed=False)
    [[types]] = metta.run("!(get-type (seam-hetero))")
    rendered = [str(t) for t in types]
    assert rendered == ["Number", "_Payload", "Number"], rendered
    assert "%Undefined%" not in rendered
