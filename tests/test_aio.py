"""Purpose: the asyncio facade: the loop stays live while the engine
works, results and errors cross threads intact, bounds fire on the worker
thread, and spaces borrow the owner's engine thread.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import asyncio

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
