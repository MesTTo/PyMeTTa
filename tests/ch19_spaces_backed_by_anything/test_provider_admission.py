"""Purpose: a provider is held for the whole of every use, and a close waits for what it admitted.

Every door admits its use of a provider at entry and releases it when the use
ends, a streamed match's on its last pull, a transaction's at its commit or
rollback. A close stops new admission first, waits for the admitted uses, then
removes the engine row and closes the backing outside the bookkeeping lock; a
close requested from inside an admitted use of the same provider hands its
physical steps to the last release and reports closing until then.
Guarantees:
  - a use ends for the thread that admitted it, so a stream closed from
    another thread leaves that thread outside every use and a close it asks
    for later waits for another thread's pull [tested 2026-09-30T09:09:35+10:00:
    test_a_use_ended_on_another_thread_leaves_its_admitting_thread_outside_every_use]
  - an evaluation abandoned while it holds a provider releases the admission
    at the next crossing, not from the collector [tested 2026-09-30T09:09:35+10:00:
    test_an_evaluation_abandoned_over_a_provider_releases_it_outside_the_collector]
"""

import gc
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from metta import MeTTa, S, V
from metta._binding import runtime as _runtime
from metta._binding.runtime import engine_thread
from metta._errors.errors import MettaError
from metta.foreign import SpaceProvider, admitted, closing, has_provider, unregister_provider

ROW = S.admission_row


class GatedListSpace(SpaceProvider):
    """A list-backed provider whose match can hold a pull open on a gate."""

    def __init__(self, atoms=()):  # noqa: D107 -- the test double's construction is documented by its scenarios
        self.stored = list(atoms)
        self.gate = threading.Event()
        self.gate.set()
        self.pulled = threading.Event()
        self.fail_after = None

    def match(self, _pattern):  # noqa: D102 -- the protocol documents the method; the gate is the scenario's
        for index, atom in enumerate(self.stored):
            if self.fail_after is not None and index >= self.fail_after:
                msg = "the backend failed mid-stream"
                raise OSError(msg)
            yield atom
            self.pulled.set()
            self.gate.wait()

    def atoms(self):  # noqa: D102 -- the protocol documents the method
        return iter(self.stored)

    def add(self, atom):  # noqa: D102 -- the protocol documents the method
        self.stored.append(atom)


def _held_pull(space, provider):
    """Start a match in another engine thread and return once its first pull is held open."""
    provider.gate.clear()
    finished = threading.Event()
    outcome = []

    def pull():
        with engine_thread():
            try:
                outcome.append(list(space.eval(S.match(space, ROW(V.x), V.x))))
            except BaseException as error:
                outcome.append(error)
            finally:
                finished.set()

    thread = threading.Thread(target=pull)
    thread.start()
    assert provider.pulled.wait(10), "the provider's first pull never happened"
    return thread, finished, outcome


def test_a_close_waits_for_an_admitted_pull_and_refuses_new_admission():
    """The route detaches at once; the retirement blocks until the held pull finishes."""
    with MeTTa() as context:
        provider = GatedListSpace([ROW(1), ROW(2), ROW(3)])
        space = context.space("&admission-wait", provider)
        thread, finished, outcome = _held_pull(space, provider)
        try:
            assert admitted("&admission-wait") == 1
            closer = ThreadPoolExecutor(max_workers=1).submit(space.drop)
            deadline = threading.Event()
            for _ in range(200):
                if closing("&admission-wait"):
                    break
                deadline.wait(0.01)
            assert closing("&admission-wait")
            assert not closer.done(), "the close returned while a pull still held the provider"
            assert not has_provider("&admission-wait"), "the route stayed attached while the close waited"
            assert not space.dropped, "the retirement ran under an admitted pull"
        finally:
            provider.gate.set()
        closer.result(timeout=10)
        thread.join(10)
        assert finished.is_set()
        assert outcome == [[1, 2, 3]]
        assert not has_provider("&admission-wait")
        assert admitted("&admission-wait") == 0 and not closing("&admission-wait")


def test_a_use_ended_on_another_thread_leaves_its_admitting_thread_outside_every_use():
    """A stream admitted on one thread and closed from another releases the thread that admitted it.

    The release counted the thread that ended the use, so the admitting thread
    stayed a holder after its stream was gone, and a close it asked for later
    took the self-retirement path: it returned at once and left the space
    pending, where a close from outside every use waits for another thread's
    pull, as this one must.
    """
    with MeTTa() as context:
        provider = GatedListSpace([ROW(1), ROW(2), ROW(3)])
        space = context.space("&admission-holder", provider)
        opened, asked = threading.Event(), threading.Event()
        cursors, outcome = [], []

        def admit_then_close_later():
            with engine_thread():
                cursor = space.stream(ROW(V.x))
                assert next(cursor).x == 1
                cursors.append(cursor)
                opened.set()
                assert asked.wait(10)
                try:
                    space.drop()
                    outcome.append(space.dropped)
                except BaseException as error:
                    outcome.append(error)

        admitter = threading.Thread(target=admit_then_close_later)
        admitter.start()
        assert opened.wait(10)
        cursors.pop().close()
        assert admitted("&admission-holder") == 0
        puller, finished, pulled = _held_pull(space, provider)
        try:
            asked.set()
            deadline = threading.Event()
            for _ in range(200):
                if closing("&admission-holder"):
                    break
                deadline.wait(0.01)
            assert closing("&admission-holder")
            admitter.join(0.5)
            assert admitter.is_alive(), "the close returned while another thread's pull held the provider"
            assert not space.dropped
        finally:
            provider.gate.set()
        admitter.join(10)
        puller.join(10)
        assert finished.is_set() and pulled == [[1, 2, 3]]
        assert outcome == [True]
        assert admitted("&admission-holder") == 0 and not closing("&admission-holder")


@pytest.mark.parametrize("abandoned", ["by its last reference", "in a cycle"])
def test_an_evaluation_abandoned_over_a_provider_releases_it_outside_the_collector(abandoned):
    """The admission an abandoned evaluation holds is released by the next crossing.

    Its release takes the admission's locks and can run a close's teardown,
    so it must not run from the collector. Before finalisers stopped crossing
    into the engine, the collector closed such a view's cursor itself, and the
    release ran inside the collection; now the close is handed to the next
    crossing, and the release with it.
    """
    with MeTTa() as context:
        name = "&admission-abandoned"
        provider = GatedListSpace([ROW(1), ROW(2), ROW(3)])
        space = context.space(name, provider)
        marker = (_runtime._CALL_PREDICATE, "true", ())
        gc.collect()
        gc.disable()
        try:
            view = context.self.answers(S.match(S[name], ROW(V.x), V.x))
            next(iter(view))
            assert admitted(name) == 1
            _runtime._DEFERRED_WORK.append(marker)
            if abandoned == "in a cycle":
                cycle = [view]
                cycle.append(cycle)
                del cycle
            del view
        finally:
            gc.enable()
        gc.collect()
        assert any(item is marker for item in _runtime._DEFERRED_WORK), (
            "the collector crossed into the engine and drained the queue"
        )
        assert admitted(name) == 1, "the admission was released from the collector"
        context.runtime.do("true")
        assert admitted(name) == 0
        space.drop()


class TransactionalListSpace(GatedListSpace):
    """The gated provider as a transaction participant whose commit can be held."""

    def __init__(self, atoms=()):  # noqa: D107 -- the test double's construction is documented by its scenarios
        super().__init__(atoms)
        self.began = threading.Event()
        self.hold_commit = threading.Event()
        self.hold_commit.set()
        self.log = []

    def begin(self):  # noqa: D102 -- the protocol documents the method
        self.log.append("begin")
        self.began.set()

    def commit(self):  # noqa: D102 -- the protocol documents the method
        self.hold_commit.wait(10)
        self.log.append("commit")

    def rollback(self):  # noqa: D102 -- the protocol documents the method
        self.log.append("rollback")


def test_an_enlisted_participant_is_held_from_begin_to_commit():
    """A close waits for a transaction that enlisted the provider until its commit has run."""
    with MeTTa() as context:
        provider = TransactionalListSpace([ROW(1)])
        space = context.space("&admission-tx", provider)
        space.atomicity("transactional")
        provider.hold_commit.clear()
        outcome = []

        def enlisting():
            with engine_thread():
                try:
                    context.self.transaction(lambda: space.add(ROW(2)))
                except BaseException as error:
                    outcome.append(error)

        thread = threading.Thread(target=enlisting)
        thread.start()
        try:
            assert provider.began.wait(10)
            assert admitted("&admission-tx") == 1, "begin did not hold the provider"
            closer = ThreadPoolExecutor(max_workers=1).submit(space.drop)
            pause = threading.Event()
            for _ in range(200):
                if closing("&admission-tx"):
                    break
                pause.wait(0.01)
            assert closing("&admission-tx")
            assert not closer.done(), "the close returned before the participant committed"
            assert not space.dropped
        finally:
            provider.hold_commit.set()
        thread.join(10)
        closer.result(timeout=10)
        assert outcome == []
        assert provider.log == ["begin", "commit"]
        assert ROW(2) in provider.stored
        assert not has_provider("&admission-tx")
        assert admitted("&admission-tx") == 0


@pytest.mark.parametrize("release", ["exhaustion", "close", "failure", "cut"])
def test_every_way_a_stream_ends_releases_its_admission(release):
    """A stream released by exhaustion, a closed cursor, a backend failure or an engine cut leaves nothing admitted."""
    with MeTTa() as context:
        provider = GatedListSpace([ROW(1), ROW(2), ROW(3)])
        space = context.space("&admission-release", provider)
        if release == "cut":
            assert context.self.eval(S.once(S.match(S["&admission-release"], ROW(V.x), V.x))) == [1]
        elif release == "failure":
            provider.fail_after = 1
            with pytest.raises(MettaError):
                list(space.eval(S.match(space, ROW(V.x), V.x)))
        elif release == "close":
            cursor = space.stream(ROW(V.x))
            assert next(cursor).x == 1
            cursor.close()
        else:
            assert list(space.eval(S.match(space, ROW(V.x), V.x))) == [1, 2, 3]
        assert admitted("&admission-release") == 0
        space.drop()
        assert not has_provider("&admission-release")


def test_an_older_snapshot_cannot_invoke_a_closed_provider():
    """A transaction that saw the registration cannot use the provider once another thread closed it."""
    with MeTTa() as context:
        provider = GatedListSpace([ROW(1)])
        space = context.space("&admission-snapshot", provider)
        saw = threading.Event()
        closed = threading.Event()
        refusals = []

        def body():
            assert has_provider("&admission-snapshot")
            saw.set()
            assert closed.wait(10)
            try:
                space.add(ROW(2))
            except (MettaError, KeyError) as error:
                refusals.append(error)

        def older():
            with engine_thread():
                context.self.transaction(body)

        thread = threading.Thread(target=older)
        thread.start()
        assert saw.wait(10)
        space.drop()
        closed.set()
        thread.join(10)
        assert len(refusals) == 1, "the older snapshot reached the closed provider"
        assert ROW(2) not in provider.stored


def test_a_close_requested_inside_an_admitted_use_completes_at_the_last_release():
    """A provider that drops its own space from inside a pull reports closing until that pull ends."""
    with MeTTa() as context:
        provider = GatedListSpace([ROW(1), ROW(2)])
        space = context.space("&admission-self", provider)
        observed = []

        def dropping_match(_pattern, original=provider.match):
            yield from original(_pattern)
            space.drop()
            observed.append((has_provider("&admission-self"), closing("&admission-self"), space.dropped))

        provider.match = dropping_match
        assert list(space.eval(S.match(space, ROW(V.x), V.x))) == [1, 2]
        assert observed == [(False, True, False)], "the teardown ran inside the use that requested it"
        assert not has_provider("&admission-self")
        assert space.dropped
        assert not closing("&admission-self") and admitted("&admission-self") == 0


def test_a_same_transaction_replacement_lets_the_admitted_batch_finish_on_its_provider():
    """Unregistering and re-registering inside the transaction that enlisted the old provider is allowed; the batch commits on the old one."""
    with MeTTa() as context:
        provider = TransactionalListSpace([ROW(1)])
        replacement = TransactionalListSpace([])
        space = context.space("&admission-replace", provider)
        space.atomicity("transactional")

        def body():
            space.add(ROW(2))
            unregister_provider(context.runtime, "&admission-replace")
            context.space("&admission-replace", replacement)

        context.self.transaction(body)
        assert provider.log == ["begin", "commit"]
        assert ROW(2) in provider.stored
        assert admitted("&admission-replace") == 0 and not closing("&admission-replace")
        space.drop()
