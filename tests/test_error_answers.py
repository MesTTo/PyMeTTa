"""Purpose: the error story across the seam: structured fields on the
PettaError family, `(Error ...)` answers raising at single-value doors while
aggregation keeps them as data, Rows.raise_for_errors as the explicit bridge,
and the boundary re-raising the library's own exceptions instead of
transcripts.
Guarantees:
  - a PettaError raised inside a Python callback crosses Prolog and
    re-arrives as the same object, fields intact [tested
    test_a_provider_refusal_carries_its_parts_across_the_boundary]
  - an op author's own exception class still arrives wrapped as EngineError
    [tested test_an_op_authors_exception_stays_wrapped]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import (
    EngineError,
    MettaOperationError,
    MettaResultError,
    PettaError,
    S,
    V,
    decode,
)
from petta.foreign import SpaceProvider

SAFE_DIV = (
    '(= (err-div $x $y) (if (== $y 0) '
    '(Error (err-div $x $y) "division by zero") (/ $x $y)))'
)


@pytest.fixture()
def m(metta):
    space = metta.new_space()
    space.run(SAFE_DIV)
    return space


def test_base_fields_default_to_none():
    error = PettaError("plain")
    assert (error.atom, error.space, error.operation, error.capability) == (
        None,
        None,
        None,
        None,
    )


def test_operation_error_operation_is_the_base_field():
    error = MettaOperationError("m", operation="op", kind="type_error")
    assert error.operation == "op"
    assert isinstance(error, PettaError)
    assert error.capability is None


def test_one_raises_a_structured_error_on_an_error_answer(m):
    with pytest.raises(MettaResultError) as failure:
        m.one("(err-div 1 0)")
    error = failure.value
    assert str(error.atom) == '(Error (err-div 1 0) "division by zero")'
    assert str(error.culprit) == "(err-div 1 0)"
    assert decode(error.reason) == "division by zero"
    assert error.space == m.space_name
    # The call rides as a note, so the message stays one sentence.
    assert any("err-div" in note for note in error.__notes__)
    # It is the program's own error value, not an engine throw.
    assert isinstance(error, PettaError)
    assert not isinstance(error, EngineError)


def test_one_still_answers_plain_values(m):
    assert m.one("(err-div 8 2)") == 4


def test_first_raises_on_an_error_first_answer_only(m):
    with pytest.raises(MettaResultError):
        m.first("(err-div 1 0)")
    # Tolerance covers absence and later members, not the returned answer.
    assert m.first("(superpose (7 (Error x y)))") == 7
    assert m.first("(empty)") is None


def test_aggregation_doors_keep_errors_as_data(m):
    answers = m.eval("(err-div 1 0)")
    assert len(answers) == 1
    assert str(answers[0]).startswith("(Error ")
    assert m.run("!(err-div 1 0)") == [answers]


def test_fn_doors_split_the_same_way(m):
    f = m.fn("err-div")
    with pytest.raises(MettaResultError):
        f(1, 0)
    with pytest.raises(MettaResultError):
        f.one(1, 0)
    with pytest.raises(MettaResultError):
        f.first(1, 0)
    assert str(f.all(1, 0)[0]).startswith("(Error ")
    assert f(8, 2) == 4


def test_rows_keep_stored_errors_and_offer_the_bridge(m):
    m.add(
        '(log e1 (Error (job 1) "boom"))',
        '(log e2 (Error (job 2) "bust"))',
        "(log ok fine)",
    )
    rows = m.query(S.log(V.id, V.what))
    assert len(rows) == 3  # bindings stay data, stored errors included
    with pytest.raises(ExceptionGroup) as failure:
        rows.raise_for_errors()
    group = failure.value
    assert len(group.exceptions) == 2
    assert all(isinstance(e, MettaResultError) for e in group.exceptions)
    # except* reaches them, the exceptions-chapter contract.
    try:
        rows.raise_for_errors()
    except* MettaResultError as caught:
        assert len(caught.exceptions) == 2


def test_raise_for_errors_chains_when_clean_and_raises_one_plainly(m):
    m.add('(log e1 (Error (job 1) "boom"))', "(log ok fine)")
    clean = m.query(S.log(S.ok, V.what))
    assert clean.raise_for_errors() is clean
    with pytest.raises(MettaResultError) as failure:
        m.query(S.log(S.e1, V.what)).raise_for_errors()
    assert str(failure.value.culprit) == "(job 1)"


def test_rows_one_and_first_stay_content_neutral(m):
    # A row is a binding, not an evaluation answer: a stored error record
    # flows through the scalar Rows doors; raise_for_errors is the bridge.
    m.add('(log e1 (Error (job 1) "boom"))')
    row = m.query(S.log(S.e1, V.what)).one()
    assert str(row.what).startswith("(Error ")


def test_a_provider_refusal_carries_its_parts_across_the_boundary(metta):
    class Moody(SpaceProvider):
        def atoms(self):
            return iter(())

        def add(self, atom):
            pass

        def should_run(self, capability, **request):
            return capability != "add"

    name = "&moody-fields"
    metta.register_space(Moody(), name)
    try:
        space = metta.space(name)
        with pytest.raises(PettaError) as failure:
            space.add(S.fact(1))
        error = failure.value
        # The very object the seam raised, not a transcript of it.
        assert type(error) is PettaError
        assert (error.space, error.operation, error.capability) == (
            name,
            "add-atom",
            "add",
        )
        assert "declines this add request" in str(error)
    finally:
        metta.unregister_space(name)


def test_an_op_authors_exception_stays_wrapped(metta):
    def moodyop(x):
        raise ValueError("nope")

    metta.register_op(moodyop)
    try:
        with pytest.raises(EngineError):
            metta.run("!(moodyop 1)")
    finally:
        metta.unregister_op("moodyop")
