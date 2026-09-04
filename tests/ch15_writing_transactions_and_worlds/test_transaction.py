"""Purpose: the Python door of the MeTTa (transaction ...) form:
m.transaction runs a callable inside one engine transaction now, and
m.transactional is its decorator twin.
Guarantees:
  - a raise inside the callable rolls back stored atoms AND compiled
    equations, and re-raises the caller's own exception class [tested
    test_a_raise_rolls_back_everything_and_arrives_as_itself]
  - an inner transaction's commit is relative to its outer transaction
    [tested test_nested_commit_dies_with_the_outer_rollback]
  - subscription events are published in write order only after the owning
    transaction commits, and are discarded with rollback or speculation
    [tested: test_events_publish_only_after_transaction_commit,
    test_atomic_scope_commits_or_discards_one_event_segment,
    test_event_folds_observe_only_the_post_commit_stream,
    test_rollback_and_outer_rollback_discard_every_buffered_event,
    test_speculative_execution_discards_its_event_segment; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import G, S, V, parse
from metta.errors import EngineError, MettaResultError


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


def test_commit_answers_the_callables_return_value(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def work():
        m.add(S.tx(1))
        return {"rows": [1, "two"]}

    assert m.transaction(work) == {"rows": [1, "two"]}
    assert m.atoms() == [S.tx(1)]
    assert m.transaction(lambda: None) is None


def test_return_values_keep_identity(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    marker = object()
    assert m.transaction(lambda: marker) is marker


def test_a_raise_rolls_back_everything_and_arrives_as_itself(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def failing():
        m.add(S.tx(2))
        m.run("(= (tx-f $x) $x)")
        msg = "undo everything"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="undo everything") as failure:
        m.transaction(failing)
    # The chain keeps the boundary visible rather than hiding it.
    assert type(failure.value.__cause__).__name__ == "EngineError"
    assert m.atoms() == []
    # The equation's compiled clauses rolled back with its atom.
    assert m.is_function("tx-f") is False
    assert m.run("!(tx-f 3)") == [[m.parse("(tx-f 3)")]]


def test_the_librarys_own_errors_pass_through_unchanged(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run('(= (tx-err) (Error (tx-err) "boom"))')

    def body():
        m._one("(tx-err)")

    with pytest.raises(MettaResultError):
        m.transaction(body)
    # The handle stays fully usable after the rollback; the equation was
    # added OUTSIDE the transaction, so it rightly survives.
    m.add(S.tx(9))
    assert S.tx(9) in m


def test_nested_commit_dies_with_the_outer_rollback(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def outer():
        m.transaction(lambda: m.add(S.tx(3)))
        msg = "outer dies"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError):
        m.transaction(outer)
    assert m.atoms() == []
    # And a nested transaction under a COMMITTING outer commits.
    m.transaction(lambda: m.transaction(lambda: m.add(S.tx(4))))
    assert m.atoms() == [S.tx(4)]


def test_transactional_is_the_decorator_twin(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.transactional
    def migrate(n):
        m.add(S.tx(n))
        if n < 0:
            msg = "negative"
            raise ValueError(msg)
        return n * 2

    # Decorating ran nothing; calling runs one transaction per call.
    assert m.atoms() == []
    assert migrate(5) == 10
    assert m.atoms() == [S.tx(5)]
    with pytest.raises(ValueError):
        migrate(-1)
    assert m.atoms() == [S.tx(5)]  # the failing call's write rolled back
    assert migrate.__name__ == "migrate"  # functools.wraps preserved it


def test_atomic_and_speculative_scopes_refuse_to_compose(m):
    """One commits each call whole, the other discards its writes.

    The two policies contradict, so entering the second scope refuses by
    name at the door, before any call could run under both.
    """
    with m.atomic():
        with pytest.raises(ValueError, match="exclusive"), m.speculative():
            m.run("(tx-both fact) !(+ 1 1)")
    with m.speculative():
        with pytest.raises(ValueError, match="exclusive"), m.atomic():
            m.run("(tx-both fact) !(+ 1 1)")
    assert m.atoms() == []


def test_events_publish_only_after_transaction_commit(m):
    """The observer sees one ordered committed report, never tentative rows."""
    seen = []
    inside = []
    subscription = m.subscribe(S.tx(V.n), seen.append)
    try:
        def work():
            m.add(S.tx(10), S.tx(11))
            inside.append([event.atom for event in seen])

        m.transaction(work)
        assert inside == [[]]
        assert [event.atom for event in seen] == [S.tx(10), S.tx(11)]
    finally:
        subscription.cancel()


def test_atomic_scope_commits_or_discards_one_event_segment(m):
    """Atomic callbacks see the complete commit and no failed-run residue."""
    seen = []
    snapshots = []
    subscription = m.subscribe(
        S.atomic_event(V.n),
        lambda event: (seen.append(event), snapshots.append(m.atoms())),
    )
    try:
        with pytest.raises(EngineError):
            with m.atomic():
                m.run("(atomic-event 1) !(+ $left $right)")
        assert seen == []
        assert S.atomic_event(1) not in m

        with m.atomic():
            m.run("(atomic-event 2) (atomic-event 3) !(+ 1 1)")
        assert [event.atom for event in seen] == [
            S.atomic_event(2),
            S.atomic_event(3),
        ]
        assert snapshots == [
            [S.atomic_event(2), S.atomic_event(3)],
            [S.atomic_event(2), S.atomic_event(3)],
        ]
    finally:
        subscription.cancel()


def test_event_folds_observe_only_the_post_commit_stream(m):
    """A fold advances after commit and never advances for a rolled-back diff."""
    fold = m.events().fold(
        lambda held, event: [*held, event.atom],
        space=m.name,
        pattern=S.folded(V.n),
        state=[],
    )
    try:
        def committed():
            m.add(S.folded(1), S.folded(2))
            assert fold.state == []

        m.transaction(committed)
        assert fold.state == [S.folded(1), S.folded(2)]

        def rolled_back():
            m.add(S.folded(3))
            assert fold.state == [S.folded(1), S.folded(2)]
            msg = "discard folded write"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="discard folded write"):
            m.transaction(rolled_back)
        assert fold.state == [S.folded(1), S.folded(2)]
    finally:
        fold.cancel()


def test_rollback_and_outer_rollback_discard_every_buffered_event(m):
    """A savepoint report joins its parent and dies if that parent rolls back."""
    seen = []
    subscription = m.subscribe(S.tx(V.n), seen.append)
    try:
        def outer():
            m.add(S.tx(20))
            m.transaction(lambda: m.add(S.tx(21)))
            assert seen == []
            msg = "discard the outer transaction"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="discard the outer transaction"):
            m.transaction(outer)
        assert seen == []
        assert S.tx(20) not in m
        assert S.tx(21) not in m
    finally:
        subscription.cancel()


def test_speculative_execution_discards_its_event_segment(m):
    """A successful what-if returns answers but publishes no change report."""
    seen = []
    subscription = m.subscribe(S.tx(V.n), seen.append)
    try:
        with m.speculative():
            assert m.run("(tx 30) !(+ 1 1)") == [[2]]
            assert seen == []
        assert seen == []
        assert S.tx(30) not in m
    finally:
        subscription.cancel()


def test_a_rolled_back_registration_leaves_no_registry_claiming_it(m):
    """The library's own mirror of engine state rolls back with the engine.

    transaction() says Python-side state is the caller's to undo, and that is
    right for a list appended or a file written. The operation registry is not
    that: it is the library's mirror of engine state, and a rolled-back
    registration left it claiming an operation the engine had forgotten.
    `registered()` answered True while the reflection rows and the type
    declarations were gone and the call no longer reduced, so an installer's
    own "already installed" check skipped reinstalling a name that was dead for
    the life of the process.
    """
    import importlib

    ops = importlib.import_module("metta.ops")

    def install():
        @m.op(effect="pureStructural")
        def rolled_back_op(value: int) -> int:
            return value * 10

        m.add(parse("(installed marker)"))
        message = "injected failure"
        raise RuntimeError(message)

    with pytest.raises(RuntimeError):
        m.transaction(install)

    # All three readings agree, which is the property that was broken: the
    # registry, the space and the engine's own answer.
    assert "rolled-back-op" not in ops.registered()
    assert not any("installed" in str(atom) for atom in m.atoms())
    assert m.run("!(rolled-back-op 4)") == [[parse("(rolled-back-op 4)")]]

    # A registration the transaction REPLACED comes back as it was, rather
    # than being dropped along with the one that replaced it.
    @m.op(effect="pureStructural")
    def shadowed(value: int) -> int:
        return value + 1

    def replace():
        @m.op(effect="pureStructural", name="shadowed")
        def louder(value: int) -> int:
            return value + 1000

        message = "injected failure"
        raise RuntimeError(message)

    try:
        with pytest.raises(RuntimeError):
            m.transaction(replace)
        assert m.run("!(shadowed 4)") == [[G(5)]]
    finally:
        m.unregister_op("shadowed")


def test_an_inner_registration_dies_with_the_outer_rollback(m):
    """Nesting follows SWI's rule: an inner commit is relative to its outer."""
    import importlib

    ops = importlib.import_module("metta.ops")

    def inner():
        @m.op(effect="pureStructural")
        def inner_op(value: int) -> int:
            return value

        return 1

    def outer():
        m.transaction(inner)
        message = "outer failure"
        raise RuntimeError(message)

    with pytest.raises(RuntimeError):
        m.transaction(outer)

    assert "inner-op" not in ops.registered()
