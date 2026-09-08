"""Purpose: prove that Python projects lib_thread scope ownership and joins.

Owns resources: scopes release their children; fixtures drop borrowed spaces
and unregister their test operations [tested: test_scopes.py; commit=WORKTREE].
"""

# ruff: noqa: D103 -- pytest names state each fixture and behavioral contract

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from random import Random

import pytest

import metta
from metta import S, Space
from metta import _scope as scope_context
from metta import aio as aio_module
from metta.aio import AsyncMeTTa
from metta.errors import MettaError
from metta.foreign import SpaceProvider
from metta.parallel import EnginePool, ProcessPool, program


@pytest.fixture
def native_ops():
    with metta.MeTTa() as m:
        m.register_prolog("""
            :- metta_extension(sc_scope_tests, [version('1')]).
            :- metta_export("(: sc-test-loop (-> %Undefined%))").
            :- metta_export("(: sc-test-error (-> %Undefined%))").
            'sc-test-loop'(_) :- repeat, fail.
            'sc-test-error'(_) :- throw(error(scope_test_failure, context(test, child))).
        """)
        try:
            yield m
        finally:
            m.unregister_prolog("sc_scope_tests")


def test_scope_releases_mints_and_refuses_every_alias():
    with metta.scope():
        child = metta.space()
        child.add(S.owned(1))
        alias = Space(child)
        name = str(child.name)
    assert child.dropped
    assert alias.dropped
    for handle in (child, alias, Space(name)):
        with pytest.raises(MettaError, match=r"dropped|released_scope_space"):
            handle.atoms()
    assert name not in metta.engine().self.space_names()


def test_keep_transfers_to_the_parent_and_borrowed_spaces_survive():
    with metta.space() as borrowed:
        with metta.scope():
            with metta.scope() as inner:
                child = inner.keep(metta.space())
                child.add(S.owned(1))
                borrowed.add(S.borrowed(2))
            assert child.atoms() == [S.owned(1)]
        assert child.dropped
        assert borrowed.atoms() == [S.borrowed(2)]
        with metta.scope() as outer:
            returned = outer.keep(metta.space())
        try:
            returned.add(S.retained(3))
            assert returned.atoms() == [S.retained(3)]
        finally:
            returned.drop()


def test_channel_and_space_operations_share_one_fifo():
    with metta.channel(max=3) as channel:
        assert isinstance(channel, Space)
        channel.send(S.item(1))
        channel.add(S.item(2))
        channel.send(S.item(1))
        assert channel.atoms() == [S.item(1), S.item(2), S.item(1)]
        assert channel.remove(S.item(2))
        assert len(channel) == 2
        assert channel.recv() == S.item(1)
        assert channel.try_recv() == S.item(1)
        assert channel.try_recv() is None


def test_scope_joins_three_children_before_releasing_their_spaces():
    with metta.space() as output:
        with metta.scope():
            children = [
                metta.spawn(S.progn(S.sleep(0.02), S.add_atom(output, S.finished(n))))
                for n in range(3)
            ]
        assert sorted(int(row.n) for row in output.match(S.finished(metta.V.n))) == [0, 1, 2]
        assert all(child.dropped for child in children)


def test_body_failure_cancels_a_pending_timer_and_releases_its_channel():
    with pytest.raises(ValueError, match="body failed"), metta.scope():
        future = metta.every(100, S.unreachable())
        channel = metta.channel()
        message = "body failed"
        raise ValueError(message)
    assert future.dropped
    assert channel.dropped


def test_scope_owns_an_executor_and_its_three_futures():
    with metta.scope():
        pool = EnginePool(3)
        futures = [pool.submit(lambda n: (time.sleep(0.02), n)[1], n) for n in range(3)]
    assert pool.closed
    assert all(not worker.is_alive() for worker in pool._started)
    assert [future.result() for future in futures] == [0, 1, 2]


def test_executor_failure_cancels_its_engine_sibling(native_ops):
    m = native_ops
    with m.self:
        with pytest.raises(ValueError, match="child failed"), m.scope():
            pool = EnginePool(2)
            sibling = pool.submit(m.eval, "(sc-test-loop)")

            def fail():
                message = "child failed"
                raise ValueError(message)

            pool.submit(fail)
        assert sibling.done()
        assert pool.closed


def test_deadline_uses_the_library_scope_and_stops_a_running_engine(native_ops):
    m = native_ops
    with m.self:
        with metta.move_on_after(0.02) as scope:
            m.eval("(sc-test-loop)")
        assert scope.cancelled
        assert m.eval("(+ 2 3)") == [5]


def test_scope_closes_subscriptions_on_borrowed_spaces():
    with metta.space() as borrowed:
        seen = []
        with metta.scope():
            subscription = borrowed.subscribe(metta.V.x, seen.append)
            borrowed.add(S.item(1))
        borrowed.add(S.item(2))
        assert len(seen) == 1
        subscription.cancel()


@pytest.mark.parametrize("started", [False, True])
def test_scope_closes_held_debuggers_and_retires_their_wrappers(started):
    with metta.space() as home:
        home.run("(= (sc-debug-double $x) (* 2 $x))")
        with metta.scope():
            session = home.debug(S['sc-debug-double'](3), on="sc-debug-double")
            if started:
                next(session)
        try:
            with pytest.raises(MettaError, match="closed"):
                next(session)
            with home.debug(S['sc-debug-double'](4)) as later:
                assert later.run() == [[8]]
        finally:
            session.close()


def test_scope_owner_confines_keep_and_close():
    errors = []
    with metta.scope() as scope:
        def foreign_owner():
            for action in (scope.close, lambda: scope.keep(1)):
                try:
                    action()
                except MettaError as error:
                    errors.append(str(error))

        worker = threading.Thread(target=foreign_owner)
        worker.start()
        worker.join()
    assert len(errors) == 2
    assert all("scope_owner" in error for error in errors)


@pytest.mark.parametrize("kind", ["state", "lifetime"])
def test_scope_readers_cannot_observe_a_writers_record_replacement(kind):
    with metta.scope() as scope:
        space = metta.space()
        with scope_context.suspend():
            row = space.runtime.must(
                "(Kind==state -> _Key=Id, _Row=state(_,_,_,_), "
                "_Read=lib_thread:scope_state_(Id,_,_,_,_); "
                "lib_thread:scope_space_key_(Name,_Key), _Row=lifetime(_,_), "
                "_Read=lib_thread:scope_space_owner_(Name,_,_)), "
                "setup_call_cleanup(message_queue_create(_Ready), "
                "(thread_create(with_mutex('$metta_scopes', "
                "setup_call_cleanup((recorded(_Key,_Row,_Ref), erase(_Ref)), "
                "(thread_send_message(_Ready,gap), sleep(0.1)), "
                "recorda(_Key,_Row,_))), _Writer, []), "
                "thread_get_message(_Ready,gap), "
                "(call(_Read) -> Observed=present; Observed=missing), "
                "thread_join(_Writer,true)), message_queue_destroy(_Ready))",
                Kind=kind, Id=scope._id, Name=space.name,
            )
        assert row["Observed"] == "present"


def test_a_cancel_refusal_does_not_skip_later_siblings(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def waiting():
        started.set()
        release.wait()

    with EnginePool(1) as pool, metta.scope() as scope:
        running = pool.submit(waiting)
        assert started.wait(10)
        queued = pool.submit(lambda: 7)

        def refuse():
            message = "executor cancel refused"
            raise RuntimeError(message)

        try:
            with monkeypatch.context() as patch:
                patch.setattr(running, "cancel", refuse)
                with pytest.raises(MettaError, match="executor cancel refused"):
                    scope.cancel()
                assert queued.cancelled()
        finally:
            release.set()


def test_host_failure_publishes_completion_when_a_sibling_refuses_cancel():
    refusing = True
    receipt = False

    def cancel(_scope_id):
        if refusing:
            message = "host signal refused"
            raise RuntimeError(message)

    with pytest.raises(BaseExceptionGroup) as failures:
        with metta.scope() as scope:
            waiting = scope_context.own("future", cancel)
            finished = scope_context.own("future", lambda _scope_id: None)
            assert waiting is not None and finished is not None
            rt = scope._home.runtime

            def has_receipt():
                with scope_context.suspend():
                    return bool(rt.once(
                        "recorded(Token, queue(_Queue), _), "
                        "message_queue_property(_Queue, size(1))", Token=finished,
                    ))

            try:
                scope_context.finished(finished, ValueError("host child failed"))
                receipt = has_receipt()
            finally:
                refusing = False
                scope_context.finished(waiting)
                # The negative control must also release its held receipt.
                if not has_receipt():
                    scope_context.finished(finished)
    assert receipt
    assert any("host child failed" in str(error) for error in failures.value.exceptions)
    assert any("host signal refused" in str(error) for error in failures.value.exceptions)


def test_normal_exit_stops_a_repeating_timer():
    with metta.scope():
        timer = metta.every(100, S.unreachable())
    assert timer.dropped


def test_a_repeating_child_failure_stops_the_scope(native_ops):
    with native_ops.self, pytest.raises(MettaError, match="scope_test_failure"):
        with native_ops.scope():
            timer = metta.every(0.001, S['sc-test-error']())
            list(timer.wait())
    assert timer.dropped


def test_a_borrowed_executor_survives_its_scoped_submission():
    with EnginePool(1) as pool:
        with metta.scope():
            future = pool.submit(lambda: (time.sleep(0.01), 42)[1])
        assert future.result() == 42
        assert not pool.closed
        assert pool.submit(lambda: 7).result() == 7


def test_scope_releases_a_partly_consumed_host_engine():
    with metta.space() as space:
        space.add(*(S.item(n) for n in range(3)))
        with metta.scope():
            unopened = space.stream(S.item(metta.V.n))
            opened = space.stream(S.item(metta.V.n))
            assert next(opened).n == 0
        try:
            with pytest.raises(MettaError):
                next(opened)
            # A query plan has no engine until its first pull.
            assert [row.n for row in unopened] == [0, 1, 2]
        finally:
            opened.close()
            unopened.close()


def test_scoped_async_publication_refuses_inside_a_transaction():
    with metta.space() as space, metta.scope():
        with pytest.raises(MettaError, match="scope_in_transaction"):
            space.transaction(lambda: metta.spawn(S['+'](1, 2)))


def test_a_rolled_back_allocation_still_belongs_to_its_scope():
    with metta.space() as borrowed:
        children = []

        def rollback():
            child = metta.space()
            children.append(child)
            child.add(S.transient(1))
            message = "rollback"
            raise ValueError(message)

        with metta.scope():
            with pytest.raises(ValueError, match="rollback"):
                borrowed.transaction(rollback)
        assert children[0].dropped


def test_a_rolled_back_allocation_cannot_recycle_a_revoked_name():
    with metta.space() as borrowed:
        children = []

        def rollback():
            children.append(metta.space())
            message = "rollback"
            raise ValueError(message)

        # Rollback can restore both the name counter and an old pool entry.
        with metta.scope():
            with pytest.raises(ValueError, match="rollback"):
                borrowed.transaction(rollback)
            name = children[0].name
        with metta.space() as later:
            assert later.name != name
            later.add(S.item(1))
            assert later.atoms() == [S.item(1)]


def test_alias_drop_releases_the_creating_handles_owned_journal(tmp_path):
    path = tmp_path / "owned.db"
    with metta.scope():
        child = metta.space(journal=path, schema={"item": 1})
        child.add(S.item(9))
        alias = Space(child)
        alias.drop()
        assert child.dropped and alias.dropped
        with metta.space(journal=path, schema={"item": 1}) as reopened:
            assert reopened.atoms() == [S.item(9)]


def test_cleanup_failure_revokes_aliases_attempts_all_and_can_retry(tmp_path, monkeypatch):
    scope = metta.scope()
    path = tmp_path / "retry.db"
    with pytest.raises(MettaError, match="scope cleanup failed"), scope:
        retained = scope.keep(metta.space())
        journal = metta.space(journal=path, schema={"item": 1})
        alias = Space(journal)
        original = type(journal._backing).close
        attempts = []

        def fail_once(backing):
            if backing is journal._backing:
                attempts.append(True)
                if len(attempts) == 1:
                    message = "scope cleanup failed"
                    raise OSError(message)
            original(backing)

        monkeypatch.setattr(type(journal._backing), "close", fail_once)
    assert retained.dropped
    assert alias.dropped
    with pytest.raises(MettaError, match="released_scope_space"):
        alias.add(S.item(1))
    scope.close()
    assert len(attempts) == 2
    with metta.space(journal=path, schema={"item": 1}):
        pass


def test_named_foreign_creation_is_owned_and_an_existing_provider_is_borrowed():
    class Provider(SpaceProvider):
        def atoms(self):
            return [S.item(3)]

    provider = Provider()
    with metta.scope():
        owned = metta.space(S.sc_owned_provider, backing=provider)
    assert owned.dropped
    assert provider.atoms() == [S.item(3)]
    borrowed = metta.space(S.sc_borrowed_provider, backing=provider)
    try:
        with metta.scope():
            assert Space(borrowed).atoms() == [S.item(3)]
        assert borrowed.atoms() == [S.item(3)]
    finally:
        borrowed.drop()


def test_scope_owns_a_process_pool_and_joins_its_results():
    with metta.scope():
        pool = ProcessPool(2)
        futures = [pool.submit(program, f"!(+ {n} 1)") for n in range(3)]
    assert pool.closed
    assert [future.result() for future in futures] == [[[1]], [[2]], [[3]]]


def test_explicit_cancellation_is_consumed_by_its_own_scope():
    reached = []
    with metta.scope() as scope:
        scope.cancel()
        metta.eval(S['+'](1, 2))
        reached.append(True)
    assert scope.cancelled
    assert reached == []
    assert metta.eval(S['+'](2, 3)) == [5]


def test_an_outer_deadline_is_not_lost_at_a_nested_scope(native_ops):
    with native_ops.self, metta.move_on_after(0.02) as outer:
        with metta.scope():
            native_ops.eval("(sc-test-loop)")
        native_ops.eval("(+ 1 2)")
    assert outer.cancelled


def test_async_cancellation_waits_for_the_coroutines_finalizer():
    entered = threading.Event()
    finalized = threading.Event()

    async def work() -> int:
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0.02)
            finalized.set()
        return 1

    with metta.MeTTa() as m:
        m.op(work, name="sc-async-finalizer", effect="oracleIO")
        try:
            with m.scope():
                future = m.eval(S['sc-async-finalizer']())[0]
                assert entered.wait(10)
                assert future.cancel() is True
                assert finalized.is_set()
            assert future.dropped
        finally:
            m.unregister_op("sc-async-finalizer")


def test_a_refused_coroutine_signal_does_not_claim_a_stopped_body(monkeypatch):
    entered = threading.Event()
    finalized = threading.Event()
    tasks = []

    async def work() -> int:
        tasks.append(asyncio.current_task())
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            finalized.set()
        return 1

    with metta.MeTTa() as m:
        m.op(work, name="sc-refused-signal", effect="oracleIO")
        future = m.eval(S['sc-refused-signal']())[0]
        assert entered.wait(10)
        task = tasks[0]
        loop = task.get_loop()
        original = loop.call_soon_threadsafe

        def refuse(callback, *args, **kwargs):
            if callback == task.cancel:
                message = "coroutine signal refused"
                raise RuntimeError(message)
            return original(callback, *args, **kwargs)

        try:
            with monkeypatch.context() as patch:
                patch.setattr(loop, "call_soon_threadsafe", refuse)
                with pytest.raises(MettaError, match="coroutine signal refused"):
                    future.cancel()
            assert not finalized.is_set()
        finally:
            original(task.cancel)
            assert finalized.wait(10)
            list(future.wait())
            future.drop()
            m.unregister_op("sc-refused-signal")


def test_scope_waits_for_async_landing_observers_and_owns_their_mints():
    observed = threading.Event()
    finished = threading.Event()
    minted = []

    async def answer() -> int:
        await asyncio.sleep(0.01)
        return 7

    def landing(_event):
        observed.set()
        time.sleep(0.02)
        minted.append(metta.space())
        finished.set()

    with metta.MeTTa() as m:
        m.op(answer, name="sc-async-observer", effect="oracleIO")
        try:
            with m.scope():
                metta.space("&metta").subscribe(
                    S['async-op'](S['sc-async-observer'], metta.V.space, S.landing),
                    landing,
                )
                future = m.eval(S['sc-async-observer']())[0]
            assert observed.is_set() and finished.is_set()
            assert future.dropped and minted[0].dropped
        finally:
            m.unregister_op("sc-async-observer")


def test_scope_owns_an_async_worker_and_its_requests():
    async def check():
        with metta.scope():
            am = await AsyncMeTTa().start()
            child = await am.space()
            await child.add(S.item(7))
            assert await child.atoms() == [S.item(7)]
        assert am._worker.state == "closed"
        assert not am._worker.thread.is_alive()
        assert child.dropped

    asyncio.run(check())


def test_scope_joins_a_cancelled_request_on_a_borrowed_async_worker():
    entered = threading.Event()
    finished = threading.Event()

    def foreign_call(_m):
        entered.set()
        time.sleep(0.05)
        finished.set()

    async def check():
        async with AsyncMeTTa() as am:
            with metta.scope():
                task = asyncio.create_task(am.call(foreign_call))
                await asyncio.to_thread(entered.wait)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            assert finished.is_set()
            assert await am.eval(S['+'](2, 3)) == [5]

    asyncio.run(check())


def test_a_scope_deadline_wakes_the_task_awaiting_an_async_worker(native_ops):
    async def check():
        async with AsyncMeTTa(metta=native_ops.self) as am:
            with metta.move_on_after(0.02) as scope:
                await am.eval("(sc-test-loop)")
            assert scope.cancelled
            assert await am.eval("(+ 2 3)") == [5]

    asyncio.run(check())


def test_async_subscription_stop_needs_only_the_workers_acquisition_receipt(monkeypatch):
    async def check():
        acquired = asyncio.Event()
        release = asyncio.Event()
        stopped = threading.Event()
        original = aio_module._acquire

        async def delay_publication(work, undo):
            result = await original(work, undo)
            acquired.set()
            await release.wait()
            return result

        monkeypatch.setattr(aio_module, "_acquire", delay_publication)
        async with AsyncMeTTa() as am:
            stream = am.subscribe(metta.V.anything)
            opening = asyncio.create_task(stream._ensure())
            await acquired.wait()

            def stop():
                stream._stop()
                stopped.set()

            closer = threading.Thread(target=stop)
            closer.start()
            independent = stopped.wait(1)
            release.set()
            await asyncio.gather(opening, return_exceptions=True)
            await asyncio.to_thread(closer.join)
            assert independent, "subscription stop waited for the event-loop continuation"

    asyncio.run(check())


def test_scope_closes_an_async_subscription_on_a_borrowed_worker():
    async def check():
        async with AsyncMeTTa() as am:
            with metta.scope():
                stream = am.subscribe(metta.V.anything)
                await stream._ensure()
                waiting = asyncio.create_task(anext(stream))
                await asyncio.sleep(0)
            with pytest.raises(StopAsyncIteration):
                await waiting
            assert not am._subscriptions
            assert await am.eval("(+ 2 3)") == [5]

    asyncio.run(check())


@pytest.mark.parametrize("capacity", [1, 2, 7])
def test_channel_space_and_mailbox_share_a_randomized_bag_and_fifo(capacity):
    rng = Random(430)
    model = deque()
    with metta.channel(max=capacity) as channel:
        for _ in range(80):
            action = rng.randrange(4)
            atom = S.item(rng.randrange(4))
            if action < 2 and len(model) < capacity:
                (channel.send if action == 0 else channel.add)(atom)
                model.append(atom)
            elif action == 2:
                actual = channel.try_recv()
                assert actual == (model.popleft() if model else None)
            else:
                removed = atom in model
                assert bool(channel.remove(atom)) == removed
                if removed:
                    model.remove(atom)
            assert channel.atoms() == list(model)
            assert len(channel) == len(model)
