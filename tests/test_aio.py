"""Purpose: the asyncio facade: the loop stays live while the engine
works, results and errors cross threads intact, bounds fire on the worker
thread, and spaces borrow the owner's engine thread.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import asyncio
import gc
import inspect
import logging

import pytest

from petta import S, V


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def test_aio_mirrors_the_surface(m):
    from petta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.add(S.edge(1, 2), S.edge(2, 3))
            rows = await am.query(S.edge(V.a, V.b), S.edge(V.b, V.c))
            groups = await am.run("!(+ 1 2)")
            value = await am.value("(+ 2 3)")
            count = await am.count()
            return rows, groups, value, count

    rows, groups, value, count = asyncio.run(go())
    assert [tuple(r) for r in rows] == [(1, 2, 3)]
    assert groups == [[3]] and value == 5 and count == 2


def test_aio_keeps_the_loop_live_while_the_engine_spins(m):
    from petta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin $n) (if (== $n 0) done (aio-spin (- $n 1))))"
            )
            ticks = 0

            async def ticker():
                nonlocal ticks
                while True:
                    await asyncio.sleep(0.005)
                    ticks += 1

            beat = asyncio.ensure_future(ticker())
            answers = await am.eval("(aio-spin 3000000)")
            beat.cancel()
            return ticks, answers

    ticks, answers = asyncio.run(go())
    assert answers == [S.done]
    # A blocked loop ticks zero times; the generous floor keeps slow
    # machines out of the assertion.
    assert ticks >= 3


def test_aio_carries_bounds_and_errors_across_threads(m):
    from petta import MettaSyntaxError, TimeLimitError, aio

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-b $n) (if (== $n 0) done (aio-spin-b (- $n 1))))"
            )
            with pytest.raises(TimeLimitError):
                # The guard fires on the attached worker thread, so the
                # alarm mechanism is proven off the main thread too.
                await am.run("!(aio-spin-b 100000000)", timeout=0.05)
            with pytest.raises(MettaSyntaxError):
                await am.run("!(unclosed")
            groups, text = await am.run("!(println! crossed)", capture=True)
            return text

    assert "crossed" in asyncio.run(go())


def test_aio_spaces_borrow_the_owners_thread(m):
    from petta import MeTTa, PettaError, aio

    async def go():
        am = await aio.connect(metta=m)
        nested = await am.space("&aio-borrowed")
        await nested.add(S.tag(1))
        got = await nested.count()
        await nested.aclose()  # borrowed: the thread is the owner's
        still = await am.count()  # so the owner keeps working
        await am.aclose()
        try:
            await am.count()
            raise AssertionError("a closed connection accepted work")
        except PettaError:
            pass
        return got, still

    got, still = asyncio.run(go())
    assert (got, still) == (1, 0)
    MeTTa("&aio-borrowed").drop()


def test_aio_interrupt_stops_the_running_evaluation(m):
    from petta import Interrupted, aio

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-c $n) (if (== $n 0) done (aio-spin-c (- $n 1))))"
            )
            spin = asyncio.ensure_future(am.eval("(aio-spin-c 2000000000)"))
            await asyncio.sleep(0.15)  # well inside the engine by now
            assert am.interrupt() is True
            with pytest.raises(Interrupted):
                await spin
            assert am.interrupt() is False  # idle again: the no-op reading
            return await am.value("(+ 1 1)")  # the engine keeps working after

    assert asyncio.run(go()) == 2


def test_aio_timeout_cancellation_stops_the_engine(m):
    import time

    from petta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-d $n) (if (== $n 0) done (aio-spin-d (- $n 1))))"
            )
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(
                    am.eval("(aio-spin-d 2000000000)"), timeout=0.2
                )
            # The cancellation interrupted the engine: were the spin still
            # holding the worker, this next call would wait minutes.
            t0 = time.perf_counter()
            value = await am.value("(+ 2 2)")
            return value, time.perf_counter() - t0

    value, took = asyncio.run(go())
    assert value == 4
    assert took < 30.0


def test_aio_cancelled_while_queued_never_runs(m):
    from petta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-e $n) (if (== $n 0) done (aio-spin-e (- $n 1))))"
            )
            long = asyncio.ensure_future(am.eval("(aio-spin-e 30000000)"))
            queued = asyncio.ensure_future(am.add(S.never(1)))
            await asyncio.sleep(0.05)  # long is running; queued is waiting
            queued.cancel()
            long.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued
            with pytest.raises(asyncio.CancelledError):
                await long
            # The abandoned add never ran: no (never 1) fact exists. The
            # space is not empty, because the spin equation is stored too.
            assert await am.query(S.never(V.n)) == []
            return True

    assert asyncio.run(go())


def test_aio_exposes_every_plain_request_response_method():
    from petta import aio

    expected = {
        "fresh_space",
        "drop",
        "profile",
        "parse",
        "cast",
        "trace",
        "lint",
        "digest",
        "unregister_op",
        "builtins",
        "is_function",
        "is_function_here",
        "arities",
        "derivation",
        "why",
    }
    assert not expected.difference(dir(aio.AsyncMeTTa))
    signature = inspect.signature(aio.AsyncMeTTa.save)
    assert list(signature.parameters) == ["self", "path", "format"]
    assert signature.parameters["format"].default == "metta"
    derivation = inspect.signature(aio.AsyncMeTTa.derivation)
    assert list(derivation.parameters) == [
        "self",
        "target",
        "depth",
        "timeout",
        "inferences",
    ]
    assert derivation.parameters["depth"].default is None
    assert list(inspect.signature(aio.AsyncMeTTa.run).parameters) == [
        "self",
        "source",
        "using",
        "timeout",
        "inferences",
        "capture",
        "atomic",
        "speculative",
    ]
    assert list(inspect.signature(aio.AsyncMeTTa.query).parameters) == [
        "self",
        "patterns",
        "where",
        "limit",
        "timeout",
        "inferences",
    ]
    assert list(inspect.signature(aio.AsyncMeTTa.eval).parameters) == [
        "self",
        "target",
        "timeout",
        "inferences",
        "capture",
        "residuals",
    ]
    assert list(inspect.signature(aio.AsyncMeTTa.value).parameters) == [
        "self",
        "target",
        "timeout",
        "inferences",
    ]


def test_aio_plain_methods_forward_on_the_worker(metta, tmp_path):
    from petta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=metta.fresh_space()) as am:
            parsed = await am.parse("(aio-forward value)")
            assert parsed == S["aio-forward"](S.value)
            assert await am.cast(3, int) == 3
            assert isinstance(await am.builtins(), list)
            assert await am.is_function("+")
            assert isinstance(await am.is_function_here("+"), bool)
            assert await am.arities("+")
            assert await am.lint() == []
            assert len(await am.digest()) == 64
            assert "unknown" in (await am.why(S["aio-unknown"](V.x))).lower()

            groups, profile = await am.profile("!(+ 1 2)")
            assert groups == [[3]]
            assert profile.samples >= 0
            assert isinstance(await am.trace("!(+ 2 3)"), list)

            await am.run(
                "(aio-proof fact)\n"
                "(= (aio-prove) (match (context-space) (aio-proof $x) $x))"
            )
            assert await am.derivation(S["aio-prove"]())
            partial = await am.derivation(
                S["aio-prove"](), depth=1, timeout=5.0, inferences=100_000
            )
            assert partial and not partial[0].complete

            await am.call(
                lambda sync: sync.register_op(
                    lambda value: value,
                    name="aio-unregister-target",
                    typed=False,
                )
            )
            assert await am.is_function("aio-unregister-target")
            await am.unregister_op("aio-unregister-target")
            assert not await am.is_function("aio-unregister-target")

            path = tmp_path / "aio.fast"
            assert await am.save(path, format="fast") == 2

            fresh = await am.fresh_space()
            assert fresh._worker is am._worker
            await fresh.add(S.temporary(1))
            assert await fresh.count() == 1
            await fresh.drop()
            await fresh.aclose()
            await am.drop()

    asyncio.run(go())


def test_aio_failed_worker_refuses_immediately_and_names_the_cause(monkeypatch):
    import petta
    from petta import PettaError, aio

    def fail_attach():
        raise RuntimeError("round2 attach failed")

    monkeypatch.setattr(petta.janus, "attach_engine", fail_attach)

    async def go():
        broken = aio.AsyncMeTTa()
        with pytest.raises(RuntimeError, match="round2 attach failed"):
            await broken.start()
        assert "failed" in repr(broken)
        with pytest.raises(PettaError, match="failed.*round2 attach failed"):
            await broken.start()
        with pytest.raises(PettaError, match="failed.*round2 attach failed"):
            await broken.count()
        await broken.aclose()
        assert "closed" in repr(broken)

    asyncio.run(go())


def test_aio_borrowed_space_refuses_after_owner_closes(metta):
    from petta import PettaError, aio

    async def go():
        owner = await aio.connect(metta=metta)
        borrowed = await owner.space("&aio-closed-borrower")
        await owner.aclose()
        assert "closed" in repr(borrowed)
        with pytest.raises(PettaError, match="closed"):
            await borrowed.count()

    asyncio.run(go())
    metta.space("&aio-closed-borrower").drop()


def test_aio_close_interrupts_work(m):
    from petta import Interrupted, PettaError, aio

    async def go():
        am = await aio.connect(metta=m)
        await am.run(
            "(= (aio-close-spin $n) "
            "(if (== $n 0) done (aio-close-spin (- $n 1))))"
        )
        running = asyncio.create_task(
            am.eval("(aio-close-spin 2000000000)")
        )
        queued = asyncio.create_task(am.add(S.never_after_close(1)))
        await asyncio.sleep(0.1)

        await am.aclose(timeout=2.0)

        with pytest.raises(Interrupted):
            await running
        with pytest.raises(PettaError, match="closed before this request ran"):
            await queued
        assert am._worker.thread is not None
        assert not am._worker.thread.is_alive()
        assert not m.query(S.never_after_close(V.value))

    asyncio.run(go())


def test_aio_leak_warns_and_stop_joins(m):
    from petta import aio

    async def open_connection():
        am = await aio.connect(metta=m)
        await am.count()
        return am

    am = asyncio.run(open_connection())
    worker = am._worker
    with pytest.warns(ResourceWarning, match="open AsyncMeTTa"):
        del am
        gc.collect()

    worker.stop(timeout=2.0)
    assert worker.thread is not None
    assert not worker.thread.is_alive()


def test_aio_shutdown_handler_stops_forgotten_workers(m):
    from petta import aio

    async def open_connection():
        return await aio.connect(metta=m)

    am = asyncio.run(open_connection())
    thread = am._worker.thread
    aio._shutdown_workers()
    assert thread is not None
    assert not thread.is_alive()


def test_aio_logs_worker_attachment_and_shutdown(m, caplog):
    from petta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            assert await am.count() == 0

    with caplog.at_level(logging.DEBUG, logger="petta.aio"):
        asyncio.run(go())

    assert "worker attached a Prolog engine" in caplog.text
    assert "worker detached its Prolog engine" in caplog.text
