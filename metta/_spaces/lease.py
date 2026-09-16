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
test_lease_rows_follow_outstanding_handles; commit=a9b0ddb6db7f4837e1910b3e796ebee15a9bd81d].
Guarantees: a retirement the engine performed on its own reconciles the class
programs living in or borrowing from the space through the same hook
[tested: test_a_native_retirement_reconciles_the_class_records; commit=3aa8268da73cbbf54d382458b6cf3173175a0321].
Guarantees: an anonymous name outside a lifetime scope returns to the pool when
its life ends, whichever handle ended it, because `Cell.ephemeral` is the
life's property rather than one handle's
[tested: test_alias_release_leaves_nothing_behind; commit=3aa8268da73cbbf54d382458b6cf3173175a0321].
Owns resources: one engine lease row per cell, released by retirement or by the
cell's finalizer, never by a native call from the garbage collector. No Python
object crosses into the engine: janus retains a crossed object until atom GC, which
would keep the cell, its handles and the row alive
[source: docs/journal/2026-09-15-foreign-participant-capture.md; commit=a9b0ddb6db7f4837e1910b3e796ebee15a9bd81d].
"""

from __future__ import annotations

import weakref
from typing import Any

from metta._binding.runtime import defer_engine_call
from metta._lazy import lazy


class Cell:
    """One space life as its Python handles see it: alive until the engine says otherwise."""

    __slots__ = ("__weakref__", "ephemeral", "lease", "name", "reason")

    def __init__(self, name: Any, lease: int) -> None:
        """Start alive; only the engine's reports below end that."""
        self.name = name
        self.lease = lease
        self.reason: str | None = None
        # An anonymous name outside a lifetime scope returns to the pool when
        # the life ends. The life's property, not one handle's: an alias that
        # drops the space pools the name as the minting handle would have.
        self.ephemeral = False

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
    """The engine retired the space behind ``lease``; every handle of it is dead.

    A class program living in or borrowing from the space reconciles here
    too, so a retirement the engine performed on its own (a native or MeTTa
    drop) withdraws the Python records the way a handle's drop does.
    """
    cell = _BY_LEASE.get(int(lease))
    _end(lease, "its space was dropped")
    if cell is not None:
        lazy('metta._declare.classes').home_retired(str(cell.name))


def aborted(lease: int) -> None:
    """The transaction that opened ``lease`` did not commit; its space never existed."""
    _end(lease, "its space was created in a transaction that did not commit")
