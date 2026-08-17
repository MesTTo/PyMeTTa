"""Purpose: the Python door of the MeTTa (transaction ...) form:
m.transaction runs a callable inside one engine transaction now, and
m.transactional is its decorator twin.
Guarantees:
  - a raise inside the callable rolls back stored atoms AND compiled
    equations, and re-raises the caller's own exception class [tested
    test_a_raise_rolls_back_everything_and_arrives_as_itself]
  - an inner transaction's commit is relative to its outer transaction
    [tested test_nested_commit_dies_with_the_outer_rollback]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import MettaResultError, S


@pytest.fixture()
def m(metta):
    return metta.new_space()


def test_commit_answers_the_callables_return_value(m):
    def work():
        m.add(S.tx(1))
        return {"rows": [1, "two"]}

    assert m.transaction(work) == {"rows": [1, "two"]}
    assert m.atoms() == [S.tx(1)]
    assert m.transaction(lambda: None) is None


def test_return_values_keep_identity(m):
    marker = object()
    assert m.transaction(lambda: marker) is marker


def test_a_raise_rolls_back_everything_and_arrives_as_itself(m):
    def failing():
        m.add(S.tx(2))
        m.run("(= (tx-f $x) $x)")
        raise ValueError("undo everything")

    with pytest.raises(ValueError, match="undo everything") as failure:
        m.transaction(failing)
    # The chain keeps the boundary visible rather than hiding it.
    assert type(failure.value.__cause__).__name__ == "EngineError"
    assert m.atoms() == []
    # The equation's compiled clauses rolled back with its atom.
    assert m.is_function("tx-f") is False
    assert m.run("!(tx-f 3)") == [[m.parse("(tx-f 3)")]]


def test_the_librarys_own_errors_pass_through_unchanged(m):
    m.run('(= (tx-err) (Error (tx-err) "boom"))')

    def body():
        m.one("(tx-err)")

    with pytest.raises(MettaResultError):
        m.transaction(body)
    # The handle stays fully usable after the rollback; the equation was
    # added OUTSIDE the transaction, so it rightly survives.
    m.add(S.tx(9))
    assert S.tx(9) in m


def test_nested_commit_dies_with_the_outer_rollback(m):
    def outer():
        m.transaction(lambda: m.add(S.tx(3)))
        raise RuntimeError("outer dies")

    with pytest.raises(RuntimeError):
        m.transaction(outer)
    assert m.atoms() == []
    # And a nested transaction under a COMMITTING outer commits.
    m.transaction(lambda: m.transaction(lambda: m.add(S.tx(4))))
    assert m.atoms() == [S.tx(4)]


def test_transactional_is_the_decorator_twin(m):
    @m.transactional
    def migrate(n):
        m.add(S.tx(n))
        if n < 0:
            raise ValueError("negative")
        return n * 2

    # Decorating ran nothing; calling runs one transaction per call.
    assert m.atoms() == []
    assert migrate(5) == 10
    assert m.atoms() == [S.tx(5)]
    with pytest.raises(ValueError):
        migrate(-1)
    assert m.atoms() == [S.tx(5)]  # the failing call's write rolled back
    assert migrate.__name__ == "migrate"  # functools.wraps preserved it
