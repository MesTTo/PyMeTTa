"""Purpose: retain the original foreign participant through native outcomes.

Owns resources: fixtures unregister their native provider rows and release
their test handles. Worker controls attach independent native engines.
Assumes: the shared native owned-record reader and corrected snapshot kernel
are installed [source: engine/spaces/owned_records.pl:metta_owned_key_problem/5;
commit=05fae56ad5b23baa140cb4e6454cb7b304c06f4f].
"""

from __future__ import annotations

import gc
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import MethodType
from uuid import uuid4
from weakref import ref

import pytest

from metta import MettaError, S, space
from metta._binding.runtime import engine_thread
from metta.foreign import PROVIDERS, SpaceProvider, register_provider, unregister_provider


class Participant(SpaceProvider):
    """A provider whose callbacks expose exactly which allocation ran."""

    def __init__(self, label="original", calls=None):
        """Keep an external call log without retaining this provider in it."""
        self.label = label
        self.calls = [] if calls is None else calls
        self.rows = []
        self.saved = []
        self.refuse_commit = False

    def atoms(self):
        """Expose the provider's current rows."""
        return iter(self.rows)

    def add(self, atom):
        """Write only after the native enlistment door has begun the batch."""
        self.calls.append((self.label, "add"))
        self.rows.append(atom)

    def begin(self):
        """Retain one savepoint, including nested speculation."""
        self.calls.append((self.label, "begin"))
        self.saved.append(self.rows.copy())

    def commit(self):
        """Commit or refuse without guessing a rollback outcome."""
        self.calls.append((self.label, "commit"))
        if self.refuse_commit:
            message = "original participant refused completion"
            raise ValueError(message)
        self.saved.pop()

    def rollback(self):
        """Restore the original provider's own savepoint."""
        self.calls.append((self.label, "rollback"))
        self.rows = self.saved.pop()


@pytest.fixture()
def registered(metta):
    """One native registration and a borrowed handle for its name."""
    provider = Participant()
    name = f"&participant-{uuid4().hex}"
    register_provider(metta.runtime, name, provider)
    handle = space(name=name)
    handle.atomicity("transactional")
    try:
        yield handle, provider
    finally:
        if name in PROVIDERS:
            unregister_provider(metta.runtime, name)
        handle.drop()


@pytest.mark.parametrize("replace", [False, True])
@pytest.mark.parametrize("abort", [False, True])
def test_completion_uses_the_captured_provider(metta, registered, replace, abort):
    """Unregister and replacement cannot redirect an old batch's completion."""
    handle, original = registered
    name = str(handle.name)
    replacement = Participant("replacement", original.calls)

    def body():
        handle.add(S.participant_value(7))
        unregister_provider(metta.runtime, name)
        if replace:
            register_provider(metta.runtime, name, replacement)
        if abort:
            message = "abort participant body"
            raise ValueError(message)

    if abort:
        with pytest.raises(ValueError, match="abort participant body"):
            metta.transaction(body)
        assert PROVIDERS[name] is original
    else:
        metta.transaction(body)
        assert PROVIDERS.get(name) is (replacement if replace else None)
    assert original.calls == [
        ("original", "begin"), ("original", "add"),
        ("original", "rollback" if abort else "commit"),
    ]
    assert original.rows == ([] if abort else [S.participant_value(7)])
    assert replacement.rows == []


def test_replacement_written_in_the_same_transaction_is_a_second_participant(metta, registered):
    """Each registration finishes only the batch that it began."""
    handle, original = registered
    name = str(handle.name)
    replacement = Participant("replacement", original.calls)

    def body():
        handle.add(S.first(1))
        unregister_provider(metta.runtime, name)
        register_provider(metta.runtime, name, replacement)
        handle.add(S.second(2))

    metta.transaction(body)
    assert original.calls == [
        ("original", "begin"), ("original", "add"),
        ("replacement", "begin"), ("replacement", "add"),
        ("replacement", "commit"), ("original", "commit"),
    ]
    assert original.rows == [S.first(1)]
    assert replacement.rows == [S.second(2)]


def test_begin_cannot_replace_the_completion_method_already_captured(metta, registered):
    """All bound operations are selected before begin can mutate descriptors."""
    handle, original = registered
    begin = original.begin

    def mutated_commit():
        original.calls.append(("replacement-method", "commit"))

    def mutate_then_begin():
        original.commit = mutated_commit
        begin()

    original.begin = mutate_then_begin
    metta.transaction(lambda: handle.add(S.captured_method(1)))
    assert original.calls == [("original", "begin"), ("original", "add"), ("original", "commit")]
    assert original.saved == []


def test_a_noncallable_completion_is_refused_before_begin(metta, registered):
    """A stale capability cannot start a batch with an unusable completion."""
    handle, original = registered
    original.commit = None
    with pytest.raises(MettaError, match="begin/commit/rollback"):
        metta.transaction(lambda: handle.add(S.invalid_completion(1)))
    assert original.calls == []
    assert original.saved == []


def test_failed_completion_never_uses_the_replacement(metta, registered):
    """A refusing original remains the named failure and receives no rollback."""
    handle, original = registered
    name = str(handle.name)
    replacement = Participant("replacement", original.calls)
    original.refuse_commit = True

    def body():
        handle.add(S.unfinished(1))
        unregister_provider(metta.runtime, name)
        register_provider(metta.runtime, name, replacement)

    # The provider's own exception is what the caller receives, as for a body
    # abort: the transaction door re-raises the Python original it finds
    # behind the engine error [source: extensions/python/metta/_spaces/scope.py:transaction].
    with pytest.raises(ValueError, match="original participant refused completion"):
        metta.transaction(body)
    assert PROVIDERS[name] is replacement
    assert original.calls == [("original", "begin"), ("original", "add"), ("original", "commit")]
    assert original.saved == [[]]


def test_native_provider_edits_change_the_public_projection(metta, registered):
    """The actual row, including its host value, is the single authority."""
    handle, original = registered
    name = str(handle.name)
    replacement = Participant("edited")
    metta.runtime.must(
        "metta_py_space_atom(Name, Space), metta_transaction(('remove-atom'('&metta', "
        "['@python-provider', ['HostSpace', Space], Original], _), "
        "'add-atom'('&metta', ['@python-provider', ['HostSpace', Space], Replacement], _)))",
        Name=name, Original=original, Replacement=replacement,
    )
    assert PROVIDERS[name] is replacement
    metta.transaction(lambda: handle.add(S.edited_provider(1)))
    assert original.calls == []
    assert replacement.rows == [S.edited_provider(1)]


def test_a_registration_born_in_an_aborted_transaction_is_absent(metta):
    """A Python mapping must not retain a provider whose native birth vanished."""
    name = f"&participant-birth-{uuid4().hex}"
    provider = Participant()

    def body():
        register_provider(metta.runtime, name, provider)
        assert PROVIDERS[name] is provider
        message = "abort registration birth"
        raise ValueError(message)

    with pytest.raises(ValueError, match="abort registration birth"):
        metta.transaction(body)
    assert name not in PROVIDERS
    assert provider.calls == []


def test_an_independent_snapshot_keeps_its_original_provider(metta, registered):
    """An admitted batch completes on its own allocation after another replaces it."""
    handle, original = registered
    name = str(handle.name)
    replacement = Participant("replacement", original.calls)
    begun, replaced = Event(), Event()
    selected = []

    def worker():
        with engine_thread():
            def body():
                handle.add(S.concurrent_participant(1))
                begun.set()
                replaced.wait()
                selected.append(PROVIDERS[name])

            try:
                metta.transaction(body)
            finally:
                begun.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        try:
            begun.wait()
            if future.done():
                future.result()
            unregister_provider(metta.runtime, name)
            register_provider(metta.runtime, name, replacement)
        finally:
            replaced.set()
        future.result()
    assert selected == [original]
    assert PROVIDERS[name] is replacement
    assert original.calls == [("original", "begin"), ("original", "add"), ("original", "commit")]


def test_completed_captures_release_their_bound_methods(metta):
    """Completion leaves the provider held by its registration alone.

    Capture hands Prolog three fresh bound methods; after commit nothing
    engine-side refers to them, so atom collection frees their references
    and the provider's reference count returns to its registered level.
    Atom collection frees the janus blobs, but janus defers each Python
    decrement until its next Prolog-to-Python call, so one py_call follows
    the collectors [measured 2026-09-16: a bound method returned to Prolog
    held its owner's refcount until py_call(builtins:len([]), _) ran after
    garbage_collect_atoms]. Whether the registration's own reference is
    released after unregistration is the reclamation unit's question: a
    Python object passed as a query input is not reliably released by this
    process even after collection, with or without a registration.
    """
    name = f"&participant-gc-{uuid4().hex}"
    calls = []
    provider = Participant(calls=calls)
    methods = ref(provider.begin.__func__)
    register_provider(metta.runtime, name, provider)
    handle = space(name=name)
    handle.atomicity("transactional")
    try:
        gc.collect()
        registered = sys.getrefcount(provider)
        metta.transaction(lambda: handle.add(S.reclaim_participant(1)))
        assert any(isinstance(holder, MethodType) for holder in gc.get_referrers(provider)) or sys.getrefcount(provider) > registered
        gc.collect()
        metta.runtime.must("garbage_collect, garbage_collect_clauses, statistics(agc, Before), garbage_collect_atoms, "
                           "statistics(agc, After), After > Before, py_call(builtins:len([]), _)")
        gc.collect()
        assert not any(isinstance(holder, MethodType) for holder in gc.get_referrers(provider))
        assert sys.getrefcount(provider) == registered
    finally:
        unregister_provider(metta.runtime, name)
        handle.drop()
    assert methods() is not None
    assert calls == [("original", "begin"), ("original", "add"), ("original", "commit")]


def test_failed_rollback_preserves_the_body_error_and_completes_every_original(metta, registered):
    """A broken rollback cannot hide the body error or skip another provider."""
    handle, original = registered
    name = f"&participant-rollback-{uuid4().hex}"
    broken = Participant("broken", original.calls)
    primary = RuntimeError("original transaction body")
    secondary = ValueError("broken rollback")

    def refuse_rollback():
        broken.calls.append(("broken", "rollback"))
        raise secondary

    broken.rollback = refuse_rollback
    register_provider(metta.runtime, name, broken)
    other = space(name=name)
    other.atomicity("transactional")

    def body():
        handle.add(S.original_batch(1))
        other.add(S.broken_batch(2))
        unregister_provider(metta.runtime, str(handle.name))
        register_provider(metta.runtime, str(handle.name), Participant("replacement", original.calls))
        raise primary

    try:
        with pytest.raises(RuntimeError) as caught:
            metta.transaction(body)
        assert caught.value is primary
        assert original.rows == []
        assert original.calls == [
            ("original", "begin"), ("original", "add"),
            ("broken", "begin"), ("broken", "add"),
            ("broken", "rollback"), ("original", "rollback"),
        ]
        assert PROVIDERS[str(handle.name)] is original
        metta.runtime.must(
            "metta_py_space_atom(BrokenName, Broken), "
            "metta_py_space_atom(OriginalName, Original), "
            "metta_foreign_completion(discard, "
            "[completed(Broken, rollback, threw(_)), completed(Original, rollback, ok)])",
            BrokenName=name, OriginalName=str(handle.name),
        )
    finally:
        unregister_provider(metta.runtime, name)
        other.drop()


@pytest.mark.parametrize("reverse", [False, True])
def test_reconciliation_runs_after_original_completion_and_attempts_every_callback(
    metta, registered, reverse,
):
    """A queued host error is reported after the other retained callbacks run."""
    handle, original = registered
    secondary = ValueError("reconciliation refused")

    def broken():
        original.calls.append(("broken", "reconcile"))
        raise secondary

    def final():
        original.calls.append(("last", "reconcile"))

    def body():
        handle.add(S.committed_batch(1))
        callbacks = [("last", final), ("broken", broken)]
        if reverse:
            callbacks.reverse()
        for label, callback in callbacks:
            metta.runtime.must(
                "metta_after_foreign(Label, user:py_call(F:'__call__'(), _))",
                Label=label, F=callback,
            )

    with pytest.raises(ValueError) as caught:
        metta.transaction(body)
    assert caught.value is secondary
    assert original.rows == [S.committed_batch(1)]
    assert original.calls[:3] == [
        ("original", "begin"), ("original", "add"), ("original", "commit"),
    ]
    assert sorted(original.calls[3:]) == [("broken", "reconcile"), ("last", "reconcile")]
