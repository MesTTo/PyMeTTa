"""Purpose: the engine and the Python side hold nothing for a space life once it is over.

Guarantees: registrations (lease rows, storage caches, exec-module rows, reference
sight and slots), retained completions (retirement witnesses, release bookkeeping,
pending shadow repairs) and Python cells (lease cells, admissions, pending
withdrawals) return to their baseline after thousands of bare handles, temporary
spaces, aborted births, committed retirements, alias releases and a failed close
retried, and a Python object crossed as a query input or raised inside a
callback is released at the reclamation barrier the memory benchmark names,
atom GC followed by a Prolog-to-Python call, which every count here runs to its
fixpoint [tested: test_reclamation; commit=3aa8268da73cbbf54d382458b6cf3173175a0321].
"""

import gc
import weakref

import pytest

from metta import MeTTa, S, Space, foreign
from metta._declare import classes
from metta._errors.errors import MettaError
from metta._spaces import lease

ROW = S.reclaim_value

_ENGINE = (
    "aggregate_all(count, metta_py_lease(_, _), Leases), "
    "( current_predicate(spaces:metta_space_retired/2)"
    " -> aggregate_all(count, spaces:metta_space_retired(_, _), Retiring) ; Retiring = 0 ), "
    "( current_predicate(metta_engine:metta_reference_release_unseen/3)"
    " -> aggregate_all(count, metta_engine:metta_reference_release_unseen(_, _, _), Unseen) ; Unseen = 0 ), "
    "( current_predicate(spaces:'$metta_shadow_repair_pending'/3)"
    " -> aggregate_all(count, spaces:'$metta_shadow_repair_pending'(_, _, _), Pending) ; Pending = 0 ), "
    "aggregate_all(count, spaces:native_storage_module_cache(_, _), Caches), "
    "aggregate_all(count, spaces:metta_exec_module_known(_, _), Known), "
    "aggregate_all(count, metta_engine:metta_reference_seen_space(_, _), Seen), "
    "aggregate_all(count, metta_engine:metta_reference_slot(_, _, _), Slots), "
    "aggregate_all(count, ( current_module(_M), sub_atom(_M, 0, _, _, '$metta_exec:') ), Modules)"
)
_ENGINE_KEYS = ("Leases", "Retiring", "Unseen", "Pending", "Caches", "Known", "Seen", "Slots", "Modules")


def _settle(runtime) -> None:
    """Run reclamation to its fixpoint: nothing Python or the engine can still free.

    A round collects Python cycles, reclaims atoms and drains janus's deferred
    releases: a py_object blob's Py_DECREF waits for atom GC, and then for the
    next Prolog-to-Python call when atom GC ran without the GIL, while a Python
    object that dies may queue an engine release for the next crossing
    [source: janus-swi 1.5.3 janus.c, MyPy_DECREF/py_gil_ensure, as
    extensions/python/benchmarks/memory_scale.py records it]. A round that
    collected no object and reclaimed no atom is the fixpoint.
    """
    reclaimed = int(runtime.must("statistics(agc_gained, N)")["N"])
    for _ in range(64):
        collected = gc.collect()
        row = runtime.must(
            "garbage_collect_atoms, garbage_collect, py_call(builtins:len([]), _Ignored), "
            "statistics(agc_gained, N)"
        )
        gained, reclaimed = int(row["N"]) - reclaimed, int(row["N"])
        if collected == 0 and gained == 0:
            return
    pytest.fail("reclamation did not reach a fixpoint in 64 rounds")


def _counts(context) -> dict[str, int]:
    runtime = context.runtime
    _settle(runtime)
    row = runtime.must(_ENGINE)
    counts = {key: int(row[key]) for key in _ENGINE_KEYS}
    # The context registers the handle it mints and forgets it at that
    # handle's drop; a life ended another way (an alias's drop, an aborted
    # birth) leaves the minted handle registered, dead, one per pooled name,
    # until the name is minted again or the context closes. Those handles
    # hold their cells; the cells are counted apart from them.
    registered_dead = [handle for handle in context._minted.values() if handle.dropped]
    assert len(registered_dead) <= 1, [str(handle._name) for handle in registered_dead]
    counts.update(
        # Every live cell, by lease: the name map keeps only a name's newest
        # cell, so it cannot count the lives a scenario left behind.
        cells=len(lease._BY_LEASE) - len(registered_dead),
        admissions=len(foreign._ADMISSIONS),
        pending_withdrawals=len(classes._PENDING),
    )
    return counts


def _holders(cell) -> list[str]:
    """Who keeps a dead cell alive: the handle types and what refers to each handle."""
    names = []
    for holder in gc.get_referrers(cell):
        if type(holder).__name__ in ("Space", "SpaceHandle"):
            uppers = []
            for up in gc.get_referrers(holder):
                kind = type(up).__name__
                if kind == "frame":
                    uppers.append(f"frame {up.f_code.co_qualname}")
                elif kind == "cell":
                    owners = [getattr(o, "__qualname__", type(o).__name__) for o in gc.get_referrers(up)]
                    uppers.append(f"cell of {owners}")
                elif kind in ("list", "tuple", "dict"):
                    owners = [getattr(o, "__qualname__", type(o).__name__) for o in gc.get_referrers(up)][:4]
                    uppers.append(f"{kind}({len(up)}) held by {owners}")
                else:
                    uppers.append(kind)
            names.append(f"{type(holder).__name__} held by {uppers}")
    return names


def _same_but_modules(before: dict[str, int], after: dict[str, int], modules_growth: int) -> None:
    moved = {key: (before[key], after[key]) for key in before if key != "Modules" and before[key] != after[key]}
    cells = [(str(cell.name), cell.lease, cell.dead, _holders(cell)) for cell in lease._BY_LEASE.values() if cell.dead]
    assert not moved, f"counts moved across the scenario: {moved}; dead cells now {cells}"
    assert after["Modules"] - before["Modules"] <= modules_growth, (before["Modules"], after["Modules"])


def _retained(context) -> dict[str, bool]:
    """The handles the context still registers, by name, and whether each life is over."""
    return {name: handle.dropped for name, handle in context._minted.items()}


def test_bare_handles_leave_nothing_behind():
    """Thousands of transient handles of one name settle to the baseline."""
    with MeTTa() as context:
        rt = context.runtime
        before = _counts(context)
        for _ in range(2000):
            Space("&reclaim-bare", _runtime=rt)
        after = _counts(context)
        _same_but_modules(before, after, modules_growth=1)


def test_temporary_spaces_leave_nothing_behind():
    """Hundreds of anonymous spaces created, written and dropped settle to the baseline."""
    with MeTTa() as context:
        first = context.space()
        first.add(ROW(0))
        first.drop()
        del first
        before = _counts(context)
        for index in range(300):
            space = context.space()
            space.add(ROW(index))
            space.drop()
            assert space.dropped
        del space
        after = _counts(context)
        _same_but_modules(before, after, modules_growth=0)
        assert _retained(context) == {}, "a dropped minted space leaves the context's registry"


def test_aborted_births_leave_nothing_behind():
    """A space born in a transaction that aborts leaves no row, cache, cell or module behind."""
    with MeTTa() as context:
        home = context.self
        before = _counts(context)
        handles = []

        def body():
            handles.append(context.space())
            handles[-1].add(ROW(1))
            msg = "rollback-birth"
            raise RuntimeError(msg)

        for _ in range(200):
            with pytest.raises(RuntimeError, match="rollback-birth"):
                home.transaction(body)
        assert all(handle.dropped for handle in handles)
        handles.clear()
        after = _counts(context)
        _same_but_modules(before, after, modules_growth=0)


def test_committed_retirements_leave_nothing_behind():
    """Hundreds of drops inside committed transactions settle to the baseline."""
    with MeTTa() as context:
        home = context.self
        warm = context.space()
        home.transaction(warm.drop)
        del warm
        before = _counts(context)
        for index in range(200):
            space = context.space()
            space.add(ROW(index))
            home.transaction(space.drop)
            assert space.dropped
        del space
        after = _counts(context)
        _same_but_modules(before, after, modules_growth=0)


def test_alias_release_leaves_nothing_behind():
    """Two handles of one name, dropped through one of them, leave one dead life and no rows."""
    with MeTTa() as context:
        warm = context.space()
        Space(warm).drop()
        del warm
        before = _counts(context)
        for index in range(200):
            holder = context.space()
            alias = Space(holder)
            holder.add(ROW(index))
            alias.drop()
            assert holder.dropped and alias.dropped
        del holder, alias
        after = _counts(context)
        _same_but_modules(before, after, modules_growth=0)


def test_a_failed_close_retried_leaves_nothing_behind(tmp_path, monkeypatch):
    """A backing whose close fails once, then succeeds on the retried drop, settles to the baseline."""
    with MeTTa() as context:
        warm = context.space(journal=tmp_path / "warm.jnl", schema={"edge": 2})
        warm.drop()
        del warm
        before = _counts(context)
        space = context.space(journal=tmp_path / "retained.jnl", schema={"edge": 2})
        space.add(S.edge(S.a, S.b))
        backing = space._backing
        close_calls = []
        original_close = type(backing).close

        def close(provider):
            close_calls.append(provider)
            if len(close_calls) == 1:
                msg = "injected backing close failure"
                raise OSError(msg)
            return original_close(provider)

        with monkeypatch.context() as patch:
            patch.setattr(type(backing), "close", close)
            with pytest.raises(OSError, match="injected backing close failure"):
                space.drop()
            with pytest.raises(MettaError, match=r"call drop\(\) again"):
                space.add(S.edge(S.c, S.d))
            space.drop()
        assert space.dropped
        close_calls.clear()
        del space, backing
        # The injected error crossed the engine inside the completion callback
        # and came back as itself; its traceback holds the handle until the
        # blob that carried it across is released at the barrier the counts run.
        after = _counts(context)
        _same_but_modules(before, after, modules_growth=0)


class _Crossed:
    """A Python object with no meaning to the engine, handed over as a query input."""


def test_a_crossed_python_object_is_released_at_the_reclamation_barrier():
    """An input object is held by its blob until atom GC and a Prolog-to-Python call drain the queue.

    Janus defers a blob's Py_DECREF when atom GC does not hold the GIL and
    drains that queue at the next py_gil_ensure, so a no-output Python call
    is the observable barrier [source: janus-swi 1.5.3 janus.c,
    MyPy_DECREF/py_gil_ensure, as extensions/python/benchmarks/memory_scale.py
    records it].
    """
    with MeTTa() as context:
        rt = context.runtime
        refs = []
        for _ in range(200):
            crossed = _Crossed()
            refs.append(weakref.ref(crossed))
            assert rt.must("py_is_object(Obj) -> Held = true ; Held = false", Obj=crossed)["Held"] == "true"
            del crossed
        gc.collect()
        assert all(ref() is not None for ref in refs), "a blob holds its object until the barrier"
        _settle(rt)
        survivors = [index for index, ref in enumerate(refs) if ref() is not None]
        holders = []
        for holder in (gc.get_referrers(refs[survivors[0]]()) if survivors else ()):
            owners = [type(up).__name__ for up in gc.get_referrers(holder) if type(up).__name__ != "frame"]
            holders.append(f"{type(holder).__name__}({len(holder) if hasattr(holder, '__len__') else '?'}) held by {owners}")
        assert not survivors, f"crossed objects {survivors} survived the barrier; holders of the first: {holders}"


def test_a_callback_exception_is_released_at_the_reclamation_barrier():
    """An exception a callback raised into the engine dies with the blob that carried it.

    The ball crosses back as itself and its traceback holds every frame below
    the callback, so a host that kept the exception kept those frames and what
    they reference: janus-swi 1.5.3 as shipped never released what PyErr_Fetch
    handed its check_error. This control states the requirement the tree's
    host must meet [docs/host-workarounds.md, janus-callback-exception-leak].
    """
    with MeTTa() as context:
        rt = context.runtime
        home = context.self
        refs = []

        def body():
            error = RuntimeError("rollback-callback")
            error.token = _Crossed()
            refs.append(weakref.ref(error.token))
            raise error

        for _ in range(50):
            with pytest.raises(RuntimeError, match="rollback-callback"):
                home.transaction(body)
        _settle(rt)
        survivors = [index for index, ref in enumerate(refs) if ref() is not None]
        assert not survivors, (
            f"callback exceptions {survivors} survived the barrier: the host keeps what a"
            " callback raised; see docs/host-workarounds.md, janus-callback-exception-leak"
        )
