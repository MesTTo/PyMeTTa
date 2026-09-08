"""Purpose: verify evaluation options across the asynchronous worker boundary.

Guarantees: lazy selections keep their demand, replay, caller rows and cleanup
  on the owner thread [tested: this file; commit=WORKTREE].
Owns resources: every test closes its engine context and worker. Blocking
  probes are released in finally blocks, including failed assertions.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from metta import G, MeTTa, S, Space, Undefined, V, aio, equation
from metta.errors import (
    AssertionFailure,
    EngineError,
    InferenceLimitError,
    MettaError,
    TimeLimitError,
)
from metta.results import Answers, Rows, _AnswerItem


@pytest.mark.parametrize("answer", ("all", "atom", "one", "first", "count", "exists", "none", "rows", "answers", "stream"))
def test_async_evaluation_options_reach_the_same_engine_choices(answer):
    """Async evaluation options reach the same engine choices."""
    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            scalar = answer in ("one", "atom")
            target = "(+ 1 2)" if scalar else "(superpose (3 3 4))"
            delivery = "atoms" if answer == "atom" else "values"
            result = await owner.eval(target, answer=answer, delivery=delivery, limit=2)
            if answer in ("answers", "stream"):
                async with result:
                    assert [value async for value in result] == [3, 3]
            elif answer == "rows":
                assert result.to_dicts() == [{"value": 3}, {"value": 3}]
            else:
                expected = {"all": [3, 3], "atom": G(3), "one": 3, "first": 3,
                            "count": 2, "exists": True, "none": None}
                assert result == expected[answer]
            assert not owner._subscriptions

    with MeTTa() as context:
        asyncio.run(run(context.self))


@pytest.mark.parametrize("answer", ("all", "answers", "stream"))
def test_async_evaluation_preserves_algebra_theory_interpreter_and_truth(answer):
    """Async evaluation preserves algebra theory interpreter and truth."""
    laws = (equation(S.async_door_choice()).to(S.left), equation(S.async_door_choice()).to(S.right))

    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            async def collect(target, **options):
                result = await owner.eval(target, answer=answer, **options)
                if answer == "all":
                    return result
                async with result:
                    return [value async for value in result]

            names = await owner.space_names()
            assert await collect(S.async_door_choice(), theory=laws, interpreter=S.async_door_eval, limit=1) == [S.Seen(S.left)]
            assert await owner.space_names() == names
            assert await owner.eval(S.async_door_choice()) == [S.base]
            annotated = await collect(S.async_door_tagged(V.value), under="async-door-product", limit=1)
            assert len(annotated) == 1
            assert annotated[0].annotation == 7
            assert annotated[0].value == S.async_door_tagged(S.yes)
            truth = await collect("(translatePredicate (async_door_wfs))", limit=1)
            assert len(truth) == 1 and isinstance(truth[0], Undefined)
            assert "async_door_wfs" in truth[0].why
            with owner.capture() as captured:
                assert await collect('(progn (println! "async door") 7)', delivery="values", limit=1) == [7]
            assert captured.text == '"async door"\n'
            assert not owner._subscriptions

    with MeTTa() as context:
        space = context.self
        space.add(equation(S.async_door_choice()).to(S.base))
        space.run("(: async-door-eval (-> Atom Atom Atom %Undefined%)) (= (async-door-eval $t $ty $s) (Seen (metta $t $ty $s)))")
        space.algebra("async-door-product", combine="+", extend="*", zero=0, one=1)
        space.add_tagged_fact(7, S.async_door_tagged(S.yes))
        space._rt._janus.consult("async_door_wfs.pl", data=":- table async_door_wfs/0.\nasync_door_wfs :- tnot(async_door_wfs).\n")
        asyncio.run(run(space))


@pytest.mark.parametrize("answer", ("all", "answers", "stream", "count"))
@pytest.mark.parametrize("bound,error", (({"timeout": 0.02}, TimeLimitError), ({"inferences": 200}, InferenceLimitError)))
def test_async_evaluation_bounds_preserve_control_refusals(answer, bound, error):
    """Async evaluation bounds preserve control refusals."""
    target = "(async-door-slow)" if "timeout" in bound else "(async-door-loop)"

    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            with pytest.raises(error):
                result = await owner.eval(target, answer=answer, on_error="empty", limit=1, **bound)
                if answer in {"answers", "stream"}:
                    async with result:
                        [value async for value in result]
            assert await owner.eval("(+ 20 22)") == [G(42)]
            assert not owner._subscriptions

    with MeTTa() as context:
        context.self.run("(= (async-door-loop) (async-door-loop))")

        @context.self.io(name="async-door-slow")
        def slow() -> int:
            time.sleep(0.04)
            return 7

        try:
            asyncio.run(run(context.self))
        finally:
            context.unregister_op("async-door-slow")


class Source:
    """A finite source whose pulls and closes expose their actual thread."""

    def __init__(self, *, fail_close=0, hold_pull=False):
        """Allocate controls that the test releases before shutdown."""
        self.values = iter((3, 4, 5))
        self.calls = []
        self.fail_close = fail_close
        self.closed = False
        self.started = threading.Event()
        self.release = threading.Event()
        if not hold_pull:
            self.release.set()

    def __iter__(self):
        """Iterate this single source."""
        return self

    def __next__(self):
        """Wait for release and record the worker that demanded an answer."""
        if self.closed:
            raise StopIteration
        self.calls.append(("next", threading.get_ident()))
        self.started.set()
        self.release.wait()
        value = next(self.values)
        row = Rows(("x",), ((G(value),),)).one()
        return _AnswerItem(G(value), row)

    def close(self):
        """Record the closing worker and fail the requested number of times."""
        if self.closed:
            return
        self.calls.append(("close", threading.get_ident()))
        if self.fail_close:
            self.fail_close -= 1
            msg = "async evaluation close failed"
            raise RuntimeError(msg)
        self.closed = True


def _install_source(monkeypatch, source):
    monkeypatch.setattr(Space, "_door_answers", lambda *_args, **_kwargs: Answers(source, columns=("x",)))


@pytest.mark.parametrize("answer", ("answers", "stream"))
def test_async_evaluation_choices_preserve_demand_and_replay(monkeypatch, answer):
    """Async evaluation choices preserve demand and replay."""
    source = Source()
    _install_source(monkeypatch, source)

    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            view = await owner.eval(S.fact(V.x), answer=answer, delivery="values")
            assert not source.calls
            iterator = aiter(view)
            assert await anext(iterator) == 3
            assert len(source.calls) == 1
            expected = [3, 4, 5] if answer == "answers" else [4, 5]
            assert [value async for value in view] == expected
            expected = [3, 4, 5] if answer == "answers" else []
            assert [value async for value in view] == expected
            if answer == "answers":
                assert view.columns == ("x",)
                assert [row.x async for row in view.rows] == [G(3), G(4), G(5)]
            assert not owner._subscriptions
            assert [kind for kind, _thread in source.calls] == ["next"] * 4 + ["close"]
            assert {thread for _kind, thread in source.calls} == {owner._worker.thread.ident}
            await view.aclose()

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_concurrent_replays_share_one_source(monkeypatch):
    """Async evaluation concurrent replays share one source."""
    source = Source()
    _install_source(monkeypatch, source)

    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            view = await owner.eval(S.fact(V.x), answer="answers", delivery="values")

            async def collect():
                return [value async for value in view]

            assert await asyncio.gather(collect(), collect()) == [[3, 4, 5], [3, 4, 5]]
            assert sum(kind == "next" for kind, _ in source.calls) == 4
            assert sum(kind == "close" for kind, _ in source.calls) == 1

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_cleanup_is_owned_and_retryable(monkeypatch):
    """Async evaluation cleanup is owned and retryable."""
    source = Source(fail_close=1)
    _install_source(monkeypatch, source)

    async def run(space):
        owner = await aio.AsyncMeTTa(metta=space).start()
        try:
            view = await owner.eval(S.fact, answer="stream")
            assert len(owner._subscriptions) == 1
            with pytest.raises(RuntimeError, match="async evaluation close failed"):
                await view.aclose()
            assert len(owner._subscriptions) == 1
            await view.aclose()
            assert not owner._subscriptions
            replacement = Source()
            _install_source(monkeypatch, replacement)
            await owner.eval(S.fact, answer="stream")
        finally:
            await owner.aclose()
        assert not owner._subscriptions
        assert replacement.calls == [("close", owner._worker.thread.ident)]
        assert {thread for _kind, thread in source.calls} == {owner._worker.thread.ident}

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_parent_close_attempts_every_failed_batch_member(monkeypatch):
    """Async evaluation parent close attempts every failed batch member."""
    sources = [Source(fail_close=1), Source(fail_close=1)]
    monkeypatch.setattr(Space, "eval", lambda *_args, **_kwargs: [Answers(source) for source in sources])

    async def run(space):
        owner = await aio.AsyncMeTTa(metta=space).start()
        try:
            await owner.eval(S.first, S.second, answer="answers")
            with pytest.raises(ExceptionGroup):
                await owner.aclose()
            assert len(owner._subscriptions) == 1
            assert [len(source.calls) for source in sources] == [1, 1]
            assert not any(source.closed for source in sources)
        finally:
            await owner.aclose()
        assert all(source.closed for source in sources)
        assert not owner._subscriptions
        assert [len(source.calls) for source in sources] == [2, 2]
        assert all(thread == owner._worker.thread.ident for source in sources for _, thread in source.calls)

    with MeTTa() as context:
        asyncio.run(run(context.self))


@pytest.mark.parametrize("fail_close", (0, 1))
def test_async_evaluation_cancelled_batch_acquisition_keeps_cleanup_owned(monkeypatch, fail_close):
    """Async evaluation cancelled batch acquisition keeps cleanup owned."""
    sources = [Source(fail_close=fail_close), Source()]
    entered = threading.Event()
    release = threading.Event()

    def evaluate(_space, *_args, **_kwargs):
        entered.set()
        release.wait()
        return [Answers(source) for source in sources]

    monkeypatch.setattr(Space, "eval", evaluate)

    async def run(space):
        owner = await aio.AsyncMeTTa(metta=space).start()
        task = asyncio.create_task(owner.eval(S.a, S.b, answer="answers"))
        try:
            await asyncio.to_thread(entered.wait)
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert bool(owner._subscriptions) is bool(fail_close)
        finally:
            release.set()
            await owner.aclose()
        assert not owner._subscriptions
        assert [len(source.calls) for source in sources] == [1 + fail_close, 1]
        assert all(thread == owner._worker.thread.ident for source in sources for _, thread in source.calls)

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_cancelled_pull_closes_on_the_worker(monkeypatch):
    """Async evaluation cancelled pull closes on the worker."""
    source = Source(hold_pull=True)
    _install_source(monkeypatch, source)

    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            view = await owner.eval(S.fact, answer="stream")
            pulling = asyncio.create_task(anext(view))
            try:
                await asyncio.to_thread(source.started.wait)
                pulling.cancel()
                source.release.set()
                with pytest.raises(asyncio.CancelledError):
                    await pulling
                assert not owner._subscriptions
            finally:
                source.release.set()
                await view.aclose()
            assert source.calls[-1] == ("close", owner._worker.thread.ident)

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_parent_close_waits_for_batch_acquisition(monkeypatch):
    """Async evaluation parent close waits for batch acquisition."""
    source = Source()
    entered = threading.Event()
    release = threading.Event()

    def evaluate(_space, *_args, **_kwargs):
        entered.set()
        release.wait()
        return Answers(source)

    monkeypatch.setattr(Space, "eval", evaluate)

    async def run(space):
        owner = await aio.AsyncMeTTa(metta=space).start()
        acquiring = asyncio.create_task(owner.eval(S.fact, answer="answers"))
        closing = None
        try:
            await asyncio.to_thread(entered.wait)
            closing = asyncio.create_task(owner.aclose())
            await asyncio.sleep(0)
            release.set()
            view = await acquiring
            await closing
            assert not owner._subscriptions
            assert [value async for value in view] == []
        finally:
            release.set()
            if closing is not None:
                await closing
            elif not owner._closed:
                await owner.aclose()
        assert source.calls == [("close", owner._worker.thread.ident)]

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_binds_once_and_preserves_scalar_refusals():
    """Async evaluation binds once and preserves scalar refusals."""
    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            with owner.bind({S.a: S.b, S.b: S.c}):
                answers = await owner.eval(S.a, S.b, answer="answers")
            assert [[value async for value in view] for view in answers] == [[S.b], [S.c]]
            with pytest.raises(AssertionFailure):
                await owner.eval("(superpose (1 2))", answer="one", determinism="det")
            with pytest.raises(EngineError):
                await owner.eval("(empty)", answer="one")
            with pytest.raises(ValueError):
                await owner.eval("(+ 1 2)", delivery="invalid")

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_synchronous_stop_releases_on_the_worker(monkeypatch):
    """Async evaluation synchronous stop releases on the worker."""
    source = Source()
    _install_source(monkeypatch, source)

    async def acquire(space):
        owner = await aio.AsyncMeTTa(metta=space).start()
        view = await owner.eval(S.fact, answer="stream")
        with pytest.raises(MettaError, match="await aclose"):
            owner.stop()
        return owner, view

    with MeTTa() as context:
        owner, _view = asyncio.run(acquire(context.self))
        owner.stop()
        assert source.calls == [("close", owner._worker.thread.ident)]
        assert not owner._subscriptions


def test_async_evaluation_parent_cleanup_rejects_an_already_queued_write(monkeypatch):
    """Async evaluation parent cleanup rejects an already queued write."""
    source = Source(hold_pull=True)
    _install_source(monkeypatch, source)

    async def run(space):
        owner = await aio.AsyncMeTTa(metta=space).start()
        view = await owner.eval(S.fact, answer="stream", delivery="values")
        pulling = asyncio.create_task(anext(view))
        pending = None
        closing = None
        try:
            await asyncio.to_thread(source.started.wait)
            pending = asyncio.create_task(owner.add(S.after_parent_close))
            await asyncio.sleep(0)
            closing = asyncio.create_task(owner.aclose())
            await asyncio.sleep(0)
            source.release.set()
            assert await pulling == 3
            with pytest.raises(MettaError, match="closed before this request ran"):
                await pending
            await closing
            assert S.after_parent_close not in space
        finally:
            source.release.set()
            await asyncio.gather(*(task for task in (pulling, pending, closing) if task), return_exceptions=True)
            if not owner._closed:
                await owner.aclose()

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_borrower_cleanup_leaves_the_other_connection_running(monkeypatch):
    """Async evaluation borrower cleanup leaves the other connection running."""
    source = Source()
    _install_source(monkeypatch, source)
    entered = threading.Event()
    release = threading.Event()

    def work(space):
        entered.set()
        release.wait()
        return space.eval("(+ 20 22)")

    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            borrower = aio.AsyncMeTTa._sharing(space, owner._worker)
            await borrower.eval(S.fact, answer="stream")
            running = asyncio.create_task(owner.call(work))
            closing = None
            try:
                await asyncio.to_thread(entered.wait)
                closing = asyncio.create_task(borrower.aclose())
                await asyncio.sleep(0)
                release.set()
                assert await running == [G(42)]
                await closing
                assert owner._worker.thread.is_alive()
                assert source.calls == [("close", owner._worker.thread.ident)]
            finally:
                release.set()
                await asyncio.gather(*(task for task in (running, closing) if task), return_exceptions=True)
                if not borrower._closed:
                    await borrower.aclose()

    with MeTTa() as context:
        asyncio.run(run(context.self))


def test_async_evaluation_repeated_stops_share_one_transition_signal(monkeypatch):
    """Async evaluation repeated stops share one transition signal."""
    source = Source(hold_pull=True)
    _install_source(monkeypatch, source)

    async def run(space):
        async with aio.AsyncMeTTa(metta=space) as owner:
            view = await owner.eval(S.fact, answer="stream", delivery="values")
            pulling = asyncio.create_task(anext(view))
            try:
                await asyncio.to_thread(source.started.wait)
                assert owner.interrupt()
                assert not owner.interrupt()
                source.release.set()
                assert await pulling == 3
                assert await owner.eval("(+ 1 2)") == [G(3)]
            finally:
                source.release.set()
                await asyncio.gather(pulling, return_exceptions=True)
                await view.aclose()

    with MeTTa() as context:
        asyncio.run(run(context.self))
