"""Purpose: snapshot Python ContextVars for engine and thread spawn boundaries.

Guarantees:
  - each token owns one independent ``contextvars.Context`` captured at launch,
    and callbacks for that token observe changes made by earlier callbacks in
    the same child computation [tested:
    test_context_snapshot_crosses_every_spawn_door_including_thread_workers;
    commit=WORKTREE]
  - a released token cannot be entered again [tested:
    test_context_snapshot_crosses_every_spawn_door_including_thread_workers,
    test_context_release_linearizes_before_a_waiting_entry; commit=WORKTREE]
Owns resources:
  - token entries from ``snapshot`` or ``fork`` until ``release``; scheduler
    settlement and structured thread joins release them on every exit path
    [tested: test_context_snapshot_crosses_every_spawn_door_including_thread_workers,
    test_context_release_linearizes_before_a_waiting_entry; commit=WORKTREE].
Guarded by:
  - ``_LOCK`` protects the registry and each entry's reentrant lock prevents
    the same Context from being entered concurrently by two carrier threads.
"""

from __future__ import annotations

import contextvars
import itertools
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    context: contextvars.Context
    lock: threading.RLock
    released: bool = False


_LOCK = threading.RLock()
_TOKENS = itertools.count(1)
_CONTEXTS: dict[int, _Entry] = {}
_ACTIVE: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "petta_spawn_context_token",
    default=None,
)


def _store(context: contextvars.Context) -> int:
    token = next(_TOKENS)
    with _LOCK:
        _CONTEXTS[token] = _Entry(context, threading.RLock())
    return token


def _retained_entry(token: int) -> _Entry:
    with _LOCK:
        return _CONTEXTS[token]


def _require_retained(token: int, entry: _Entry) -> None:
    if entry.released:
        raise KeyError(token)


def snapshot() -> int:
    """Capture the caller's current ContextVars under one opaque token."""
    return _store(contextvars.copy_context())


def snapshot_many(count: int) -> list[int]:
    """Capture one independent child Context for each parallel branch."""
    if count < 0:
        msg = f"a context branch count cannot be negative: {count}"
        raise ValueError(msg)
    parent = contextvars.copy_context()
    return [_store(parent.copy()) for _ in range(count)]


def fork(token: int | None) -> int:
    """Copy a retained child context, or the current context when absent."""
    if token is None:
        return snapshot()
    entry = _retained_entry(token)
    with entry.lock:
        _require_retained(token, entry)
        return _store(entry.context.copy())


def fork_many(token: int | None, count: int) -> list[int]:
    """Copy one parent into independent Contexts for parallel child branches."""
    if count < 0:
        msg = f"a context branch count cannot be negative: {count}"
        raise ValueError(msg)
    if token is None:
        return snapshot_many(count)
    entry = _retained_entry(token)
    with entry.lock:
        _require_retained(token, entry)
        return [_store(entry.context.copy()) for _ in range(count)]


def release(token: int | None) -> bool:
    """Drop one retained Context, idempotently."""
    if token is None:
        return False
    with _LOCK:
        entry = _CONTEXTS.pop(token, None)
    if entry is None:
        return False
    with entry.lock:
        entry.released = True
    return True


def release_many(tokens: list[int]) -> None:
    """Drop every token created for one structured parallel operation."""
    for token in tokens:
        release(token)


def run[R](token: int | None, fn: Callable[..., R], /, *args: Any, **kwargs: Any) -> R:
    """Call inside the retained child Context.

    Recursive host calls already execute inside the requested Context and run
    directly. Re-entering an active ``Context`` is forbidden by Python, while
    the direct call has exactly the inherited dynamic scope the nested call
    needs.
    """
    if token is None or _ACTIVE.get() == token:
        return fn(*args, **kwargs)
    entry = _retained_entry(token)

    def invoke() -> R:
        active = _ACTIVE.set(token)
        try:
            return fn(*args, **kwargs)
        finally:
            _ACTIVE.reset(active)

    with entry.lock:
        _require_retained(token, entry)
        return entry.context.run(invoke)


def context_copy(token: int) -> contextvars.Context:
    """Copy a retained Context for an asyncio Task's independent lifetime."""
    entry = _retained_entry(token)
    with entry.lock:
        _require_retained(token, entry)
        return entry.context.copy()
