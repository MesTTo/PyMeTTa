"""Purpose: the error story across the seam: structured fields on the
MettaError family, `(Error ...)` answers raising at single-value doors while
aggregation keeps them as data, Rows.raise_for_errors as the explicit bridge,
and the boundary re-raising the library's own exceptions instead of
transcripts.
Guarantees:
  - a MettaError raised inside a Python callback crosses Prolog and
    re-arrives as the same object, fields intact [tested
    test_a_provider_refusal_carries_its_parts_across_the_boundary]
  - an op author's own exception class still arrives wrapped as EngineError
    even when several are grouped [tested:
    test_an_op_authors_exception_stays_wrapped,
    test_an_op_authors_exception_group_stays_wrapped; commit=d8673a8488a111f1c01c778af3ed11b845c284a8]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import Expression, G, MettaError, S, V, wire
from metta.errors import EngineError, MettaOperationError, MettaResultError
from metta.foreign import SpaceProvider

SAFE_DIV = (
    '(= (err-div $x $y) (if (== $y 0) '
    '(Error (err-div $x $y) "division by zero") (/ $x $y)))'
)


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._new_space()
    space.run(SAFE_DIV)
    return space


def test_base_fields_default_to_none():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    error = MettaError("plain")
    assert (error.atom, error.space, error.operation, error.capability) == (
        None,
        None,
        None,
        None,
    )


def test_operation_error_operation_is_the_base_field():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    error = MettaOperationError("m", operation="op", kind="type_error")
    assert error.operation == "op"
    assert isinstance(error, MettaError)
    assert error.capability is None


def test_one_raises_a_structured_error_on_an_error_answer(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaResultError) as failure:
        m._one("(err-div 1 0)")
    error = failure.value
    assert str(error.atom) == '(Error (err-div 1 0) "division by zero")'
    assert str(error.culprit) == "(err-div 1 0)"
    assert wire.decode(error.reason) == "division by zero"
    assert error.space == m.name
    # The call rides as a note, so the message stays one sentence.
    assert any("err-div" in note for note in error.__notes__)
    # It is the program's own error value, not an engine throw.
    assert isinstance(error, MettaError)
    assert not isinstance(error, EngineError)


def test_one_still_answers_plain_values(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m._one("(err-div 8 2)") == 4


def test_first_raises_on_an_error_first_answer_only(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaResultError):
        m._first("(err-div 1 0)")
    # Tolerance covers absence and later members, not the returned answer.
    assert m._first("(superpose (7 (Error x y)))") == 7
    assert m._first("(empty)") is None


def test_aggregation_doors_keep_errors_as_data(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    answers = m.eval("(err-div 1 0)")
    assert len(answers) == 1
    assert str(answers[0]).startswith("(Error ")
    assert m.run("!(err-div 1 0)") == [answers]


def test_fn_doors_split_the_same_way(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    f = m.fn.err_div
    failed = f(1, 0)
    assert str(failed[0]).startswith("(Error ")
    with pytest.raises(MettaResultError):
        failed.one()
    with pytest.raises(MettaResultError):
        failed.first()
    assert f(8, 2) == [4]


def test_rows_keep_stored_errors_and_offer_the_bridge(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(
        '(log e1 (Error (job 1) "boom"))',
        '(log e2 (Error (job 2) "bust"))',
        "(log ok fine)",
    )
    rows = m.match(S.log(V.id, V.what))
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


def test_raise_for_errors_chains_when_clean_and_raises_one_plainly(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add('(log e1 (Error (job 1) "boom"))', "(log ok fine)")
    clean = m.match(S.log(S.ok, V.what))
    assert clean.raise_for_errors() is clean
    with pytest.raises(MettaResultError) as failure:
        m.match(S.log(S.e1, V.what)).raise_for_errors()
    assert str(failure.value.culprit) == "(job 1)"


def test_rows_one_and_first_stay_content_neutral(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A row is a binding, not an evaluation answer: a stored error record
    # flows through the scalar Rows doors; raise_for_errors is the bridge.
    m.add('(log e1 (Error (job 1) "boom"))')
    row = m.match(S.log(S.e1, V.what)).one()
    assert str(row.what).startswith("(Error ")


def test_a_provider_refusal_carries_its_parts_across_the_boundary(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Moody(SpaceProvider):
        def atoms(self):
            return iter(())

        def add(self, atom):
            pass

        def should_run(self, capability, **request):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return capability != "add"

    name = "&moody-fields"
    metta._register_space(Moody(), name)
    try:
        space = metta._at(name)
        with pytest.raises(MettaError) as failure:
            space.add(S.fact(1))
        error = failure.value
        # The very object the seam raised, not a transcript of it.
        assert type(error) is MettaError
        assert (error.space, error.operation, error.capability) == (
            name,
            "add-atom",
            "add",
        )
        assert "declines this add request" in str(error)
    finally:
        metta._unregister_space(name)


def test_an_op_authors_exception_stays_wrapped(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def moodyop(x):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        msg = "nope"
        raise ValueError(msg)

    metta.op(moodyop, effect="pureStructural")
    try:
        with pytest.raises(EngineError):
            metta.run("!(moodyop 1)")
    finally:
        metta.unregister_op("moodyop")


def test_an_op_authors_exception_group_stays_wrapped(metta):
    """Only groups whose every leaf is a library error cross intact."""

    def moodygroup(x):  # noqa: ARG001  -- the reflected parameter is part of the operation protocol
        message = "two user failures"
        raise ExceptionGroup(
            message, [ValueError("nope"), RuntimeError("still nope")]
        )

    metta.op(moodygroup, effect="pureStructural")
    try:
        with pytest.raises(EngineError) as caught:
            metta.run("!(moodygroup 1)")
    finally:
        metta.unregister_op("moodygroup")

    assert not isinstance(caught.value, BaseExceptionGroup)
    assert "two user failures" in str(caught.value)


def test_case_dual_refusal_names_the_unarrived_cases(metta):
    """The refusal says WHY: the cases have not arrived at compile time.

    A dual is built once, out of the equation as written, so case branches
    handed in at run time have none to negate. let*'s dual already refuses
    with that precise reason; case fell through to the generic special-form
    refusal, which names a true fact about case and the wrong reason for
    this equation.
    """
    with metta._new_space() as space:
        space.run("(= (cdrf-key) 1)")
        space.run("(= (cdrf-handed $cs) (case (cdrf-key) $cs))")
        with pytest.raises(EngineError) as caught:
            space.run("!(not-provable (cdrf-handed (quote ((1 (> 1 0))))))")
        message = str(caught.value)
        assert "arrive" in message
        assert "writing the cases out" in message
        assert "special form" not in message


def test_an_opaque_argument_does_not_replace_the_failure_it_was_passed_to(metta):
    """The report of a failed call must not fail on the call's own arguments.

    `prolog:message//1` rendered the failing call through the ROUND-TRIP
    writer, which refuses a value whose printed form would read back as
    something else. An opaque host handle is exactly such a value, so
    reporting the failure threw out of the renderer and the caller received
    that refusal instead of what the operation raised:

        PrologError: swrite/2: cannot write <py_Box>(0x...) as MeTTa text

    with the operation's own message gone. Rendering a message is display, not
    round-trip, so the total writer answers it.
    """
    def opaque_op(handle):  # noqa: ARG001  -- the reflected parameter is part of the operation protocol
        message = "clean"
        raise MettaError(message)

    metta.op(opaque_op, effect="oracleIO")
    try:
        with pytest.raises(EngineError) as caught:
            metta.eval(Expression([S["opaque-op"], G(object())]))
    finally:
        metta.unregister_op("opaque-op")

    text = str(caught.value)
    assert "clean" in text, text
    assert "swrite" not in text, text
    # The operation is still named, which is the whole point of rendering the
    # call, and the argument that could not be written appears by identity.
    assert "opaque-op" in text, text
