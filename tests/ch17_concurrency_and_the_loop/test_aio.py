"""Purpose: the asyncio facade: the loop stays live while the engine
works, results and errors cross threads intact, bounds fire on the worker
thread, and spaces borrow the owner's engine thread.
Guarantees:
  - the two surfaces agree PARAMETER for parameter, not merely method for
    method, so a door cannot carry one name and two shapes: checking names
    alone let watch(), stream() and define() each diverge until they were
    found by hand [tested: test_aio_covers_the_whole_synchronous_surface;
    commit=891d413a32b3e6f132998e3613618ff029dfda0d]
  - async solve, Linda verbs, watch, class/type dispatch, and both transaction
    laws execute on the owning worker [tested:
    test_aio_structural_surface_behaves; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - AsyncMeTTa.eval mirrors the synchronous single answer shape and exposes
    no residuals parameter [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - capture and execution-policy scopes cross the worker hop without changing
    awaited return shapes [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - async space is the single named, anonymous, and provider-backed creation
    door [tested: test_aio_space_attaches_a_provider_without_a_register_alias;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - async anonymous spaces retain the submitting coroutine's source location
    across the worker hop [tested:
    test_async_anonymous_space_repr_keeps_the_submitting_site;
    commit=50d1de4d0ead4a0c3997f9b2ef58631bbafaede3]
  - async peek and take mirror the Space handle's Linda wait verbs on the
    engine worker [tested: test_async_peek_and_take_mirror_the_space_handle;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - async match and sample mirror the algebra carrier doors on their owning
    worker [tested: test_aio_covers_the_whole_synchronous_surface;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - async bound ``fn.neg`` evaluates the shared composite operator recipe on
    the engine worker [tested: test_aio_structural_surface_behaves;
    commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
  - async reification, world evaluation, and commit stay on the owning worker
    and preserve immutable branching [tested:
    test_async_worlds_stay_on_the_owning_worker; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - async coverage declarations and complete saga scopes stay on the owning
    worker [tested: test_async_saga_and_world_coverage_stay_on_the_owning_worker;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import asyncio
import dataclasses
import gc
import inspect
import logging
import re
import threading
import time
import uuid
from collections import Counter

import pytest

import metta as metta_module
from metta import (
    TRUE,
    MeTTa,
    MettaError,
    S,
    V,
    aio,
)
from metta._engine import bridge as engine_bridge
from metta.atoms import Variable
from metta.errors import (
    EngineError,
    InferenceLimitError,
    Interrupted,
    MettaSyntaxError,
    TimeLimitError,
)
from metta.foreign import SpaceProvider


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def test_aio_mirrors_the_surface(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.add(S.edge(1, 2), S.edge(2, 3))
            rows = await am.match(S.edge(V.a, V.b), S.edge(V.b, V.c))
            groups = await am.run("!(+ 1 2)")
            value = await am.one("(+ 2 3)")
            count = await am.count()
            return rows, groups, value, count

    rows, groups, value, count = asyncio.run(go())
    assert [tuple(r) for r in rows] == [(1, 2, 3)]
    assert groups == [[3]] and value == 5 and count == 2


def test_async_worlds_stay_on_the_owning_worker(m):
    """The async wrapper never exposes a blocking world evaluation door."""
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.add(S.base(1))
            await am.covers("writesState")
            world = await am.reify()
            answers, successor = await world.eval(
                "(progn (add-atom &self (async-world 2)) done)"
            )
            assert world.atoms == (S.base(1),)
            assert successor.diff(world) == ([S.async_world(2)], [])
            assert await am.atoms() == [S.base(1)]
            await am.commit(successor)
            return answers, await am.atoms()

    answers, atoms = asyncio.run(go())
    assert answers == [S.done]
    assert atoms == [S.base(1), S.async_world(2)]


def test_async_saga_and_world_coverage_stay_on_the_owning_worker(m):
    """Both new synchronous laws cross the worker as complete scopes."""
    suffix = uuid.uuid4().hex[:8]
    operation = f"aio-saga-forward-{suffix}"
    compensation = f"aio-saga-reverse-{suffix}"
    callback_threads = []

    def forward(value: int) -> int:
        callback_threads.append(threading.get_ident())
        return value

    def reverse(_quoted):
        callback_threads.append(threading.get_ident())
        return S.done

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            receipts = await am.space()
            declaration = None
            coverage = None
            try:
                await am.op(forward, name=operation, effect="writesState")
                await am.op(reverse, name=compensation, effect="writesState")
                declaration = await am.compensates(operation, compensation)

                uncovered = await am.reify()
                try:
                    with pytest.raises(MettaError, match="writesState"):
                        await uncovered.eval(f"({operation} 1)")
                finally:
                    await uncovered.aclose()

                coverage = await am.covers("writesState")
                world = await am.reify()
                try:
                    assert (await world.eval(f"({operation} 2)"))[0] == [2]
                finally:
                    await world.aclose()

                with pytest.raises(RuntimeError, match="async saga abort"):
                    async with am.saga(receipts) as saga:
                        assert await saga.run(f"({operation} 7)") == [7]
                        abort = RuntimeError("async saga abort")
                        raise abort
                assert await receipts.atoms() == []
                worker_thread = await am.call(lambda _space: threading.get_ident())
                assert callback_threads == [worker_thread, worker_thread, worker_thread]
            finally:
                if coverage is not None:
                    await am.call(
                        lambda space: space._at("&metta").remove(coverage)
                    )
                if declaration is not None:
                    await am.call(
                        lambda space: space._at("&metta").remove(declaration)
                    )
                await am.unregister_op(operation)
                await am.unregister_op(compensation)
                await receipts.drop()

    asyncio.run(go())


def test_aio_keeps_the_loop_live_while_the_engine_spins(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run("(= (aio-spin $n) (if (== $n 0) done (aio-spin (- $n 1))))")
            ticks = 0

            async def ticker():
                nonlocal ticks
                while True:
                    await asyncio.sleep(0.005)
                    ticks += 1

            beat = asyncio.ensure_future(ticker())
            answers = await am.eval(
                "(with-pragma! ((max-stack-depth 1000000000)) (aio-spin 3000000))"
            )
            beat.cancel()
            return ticks, answers

    ticks, answers = asyncio.run(go())
    assert answers == [S.done]
    # A blocked loop ticks zero times; the generous floor keeps slow
    # machines out of the assertion.
    assert ticks >= 3


def test_aio_carries_bounds_and_errors_across_threads(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-b $n) (if (== $n 0) done (aio-spin-b (- $n 1))))"
            )
            with pytest.raises(TimeLimitError):
                # The guard fires on the attached worker thread, so the
                # alarm mechanism is proven off the main thread too.
                await am.run(
                    "!(with-pragma! ((max-stack-depth 1000000000)) "
                    "(aio-spin-b 100000000))",
                    timeout=0.05,
                )
            with pytest.raises(MettaSyntaxError):
                await am.run("!(unclosed")
            with am.capture() as output:
                groups = await am.run("!(println! crossed)")
            assert groups == [[TRUE]]
            return output.text

    assert "crossed" in asyncio.run(go())


def test_aio_spaces_borrow_the_owners_thread(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
            msg = "a closed connection accepted work"
            raise AssertionError(msg)
        except MettaError:
            pass
        return got, still

    got, still = asyncio.run(go())
    assert (got, still) == (1, 0)
    MeTTa().space("&aio-borrowed").drop()


def test_aio_interrupt_stops_the_running_evaluation(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-c $n) (if (== $n 0) done (aio-spin-c (- $n 1))))"
            )
            spin = asyncio.ensure_future(
                am.eval(
                    "(with-pragma! ((max-stack-depth 1000000000)) "
                    "(aio-spin-c 2000000000))"
                )
            )
            await asyncio.sleep(0.15)  # well inside the engine by now
            assert am.interrupt() is True
            with pytest.raises(Interrupted):
                await spin
            assert am.interrupt() is False  # idle again: the no-op reading
            return await am.one("(+ 1 1)")  # the engine keeps working after

    assert asyncio.run(go()) == 2


def test_aio_drain_only_discards_structured_interrupt(m, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    janus = engine_bridge()
    original = janus.query_once
    unexpected_waiting = threading.Event()
    release_unexpected = threading.Event()
    injected = iter(
        (
            "error(metta_control_signal(interrupted, none), context(metta, interrupted))",
            "error(unexpected_drain, context(test, drain))",
        )
    )

    def inject(goal, inputs=None):
        if goal == "true" and (error := next(injected, None)) is not None:
            if "unexpected_drain" in error:
                unexpected_waiting.set()
                if not release_unexpected.wait(2.0):
                    msg = "the drain test did not release its worker"
                    raise RuntimeError(msg)
            return original(f"throw({error})")
        return original(goal, inputs)

    monkeypatch.setattr(janus, "query_once", inject)

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            assert await am.count() == 0
            running = asyncio.create_task(am.count())
            assert await asyncio.to_thread(unexpected_waiting.wait, 2.0)
            queued = asyncio.create_task(am.count())
            await asyncio.sleep(0)
            release_unexpected.set()
            with pytest.raises(EngineError, match="unexpected_drain"):
                await asyncio.wait_for(running, timeout=2.0)
            with pytest.raises(MettaError, match="failed before this request ran"):
                await asyncio.wait_for(queued, timeout=2.0)
            assert "failed" in repr(am)
            with pytest.raises(MettaError, match=r"failed.*unexpected_drain"):
                await am.count()

    asyncio.run(go())


def test_aio_timeout_cancellation_stops_the_engine(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-d $n) (if (== $n 0) done (aio-spin-d (- $n 1))))"
            )
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(
                    am.eval(
                        "(with-pragma! ((max-stack-depth 1000000000)) "
                        "(aio-spin-d 2000000000))"
                    ),
                    timeout=0.2,
                )
            # The cancellation interrupted the engine: were the spin still
            # holding the worker, this next call would wait minutes.
            t0 = time.perf_counter()
            value = await am.one("(+ 2 2)")
            return value, time.perf_counter() - t0

    value, took = asyncio.run(go())
    assert value == 4
    assert took < 30.0


def test_aio_cancelled_while_queued_never_runs(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-spin-e $n) (if (== $n 0) done (aio-spin-e (- $n 1))))"
            )
            long = asyncio.ensure_future(
                am.eval(
                    "(with-pragma! ((max-stack-depth 1000000000)) "
                    "(aio-spin-e 30000000))"
                )
            )
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
            assert await am.match(S.never(V.n)) == []
            return True

    assert asyncio.run(go())


def test_aio_covers_the_whole_synchronous_surface():
    """Parity is computed, not hand-listed: every public MeTTa method is
    on AsyncMeTTa except the ledger below, each exclusion with its
    reason, so a new synchronous method fails here until it gains its
    async twin or a stated reason not to.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from metta._space import Space

    excluded = {
        # asyncio's fan-out is N workers and asyncio.gather; a pool of
        # engine threads is the synchronous spelling of the same thing.
        "pool",
        # an interactive Prolog toplevel belongs to a terminal thread.
        "prolog",
        # a transaction body is a closed synchronous goal (SWI's
        # transaction/1 takes one); transaction() is the async spelling
        # and there is no decorator because decoration cannot await.
        "transactional",
        # Answers is a synchronous replayable iterator. AsyncMeTTa's stream
        # is the awaitable pull protocol rather than a cross-thread iterator.
        "answers",
        # These are Space's Atom/Handle operand protocol, not engine calls.
        "metatype",
        "to_wire",
    }
    # Atom and Handle methods are operand behavior inherited by Space, not
    # engine calls for the async facade to mirror.
    sync = {name for name in Space.__dict__ if not name.startswith("_")}
    missing = sync - set(dir(aio.AsyncMeTTa)) - excluded
    assert not missing, f"AsyncMeTTa lacks {sorted(missing)}"
    assert not excluded - sync, "the exclusion ledger names a method Space lost"

    # Parity is per PARAMETER, not per name. Checking names alone let three
    # doors carry the same name and a different surface on each side, all
    # found by hand on 2026-08-31: watch() took deadline= here and queue_max=
    # there, stream() lost limit= and under=, and define() lost name=, which
    # is the naming ladder's exact-spelling rung and so cannot be missing from
    # one surface. A default may differ where the surfaces genuinely differ
    # (queue_max is unbounded-by-default synchronously); a NAME may not.
    parameter_excluded = {
        # The async stream IS the delivery, so there is nothing to call back.
        # The asynchronous docstring says so where the parameter would be.
        ("subscribe", "callback"),
    }
    divergent = set()
    for name in sorted(sync - excluded):
        asynchronous = getattr(aio.AsyncMeTTa, name, None)
        if asynchronous is None:
            continue
        try:
            here = inspect.signature(getattr(Space, name))
            there = inspect.signature(asynchronous)
        except (TypeError, ValueError):
            continue
        named = {
            side: {
                parameter.name
                for parameter in signature.parameters.values()
                if parameter.name != "self" and parameter.kind is not parameter.VAR_KEYWORD
            }
            for side, signature in (("sync", here), ("async", there))
        }
        divergent |= {
            (name, parameter)
            for parameter in named["sync"] ^ named["async"]
            if (name, parameter) not in parameter_excluded
        }
    assert not divergent, (
        f"these doors carry one name and two surfaces: {sorted(divergent)}"
    )
    # The set comparison above already proves the two surfaces carry the same
    # parameter NAMES. What is left to pin is what a name alone does not say:
    # the defaults, and which parameters are positional. Pinning the exact list
    # instead made every legitimate widening of a door look like a defect --
    # `save` gaining the limit guards its siblings carry went red here while
    # the parity it exists to check was intact.
    save = inspect.signature(aio.AsyncMeTTa.save)
    assert save.parameters["format"].default == "metta"
    assert save.parameters["format"].kind is inspect.Parameter.KEYWORD_ONLY
    derivation = inspect.signature(aio.AsyncMeTTa.derivation)
    assert derivation.parameters["depth"].default is None
    assert (
        derivation.parameters["depth"].kind
        is inspect.Parameter.POSITIONAL_OR_KEYWORD
    )
    assert list(inspect.signature(aio.AsyncMeTTa.run).parameters) == [
        "self",
        "source",
        "timeout",
        "inferences",
    ]
    assert list(inspect.signature(aio.AsyncMeTTa.match).parameters) == [
        "self",
        "patterns",
        "where",
        "limit",
        "timeout",
        "inferences",
        "under",
        "into",
    ]
    # What this pin exists for, stated rather than spelled as a list: the
    # `residuals` parameter is still absent, and eval() carries answers()'
    # three relation selectors on BOTH surfaces because answers() itself is
    # excluded above. An exact list would go red on every legitimate widening
    # or pruning, as it did when `using=` collapsed into `bind()`.
    evaluated = set(inspect.signature(aio.AsyncMeTTa.eval).parameters)
    assert "residuals" not in evaluated
    assert {"under", "theory", "interpreter"} <= evaluated
    # And the binding scope replaced the keyword on every door that took it.
    for door in ("eval", "one", "first", "eval_status", "derivation"):
        parameters = set(inspect.signature(getattr(aio.AsyncMeTTa, door)).parameters)
        assert "using" not in parameters, door


def test_aio_plain_methods_forward_on_the_worker(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=metta._new_space()) as am:
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

            token_pattern = re.compile(r"aio[0-9]+", re.IGNORECASE)
            await am.register_token(token_pattern, lambda token: S["aio-token"](token))
            try:
                assert await am.parse("AIO7") == S["aio-token"]("AIO7")
            finally:
                await am.unregister_token(token_pattern)
            assert await am.parse("AIO7") == S.AIO7

            groups, profile = await am.profile("!(+ 1 2)")
            assert groups == [[3]]
            assert profile.samples >= 0
            assert isinstance(await am.trace("!(+ 2 3)"), list)

            await am.run(
                "(aio-proof fact)\n(= (aio-prove) (match (context-space) (aio-proof $x) $x))"
            )
            assert await am.derivation(S["aio-prove"]())
            partial = await am.derivation(
                S["aio-prove"](), depth=1, timeout=5.0, inferences=100_000
            )
            assert partial and not partial[0].complete

            await am.call(
                lambda sync: sync.op(
                    lambda value: value,
                    name="aio-unregister-target",
                    effect="pureStructural",
                )
            )
            assert await am.is_function("aio-unregister-target")
            await am.unregister_op("aio-unregister-target")
            assert not await am.is_function("aio-unregister-target")

            path = tmp_path / "aio.fast"
            assert await am.save(path, format="fast") == 2

            fresh = await am.space()
            assert fresh._worker is am._worker
            await fresh.add(S.temporary(1))
            assert await fresh.count() == 1
            await fresh.drop()
            await fresh.aclose()
            await am.drop()

    asyncio.run(go())


def test_async_peek_and_take_mirror_the_space_handle(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=metta._new_space()) as am:
            job = S.job(S.ready)
            await am.add(job)
            assert await am.peek(S.job(V.state), deadline=0.1) == job
            assert await am.take(S.job(V.state), deadline=0.1) == job
            with pytest.raises(TimeoutError, match="no atom matching"):
                await am.take(S.job(V.state), deadline=0.001)

    asyncio.run(go())


def test_aio_space_attaches_a_provider_without_a_register_alias():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Provider(SpaceProvider):
        def __init__(self):
            self.stored = [S.edge(S.a, S.b)]

        def match(self, _pattern):
            return iter(self.stored)

        def atoms(self):
            return iter(self.stored)

        def add(self, atom):
            self.stored.append(atom)

        def remove(self, atom):
            try:
                self.stored.remove(atom)
            except ValueError:
                return False
            return True

    async def go():
        async with aio.AsyncMeTTa() as am:
            provider = Provider()
            attached = await am.space("&aio-provider", backing=provider)
            try:
                await attached.add(S.edge(S.b, S.c))
                rows = await attached.match(S.edge(V.left, V.right))
                assert [(row.left, row.right) for row in rows] == [
                    (S.a, S.b),
                    (S.b, S.c),
                ]
            finally:
                await attached.drop()

    asyncio.run(go())


def test_aio_failed_worker_refuses_immediately_and_names_the_cause(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def fail_attach():
        msg = "round2 attach failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(engine_bridge(), "attach_engine", fail_attach)

    async def go():
        broken = aio.AsyncMeTTa()
        with pytest.raises(RuntimeError, match="round2 attach failed"):
            await broken.start()
        assert "failed" in repr(broken)
        with pytest.raises(MettaError, match=r"failed.*round2 attach failed"):
            await broken.start()
        with pytest.raises(MettaError, match=r"failed.*round2 attach failed"):
            await broken.count()
        await broken.aclose()
        assert "closed" in repr(broken)

    asyncio.run(go())


def test_aio_borrowed_space_refuses_after_owner_closes(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        owner = await aio.connect(metta=metta)
        borrowed = await owner.space("&aio-closed-borrower")
        await owner.aclose()
        assert "closed" in repr(borrowed)
        with pytest.raises(MettaError, match="closed"):
            await borrowed.count()

    asyncio.run(go())
    metta._at("&aio-closed-borrower").drop()


def test_aio_close_interrupts_work(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        am = await aio.connect(metta=m)
        await am.run(
            "(= (aio-close-spin $n) (if (== $n 0) done (aio-close-spin (- $n 1))))"
        )
        running = asyncio.create_task(
            am.eval(
                "(with-pragma! ((max-stack-depth 1000000000)) "
                "(aio-close-spin 2000000000))"
            )
        )
        queued = asyncio.create_task(am.add(S.never_after_close(1)))
        await asyncio.sleep(0.1)

        await am.aclose(timeout=2.0)

        with pytest.raises(Interrupted):
            await running
        with pytest.raises(MettaError, match="closed before this request ran"):
            await queued
        assert am._worker.thread is not None
        assert not am._worker.thread.is_alive()
        assert not m.match(S.never_after_close(V.value))

    asyncio.run(go())


def test_aio_leak_warns_and_stop_joins(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_aio_shutdown_handler_stops_forgotten_workers(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def open_connection():
        return await aio.connect(metta=m)

    am = asyncio.run(open_connection())
    thread = am._worker.thread
    aio._shutdown_workers()
    assert thread is not None
    assert not thread.is_alive()


def test_aio_empty_shutdown_does_not_import_janus(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def fail_bridge():
        msg = "No module named 'janus_swi'"
        raise ModuleNotFoundError(msg)

    monkeypatch.setattr(aio, "_LIVE_WORKERS", [])
    monkeypatch.setattr(aio, "bridge", fail_bridge)

    aio._shutdown_workers()


def test_aio_shutdown_handler_attempts_every_worker(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    stopped = []

    class BrokenWorker:
        def __init__(self, name):
            self.name = name

        def stop(self):
            stopped.append(self.name)
            msg = f"cannot stop {self.name}"
            raise RuntimeError(msg)

    workers = [BrokenWorker("first"), BrokenWorker("second")]
    monkeypatch.setattr(aio, "_LIVE_WORKERS", workers)

    with pytest.raises(ExceptionGroup, match="failed to stop 2") as caught:
        aio._shutdown_workers()

    assert stopped == ["first", "second"]
    assert [str(error) for error in caught.value.exceptions] == [
        "cannot stop first",
        "cannot stop second",
    ]


def test_aio_logs_worker_attachment_and_shutdown(m, caplog):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            assert await am.count() == 0

    with caplog.at_level(logging.DEBUG, logger="metta.aio"):
        asyncio.run(go())

    assert "worker attached a Prolog engine" in caplog.text
    assert "worker detached its Prolog engine" in caplog.text


def test_aio_structural_surface_behaves():
    """The non-mechanical parity pieces end to end: transaction rollback,
    stats, assuming, prepared, the async cursor, the async subscription
    stream, and the async function object.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    async def go():
        async with aio.AsyncMeTTa() as am:
            m = await am.space()
            await m.add(S.edge(S.a, S.b), S.edge(S.b, S.c))

            def failing(sync_m):
                sync_m.add(S.tx(1))
                msg = "undo"
                raise ValueError(msg)

            with pytest.raises(ValueError, match="undo"):
                await m.transaction(failing)
            assert await m.count() == 2  # the write rolled back

            returned = await m.transaction(len)
            assert returned == 2

            solved = await m.solve(4, V.async_x - 1)
            assert solved.async_x == 5

            @dataclasses.dataclass
            class AsyncPoint:
                x: int

            await m.define(AsyncPoint)
            assert await m.type(AsyncPoint(3)) == S.AsyncPoint

            await m.add(S.async_message(7))
            assert await m.peek(S.async_message(V.n), deadline=0.1) == S.async_message(7)
            assert await m.take(S.async_message(V.n), deadline=0.1) == S.async_message(7)

            term = S.progn(
                S["add-atom"](S[m.name], S.async_tx(1)),
                S.empty(),
            )
            before_transaction = await m.count()
            assert await m.transaction(term) == []
            assert await m.count() == before_transaction

            async with m.stats() as s:
                await m.match(S.edge(V.x, V.y))
            assert s.inferences > 0

            async with m.assuming(S.closed(S.gate)):
                assert len(await m.match(S.closed(V.w))) == 1
            assert len(await m.match(S.closed(V.w))) == 0

            route = await m.prepare(S.edge(V.a, V.b))
            assert route.columns == ("a", "b")
            assert len(await route.solve()) == 2
            assert len(await route.solve(given=[S.edge(S.c, S.d)])) == 3
            assert "stored atoms: engine unification" in await route.explain()

            cloned = await am.copy()
            # This assertion has flaked through three distinct causes, each
            # fixed where it lived. First the module-blind invalidation
            # wrapper let a clone's write strip &self's spec atoms (fixed by
            # scoping, 2026-08-19). Then a copied specialization's own body
            # re-entered the specializer with no row behind its name and
            # stored every spec TWICE in the clone (fixed by adoption), and
            # an enumeration that interleaved a base equation between two
            # generated clauses dropped the earlier one (fixed by copy()
            # ordering generated equations last), both 2026-08-20. What
            # remains here is the comparison itself: str() spells variables
            # by their raw ids, and two enumerations of the same stored
            # equation may render different ids, so equal-up-to-alpha atoms
            # compared unequal as strings. Canonicalizing variable names by
            # first occurrence compares what the assertion means.
            def _canonical(atom):
                names: dict[str, str] = {}

                def rename(node):
                    if isinstance(node, Variable):
                        label = names.setdefault(node.name,
                                                 f"$c{len(names)}")
                        return Variable(label)
                    return node

                return str(atom.map(rename))

            clone_atoms = Counter(_canonical(a) for a in await cloned.atoms())
            self_atoms = Counter(_canonical(a) for a in await am.atoms())
            extra = sorted((clone_atoms - self_atoms).elements())
            missing = sorted((self_atoms - clone_atoms).elements())
            assert not extra and not missing, (
                f"&self moved between copy and count: the clone holds "
                f"{extra} that &self does not, and &self holds "
                f"{missing} the clone never saw"
            )
            await cloned.drop()

            async with m.stream(S.edge(V.a, V.b)) as rows:
                assert await rows.columns() == ("a", "b")
                assert "stored atoms: engine unification" in await rows.explain()
                streamed = [row async for row in rows]
            assert len(streamed) == 2

            # A cursor iterated without async-with closes explicitly.
            bare = m.stream(S.edge(V.a, V.b))
            assert (await bare.__anext__()) is not None
            await bare.aclose()
            with pytest.raises(StopAsyncIteration):
                await bare.__anext__()

            await m.run("(= (aio-inc $x) (+ $x 1))")
            inc = m.fn["aio-inc"]
            assert await inc(41) == 42
            assert await m.fn.aio_inc(41) == 42
            assert await m.fn.neg(4) == -4
            assert await inc.first(1) == 2
            assert await inc.all(2) == [3]
            assert inc.__qualname__.endswith(".aio-inc")

            events = []
            async with m.subscribe(S.order(V.n), on="both") as sub:
                await m.add(S.order(1))
                events.append(await asyncio.wait_for(sub.__anext__(), 5))
                await m.remove(S.order(1))
                events.append(await asyncio.wait_for(sub.__anext__(), 5))
            assert [event.action for event in events] == ["add", "remove"]

            async with m.watch(S.watched(V.n)) as watched:
                await m.add(S.watched(9))
                event = await asyncio.wait_for(watched.__anext__(), 5)
                assert event.n == 9
            # After aclose the stream ends rather than hanging.
            with pytest.raises(StopAsyncIteration):
                await sub.__anext__()
            return True

    assert asyncio.run(go())


def test_async_anonymous_space_repr_keeps_the_submitting_site(metta):
    """Creation provenance is captured before control crosses the worker."""
    async def go():
        async with aio.AsyncMeTTa(metta=metta) as am:
            line = inspect.currentframe().f_lineno + 1
            child = await am.space()
            try:
                assert f"{__file__}:{line}" in repr(child)
            finally:
                await child.drop()

    asyncio.run(go())


def test_aio_declare_and_register_delegations_land():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    async def go():
        async with aio.AsyncMeTTa() as am:
            m = await am.space()
            source = await m.space("&aio-src")
            declared = await source.source("linear")
            assert "aio-src" in str(declared)

            def double(x: int) -> int:
                return 2 * x

            await m.op(double, name="aio-double", effect="pureStructural")
            assert await m.one("(aio-double 21)") == 42
            await m.unregister_op("aio-double")
            await m.run("(= (aio-dis $x) $x)")
            assert "aio-dis" in await m.call(lambda space: space._disassemble("aio-dis"))
            names = await m.space_names()
            assert "&self" in names
            return True

    assert asyncio.run(go())


def test_aio_scoped_limits_cross_to_the_worker(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # with-limits state is a ContextVar; the request copies the task's
    # context at submission and the worker runs inside it, so the block
    # bounds engine work that happens on ANOTHER thread.
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run(
                "(= (aio-ctx-spin $n) (if (== $n 0) done (aio-ctx-spin (- $n 1))))"
            )
            with am.limits(inferences=2000):
                with pytest.raises(InferenceLimitError):
                    await am.eval("(aio-ctx-spin 100000000)")
            # outside the block the same engine call runs unbounded
            assert await am.eval("(aio-ctx-spin 3)") == [S.done]

    asyncio.run(go())


def _live_workers() -> set:
    """The engine worker threads alive right now, by the name they take."""
    return {
        thread
        for thread in threading.enumerate()
        if thread.name == "metta-aio" and thread.is_alive()
    }


def _watched(space) -> list:
    """What Python is watching, read the way a MeTTa program reads it.

    The standing queries reflect into &metta as (subscription <space>
    <pattern> <edge>) and withdraw when they are cancelled.
    """
    (group,) = space.run("!(collapse (match &metta (subscription $s $p $on) $p))")
    return list(group[0])


def _live_engines(space) -> int:
    """How many SWI engines exist, which is one per open answer cursor.

    Through the runtime's own door, so the count does not race the worker
    thread that is holding the engine this connection attached.
    """
    return space.runtime.once("aggregate_all(count, current_engine(_), N)")["N"]


def _fail_one_crossing(am, failure):
    """Make the next worker crossing raise, and the one after it behave."""
    real = am.call
    fired = []

    async def call(fn):
        if not fired:
            fired.append(1)
            am.call = real
            raise failure
        return await real(fn)

    am.call = call


def test_aio_cancelled_connect_leaves_no_live_worker(m):
    """A cancelled connect() stops the worker it launched.

    The awaiting caller never received the AsyncMeTTa, so nothing else could
    ever close it: the thread and its attached engine used to live to
    interpreter exit.
    """
    before = _live_workers()

    async def go():
        task = asyncio.ensure_future(aio.connect(metta=m))
        await asyncio.sleep(0)  # the task reaches its first suspension
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # Inside the loop, because the refused worker reports its startup
        # through call_soon_threadsafe on the way out.
        for _ in range(100):
            if not _live_workers() - before:
                return
            await asyncio.sleep(0.05)

    asyncio.run(go())
    assert not _live_workers() - before


def test_aio_cancelled_assuming_removes_the_facts_it_installed(m):
    """Cancelling as the worker installs assumed facts removes them again."""

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            block = am.assuming(S.aio_assumed(1))
            holder: list = [None]
            real = am.call
            cancelled: list = []

            async def call(fn):
                answer = await real(fn)
                # Cancel at the crossing that INSTALLED the facts, whatever
                # number that is, which is the torn middle the block would
                # otherwise have to undo and cannot.
                installed = await real(lambda space: bool(space.match(S.aio_assumed(V.n))))
                if installed and not cancelled:
                    cancelled.append(1)
                    holder[0].cancel()
                    await asyncio.sleep(0)
                return answer

            am.call = call
            holder[0] = asyncio.ensure_future(block.__aenter__())
            with pytest.raises(asyncio.CancelledError):
                await holder[0]
            am.call = real
            assert cancelled, "the facts were never installed, so nothing was torn"
            return await am.match(S.aio_assumed(V.n))

    assert asyncio.run(go()) == []


def test_aio_cancelled_subscription_registration_cancels_it(m):
    """A cancelled registration is cancelled on the engine too.

    The caller stopped waiting, so nothing holds the queue the standing query
    would deliver into.
    """

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            events = am.watch(S.aio_orphan(V.x))
            holder: list = [None]
            real = am.call

            async def call(fn):
                # The torn middle: the worker has registered the standing
                # query and the caller that would own it is already gone.
                answer = await real(fn)
                holder[0].cancel()
                await asyncio.sleep(0)  # the cancellation lands on the waiter
                return answer

            am.call = call
            holder[0] = asyncio.ensure_future(events.__anext__())
            with pytest.raises(asyncio.CancelledError):
                await holder[0]
            am.call = real
            return _watched(m)

    assert asyncio.run(go()) == []


def test_aio_a_failed_cursor_close_stays_retryable(m):
    """A close that failed leaves the cursor open AND closable.

    The engine still holds it, so a flag that refused the retry stranded it.
    """

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.add(S.aio_row(1), S.aio_row(2))
            rows = am.stream(S.aio_row(V.n))
            await rows.columns()  # opens the engine cursor
            open_engines = _live_engines(m)
            _fail_one_crossing(am, RuntimeError("transient close failure"))
            with pytest.raises(RuntimeError, match="transient close failure"):
                await rows.aclose()
            await rows.aclose()
            return open_engines, _live_engines(m)

    open_engines, after = asyncio.run(go())
    assert after == open_engines - 1


def test_aio_a_failed_subscription_close_stays_retryable(m):
    """A cancel that failed leaves the subscription live AND cancellable."""

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            events = am.watch(S.aio_retry(V.x))
            await events.__aenter__()
            assert _watched(m)
            _fail_one_crossing(am, RuntimeError("transient cancel failure"))
            with pytest.raises(RuntimeError, match="transient cancel failure"):
                await events.aclose()
            still_live = _watched(m)
            await events.aclose()
            return still_live, _watched(m)

    still_live, after = asyncio.run(go())
    assert still_live != []
    assert after == []


def test_aio_a_failed_subscription_publishes_no_queue(m):
    """A registration that failed leaves no queue for a consumer to wait on.

    The queue used to be published before the subscription existed, so the
    second pull waited on a queue nothing owned and nothing would ever write
    to, forever.
    """

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            events = am.watch(S.aio_refused(V.x))

            async def refuse(_fn):
                msg = "registration refused"
                raise MettaError(msg)

            am.call = refuse
            with pytest.raises(MettaError, match="registration refused"):
                await events.__anext__()
            with pytest.raises(MettaError, match="registration refused"):
                await asyncio.wait_for(events.__anext__(), timeout=10.0)

    asyncio.run(go())


def test_aio_the_close_sentinel_survives_a_full_queue(m):
    """Closing a stream whose queue is full ends it instead of raising.

    put_nowait raises QueueFull, and a close path that raises leaves the
    subscription live behind a flag that has already refused every retry.
    """

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            async with am.watch(S.aio_full(V.x), queue_max=1) as events:
                # Each add delivers through call_soon_threadsafe BEFORE the
                # add's own result does, so the queue is full on return.
                await am.add(S.aio_full(1))
                await am.add(S.aio_full(2))
                assert events is not None
            return _watched(m)

    assert asyncio.run(go()) == []


def test_aio_a_worker_whose_loop_closed_stops_itself(m, monkeypatch):
    """A worker whose caller's loop is gone refuses itself quietly.

    The worker reports its startup through call_soon_threadsafe, which raises
    once the loop has closed. Left unguarded that RuntimeError leaves the
    thread through threading.excepthook, printing a traceback for a case the
    library already handles everywhere else it delivers to a loop.
    """
    janus = engine_bridge()
    attach = janus.attach_engine
    released = threading.Event()
    raised: list = []

    def slow_attach():
        # Hold the worker inside the attach until the caller's loop is closed.
        assert released.wait(30)
        attach()

    monkeypatch.setattr(janus, "attach_engine", slow_attach)
    monkeypatch.setattr(threading, "excepthook", raised.append)
    before = _live_workers()

    async def go():
        task = asyncio.ensure_future(aio.connect(metta=m))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())  # the loop closes with the worker still attaching
    released.set()
    for _ in range(300):
        if not _live_workers() - before:
            break
        time.sleep(0.05)
    assert not _live_workers() - before, "the worker did not stop itself"
    assert not raised, f"the worker raised out of its thread: {raised}"


def test_async_rules_and_pre_add_land_as_awaitable_calls(m):
    """Both doors were excluded because "a decorator cannot await".

    True, and not the obstacle: define(), cache(), pure() and op() have the
    same decorator shape and crossed by becoming awaitable CALLS instead of
    decorators. These two were the only ones the reading kept out, which left
    an async caller unable to land an equation bundle or claim a write door at
    all [measured 2026-08-31].
    """
    from metta import accept, equation, refuse

    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            def bundle():
                yield equation(S["aio-cell"](1)).to(S.low)
                yield equation(S["aio-cell"](2)).to(S.high)

            landed = await am.rules(bundle)
            low = await am.eval(S["aio-cell"](1))
            high = await am.eval(S["aio-cell"](2))

            guarded = await am.space()
            def judge(atom):
                match atom:
                    case (S.secret, _):
                        return refuse("no secrets here")
                    case _:
                        return accept()

            await guarded.pre_add(judge)
            await guarded.add(S.plain(1))
            kept = await guarded.match(S.plain(V.x))
            with pytest.raises(MettaError, match="no secrets here"):
                await guarded.add(S.secret(1))
            return len(landed), low, high, [row.x for row in kept]

    landed, low, high, kept = asyncio.run(go())
    assert landed == 2
    assert low == [S.low] and high == [S.high]
    assert kept == [1]


def test_an_async_evaluation_can_be_annotated(m):
    """answers() is excluded here, so eval() had to carry the carrier.

    An await hands back the whole result, so the replayable cross-thread
    iterator that keeps answers() off this surface is not what an async
    caller wants anyway. Without the carrier on eval(), match(under=) covered
    patterns and NOTHING covered calls: an evaluation could not be annotated
    asynchronously at all [measured 2026-08-31].
    """
    async def go():
        async with aio.AsyncMeTTa(metta=m) as am:
            await am.run("(= (aio-path a) b) (= (aio-path a) c)")
            plain = await am.eval(S["aio-path"](S.a))
            counted = await am.eval(S["aio-path"](S.a), under="counting")
            tagged = await am.eval(S["aio-path"](S.a), under="ranked")
            with metta_module.under("counting"):
                scoped = await am.eval(S["aio-path"](S.a))
            return plain, counted, tagged, scoped

    plain, counted, tagged, scoped = asyncio.run(go())
    assert plain == [S.b, S.c]
    assert counted == [2]
    assert [type(one).__name__ for one in tagged] == ["TaggedAnswer", "TaggedAnswer"]
    assert scoped == [2]
