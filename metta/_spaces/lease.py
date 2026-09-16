"""Purpose: give every live space name one host registration that all its Python handles share.

Assumes: the engine's metta_py_lease/2 row is the authority for a cell's life; a cell
never revives one, and the binding's space_released and lease_aborted callbacks are
the only writers of `reason`.
Guarantees: every handle of one live name shares one cell; a retirement by any party
marks the cell dead after the retiring handle's own cleanup ran; a lease born in a
transaction that aborts is dead when that transaction ends; a collected cell releases
its lease through the deferred engine queue, so rows follow outstanding handles
[tested: test_a_native_drop_marks_every_retained_handle_dead,
test_aliases_share_one_life_and_a_reused_name_starts_another,
test_a_handle_born_in_an_aborted_transaction_is_dead,
test_lease_rows_follow_outstanding_handles; commit=WORKTREE].
Owns resources: one engine lease row per cell, released by retirement or by the
cell's finalizer, never by a native call from the garbage collector. No Python
object crosses into the engine: janus retains a crossed object until atom GC, which
would keep the cell, its handles and the row alive
[source: docs/journal/2026-09-15-foreign-participant-capture.md; commit=WORKTREE].
"""

from __future__ import annotations

import weakref
from typing import Any

from metta._binding.runtime import defer_engine_call


class Cell:
    """One space life as its Python handles see it: alive until the engine says otherwise."""

    __slots__ = ("__weakref__", "lease", "name", "reason")

    def __init__(self, name: Any, lease: int) -> None:
        """Start alive; only the engine's reports below end that."""
        self.name = name
        self.lease = lease
        self.reason: str | None = None

    @property
    def dead(self) -> bool:
        """Whether the engine has reported this life over."""
        return self.reason is not None


# Both maps are weak: the last handle leaving takes its cell, and the finalizer
# registered in attach() releases the engine row on the next crossing.
_BY_NAME: weakref.WeakValueDictionary[Any, Cell] = weakref.WeakValueDictionary()
_BY_LEASE: weakref.WeakValueDictionary[int, Cell] = weakref.WeakValueDictionary()


def attach(runtime: Any, name: Any) -> Cell:
    """Share the live cell for ``name``, or open a lease and start one.

    Opening asserts the row inside the caller's transaction and registers a
    completion that reports an aborted birth to the new cell by lease number.
    """
    cell = _BY_NAME.get(name)
    if cell is not None and not cell.dead:
        return cell
    row = runtime.must("metta_py_lease_open(Space, Lease)", Space=name)
    cell = Cell(name, int(row["Lease"]))
    _BY_NAME[name] = cell
    _BY_LEASE[cell.lease] = cell
    weakref.finalize(cell, defer_engine_call, "metta_py_lease_release", name, cell.lease)
    return cell


def _end(lease: int, reason: str) -> None:
    cell = _BY_LEASE.get(int(lease))
    if cell is not None and not cell.dead:
        cell.reason = reason


def released(lease: int) -> None:
    """The engine retired the space behind ``lease``; every handle of it is dead."""
    _end(lease, "its space was dropped")


def aborted(lease: int) -> None:
    """The transaction that opened ``lease`` did not commit; its space never existed."""
    _end(lease, "its space was created in a transaction that did not commit")
