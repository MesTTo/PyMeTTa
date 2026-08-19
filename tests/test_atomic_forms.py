"""Purpose: the atomic forms answer everything their body answers and still
commit or roll back whole.
Guarantees:
  - a three-answer body inside a transaction answers three times, and every
    answer's writes land together [tested
    test_a_transaction_preserves_every_answer_of_its_body]
  - a body that ends with no answer rolls the whole transaction back, and one
    that raises rolls it back and re-raises [tested
    test_a_transaction_rolls_back_every_answers_writes_together]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import EngineError


def _answers(space, query):
    """The one collapsed answer group of a query, as strings."""
    [[collapsed]] = space.run(query)
    return [str(a) for a in collapsed]


@pytest.fixture()
def three(metta):
    """A space of its own where one name has three equations, so its call is
    a body with three answers rather than a superpose a form could
    special-case. The space is per-test because the `metta` fixture is
    session-scoped, so equations written into the base tier would accumulate
    across tests and a three-answer body would quietly become a nine-answer
    one."""
    space = metta.new_space()
    for answer in (1, 2, 3):
        space.run(f"(= (petta-three) {answer})")
    return space


def test_a_transaction_preserves_every_answer_of_its_body(three):
    """Reproduced 2026-08-19: `!(collapse (petta-three))` answered `(1 2 3)`
    and `!(collapse (transaction (petta-three)))` answered `(1)`. Two of the
    three answers were gone and nothing said so, because SWI's transaction/1
    runs its goal as once/1.

    Dropping them is an opacity violation in the transactional-memory sense:
    a reader of the result sees a state no serial run of the body produces.
    """
    assert _answers(three, "!(collapse (petta-three))") == ["1", "2", "3"]
    assert _answers(three, "!(collapse (transaction (petta-three)))") == ["1", "2", "3"]
    # A superpose body is the same claim written without equations.
    assert _answers(three, "!(collapse (transaction (superpose (a b c))))") == [
        "a",
        "b",
        "c",
    ]
    # An answer that binds a caller variable replays its own binding rather
    # than a copy of whichever one came first.
    three.run("(= (petta-tag 1) one)")
    three.run("(= (petta-tag 2) two)")
    assert _answers(
        three, "!(collapse (transaction (petta-tag (superpose (1 2)))))"
    ) == ["one", "two"]


def test_a_transaction_rolls_back_every_answers_writes_together(three):
    """Preserving the answers must not cost the atomicity that is the form's
    reason to exist, so each half is checked with a body that answers more
    than once."""
    # Every answer writes, and every write lands.
    assert _answers(
        three,
        "!(collapse (transaction (superpose ((add-atom (context-space) (kept 1)) "
        "(add-atom (context-space) (kept 2))))))",
    ) == ["()", "()"]
    assert _answers(three, "!(collapse (match (context-space) (kept $x) $x))") == [
        "1",
        "2",
    ]

    # Two answers write and then the body ends with none: both writes go.
    three.run(
        "(= (petta-write-then-fail) (progn (superpose ("
        "(add-atom (context-space) (gone 1)) (add-atom (context-space) (gone 2)))) "
        "(empty)))"
    )
    assert _answers(three, "!(collapse (transaction (petta-write-then-fail)))") == []
    assert _answers(three, "!(collapse (match (context-space) (gone $x) $x))") == []

    # Two answers write and then the body raises: both writes go, and the
    # rollback does not swallow the exception.
    def blow():
        raise RuntimeError("the host operation failed")

    three.register_op(blow, name="petta-blow")
    three.run(
        "(= (petta-write-then-raise) (progn (superpose ("
        "(add-atom (context-space) (lost 1)) (add-atom (context-space) (lost 2)))) "
        "(petta-blow)))"
    )
    with pytest.raises(EngineError):
        three.run("!(collapse (transaction (petta-write-then-raise)))")
    assert _answers(three, "!(collapse (match (context-space) (lost $x) $x))") == []


def test_a_nested_transaction_preserves_answers_too(three):
    """The nested branch runs inside the outer transaction's registry rather
    than opening its own, and it collects and replays for the same reason the
    outer one does: SWI's transaction/1 is once-like at every depth."""
    assert _answers(
        three, "!(collapse (transaction (transaction (superpose (7 8)))))"
    ) == ["7", "8"]
    assert _answers(three, "!(collapse (transaction (transaction (petta-three))))") == [
        "1",
        "2",
        "3",
    ]
