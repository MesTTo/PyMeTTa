"""Purpose: the atomic forms answer everything their body answers and still
commit or roll back whole.
Guarantees:
  - a three-answer body inside a transaction answers three times, and every
    answer's writes land together [tested
    test_a_transaction_preserves_every_answer_of_its_body]
  - a body that ends with no answer rolls the whole transaction back, and one
    that raises rolls it back and re-raises [tested
    test_a_transaction_rolls_back_every_answers_writes_together]
  - `atomically` carries the same guarantees, over a body that may be a term
    the program computed [tested
    test_atomically_answers_in_full_and_commits_or_rolls_back_whole,
    test_atomically_takes_a_body_that_is_data_where_transaction_cannot]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta.errors import EngineError


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
    one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    space = metta._new_space()
    for answer in (1, 2, 3):
        space.run(f"(= (metta-three) {answer})")
    return space


def test_a_transaction_preserves_every_answer_of_its_body(three):
    """Reproduced 2026-08-19: `!(collapse (metta-three))` answered `(1 2 3)`
    and `!(collapse (transaction (metta-three)))` answered `(1)`. Two of the
    three answers were gone and nothing said so, because SWI's transaction/1
    runs its goal as once/1.

    Dropping them is an opacity violation in the transactional-memory sense:
    a reader of the result sees a state no serial run of the body produces.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert _answers(three, "!(collapse (metta-three))") == ["1", "2", "3"]
    assert _answers(three, "!(collapse (transaction (metta-three)))") == ["1", "2", "3"]
    # A superpose body is the same claim written without equations.
    assert _answers(three, "!(collapse (transaction (superpose (a b c))))") == [
        "a",
        "b",
        "c",
    ]
    # An answer that binds a caller variable replays its own binding rather
    # than a copy of whichever one came first.
    three.run("(= (metta-tag 1) one)")
    three.run("(= (metta-tag 2) two)")
    assert _answers(
        three, "!(collapse (transaction (metta-tag (superpose (1 2)))))"
    ) == ["one", "two"]


def test_a_transaction_rolls_back_every_answers_writes_together(three):
    """Preserving the answers must not cost the atomicity that is the form's
    reason to exist, so each half is checked with a body that answers more
    than once.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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
        "(= (metta-write-then-fail) (progn (superpose ("
        "(add-atom (context-space) (gone 1)) (add-atom (context-space) (gone 2)))) "
        "(empty)))"
    )
    assert _answers(three, "!(collapse (transaction (metta-write-then-fail)))") == []
    assert _answers(three, "!(collapse (match (context-space) (gone $x) $x))") == []

    # Two answers write and then the body raises: both writes go, and the
    # rollback does not swallow the exception.
    def blow():
        msg = "the host operation failed"
        raise RuntimeError(msg)

    three.op(blow, name="metta-blow", effect="pureStructural")
    three.run(
        "(= (metta-write-then-raise) (progn (superpose ("
        "(add-atom (context-space) (lost 1)) (add-atom (context-space) (lost 2)))) "
        "(metta-blow)))"
    )
    with pytest.raises(EngineError):
        three.run("!(collapse (transaction (metta-write-then-raise)))")
    assert _answers(three, "!(collapse (match (context-space) (lost $x) $x))") == []


def test_a_nested_transaction_preserves_answers_too(three):
    """The nested branch runs inside the outer transaction's registry rather
    than opening its own, and it collects and replays for the same reason the
    outer one does: SWI's transaction/1 is once-like at every depth.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert _answers(
        three, "!(collapse (transaction (transaction (superpose (7 8)))))"
    ) == ["7", "8"]
    assert _answers(three, "!(collapse (transaction (transaction (metta-three))))") == [
        "1",
        "2",
        "3",
    ]


def test_atomically_answers_in_full_and_commits_or_rolls_back_whole(three):
    """Reproduced 2026-08-19: `atomically` did not exist, so
    `!(atomically (+ 1 1))` answered `(atomically 2)`, the unknown head
    applied to its evaluated argument, rather than running anything
    atomically.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert [str(a) for a in three.run("!(atomically (+ 1 1))")[0]] == ["2"]
    assert _answers(three, "!(collapse (atomically (metta-three)))") == ["1", "2", "3"]

    # Commits whole.
    assert _answers(
        three,
        "!(collapse (atomically (superpose ((add-atom (context-space) (a-kept 1)) "
        "(add-atom (context-space) (a-kept 2))))))",
    ) == ["()", "()"]
    assert _answers(three, "!(collapse (match (context-space) (a-kept $x) $x))") == [
        "1",
        "2",
    ]

    # Rolls back whole.
    three.run(
        "(= (metta-a-fail) (progn (superpose ("
        "(add-atom (context-space) (a-gone 1)) (add-atom (context-space) (a-gone 2)))) "
        "(empty)))"
    )
    assert _answers(three, "!(collapse (atomically (metta-a-fail)))") == []
    assert _answers(three, "!(collapse (match (context-space) (a-gone $x) $x))") == []

    # A raise rolls back and is not swallowed.
    def blow():
        msg = "the host operation failed"
        raise RuntimeError(msg)

    three.op(blow, name="metta-a-blow", effect="pureStructural")
    three.run(
        "(= (metta-a-raise) (progn (superpose ("
        "(add-atom (context-space) (a-lost 1)) (add-atom (context-space) (a-lost 2)))) "
        "(metta-a-blow)))"
    )
    with pytest.raises(EngineError):
        three.run("!(collapse (atomically (metta-a-raise)))")
    assert _answers(three, "!(collapse (match (context-space) (a-lost $x) $x))") == []

    # Nesting keeps both, the same way transaction's does.
    assert _answers(
        three, "!(collapse (atomically (atomically (superpose (7 8)))))"
    ) == ["7", "8"]


def test_atomically_takes_a_body_that_is_data_where_transaction_cannot(three):
    """The two forms are not one operation wearing two names, and this is the
    difference. `transaction` is a special form: its body is compiled into the
    call site, so a variable there is a value rather than a goal and the term
    comes back unrun. `atomically` takes its body as an unreduced Atom and
    evaluates it, so the body may be a term the program computed.

    Measured 2026-08-19 over a three-answer body: 557.04 inferences plain,
    773.05 through `transaction`, 956.07 through `atomically`. The 183 that
    separate them are what evaluating a runtime term costs against compiling
    the body in place, which is why both forms exist rather than one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    three.run("(= (metta-body) (noeval (superpose ((+ 1 1) (+ 2 2)))))")
    assert _answers(
        three, "!(collapse (let $body (metta-body) (atomically $body)))"
    ) == ["2", "4"]
    assert _answers(
        three, "!(collapse (let $body (metta-body) (transaction $body)))"
    ) == ["(superpose ((+ 1 1) (+ 2 2)))"]
