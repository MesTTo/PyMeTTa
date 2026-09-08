"""Purpose: the bounds this seat decides, as `(limit <name> <value>)` rows in
`&metta` once an engine is running, and as validated process settings before
one is.

Every number here used to sit beside whichever door read it: the crossing chunk
cap in this module, the subscription queue bound in `metta.subscribe`, the repr
row count in `metta.results`. A program could read none of them and change none
of them, and each was a `Decides:` line nothing could query. They are one table
now, and boot publishes it into `&metta` as `(limit ...)` rows, so
`!(match &metta (limit $name $value) ($name $value))` is what the bounds are and
`!(add-atom &metta (limit display-rows 5))` is how a program changes one.

Two settings are NOT rows: `stack_limit` and `heartbeat_interval` configure the
SWI runtime in the same call that boots it, which is before `&metta` exists, so
their value has to be here and they freeze once the engine has started.

A bound is read on a hot path -- a cursor reads its chunk cap when it opens --
so the rows are MIRRORED here rather than consulted per read, and the engine
announces every `(limit ...)` write through `seam:catalog_row_changed/2` so
the mirror cannot go stale. Consulting the catalog per read instead cost 21
inferences and 3.2 of the 35 microseconds a one-answer `match` takes.

Assumes:
  - startup settings are configured before the first engine consult [tested
    test_runtime_settings_freeze_after_startup]
Guarantees:
  - configuration updates are validated and applied atomically [tested
    test_configuration_updates_are_atomic]
  - invalid METTA_* environment values stop package import with a named error
    [tested test_configuration_reads_and_validates_environment]
  - every row-backed setting is a `(limit ...)` row once an engine runs, a
    program that rewrites the row changes what the seat reads, and the two
    startup settings are absent from the rows [tested:
    test_the_bounds_are_rows_a_program_can_read_and_replace; commit=WORKTREE]
  - a bound costs no crossing to read after the first, and a row a program
    adds or removes reaches the next read whatever wrote it [tested:
    test_a_bound_read_after_the_first_costs_no_crossing,
    test_a_bound_a_program_rewrites_reaches_the_next_read,
    test_a_bound_this_seat_does_not_know_forgets_every_mirrored_bound;
    commit=WORKTREE]
  - reading a bound costs 0 inferences where the catalog read it replaced cost
    21, and a one-answer `match` is back to what it cost with the bound as a
    module constant [measured 2026-09-08: 24.0 inferences either way, and 33.5
    and 35.5 microseconds as a row against 33.7 and 34.6 as a constant, where
    the catalog read measured 45.1 inferences and 42.0 microseconds;
    command=python extensions/python/benchmarks/probes/bound_row_cost.py --read;
    fixture=a 50-atom space, 20,000 matches per arm, min of five, two runs;
    commit=WORKTREE]
Guarded by: Config._lock protects settings and the startup freeze;
  _MIRROR_LOCK protects the mirror and the change count it moves with.
Decides:
  - stack_limit and heartbeat_interval are held here rather than as rows,
    because they are arguments to the boot that creates the space the rows
    would live in
  - a changed row INVALIDATES its mirrored entry rather than updating it,
    because a removal leaves whatever was written before it standing and only
    the catalog knows what that is
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

__all__ = ["Config", "config"]

_UNSET = object()

#: Every bound, and what each one is for. The comment above a value is its
#: `Decides:` reason, kept beside the number rather than beside whichever door
#: reads it.
#:
#: `chunk_cap` is the largest chunk one crossing carries, for every door that
#: pulls a sequence over a boundary: the engine cursor's janus crossings
#: (`_space_objects.Cursor._refill`, `_space_execution.evaluate_answers`) and
#: the record batches an Arrow capsule hands a consumer (`_arrow.batch_bounds`).
#: Growth is geometric, so the cap only decides where doubling stops, and the
#: sweep says it stops mattering at 16: speedup against a chunk of one, drained
#: at four sizes, 1 / 1.24x / 1.53x / 1.86x / 1.80x / 1.91x / 1.88x / 1.91x for
#: caps 1, 2, 4, 16, 64, 256, 1024, 4096 at ten thousand answers [tested:
#: extensions/python/tests/ch18_performance/test_cursor_chunking.py::test_draining_amortises_the_crossing].
#: Everything from 16 up is one flat band, so this takes the smallest cap
#: comfortably past its start rather than the largest: 64 reaches the whole win
#: while a refill holds a quarter of what 256 would. SQL Server's cursors pick
#: 128 by the same reasoning and Lemire measures 64 as the batch where
#: prefetching stops paying.
#:
#: `subscription_queue` is how many undelivered events a queueing subscription
#: holds before it REFUSES the write, which is a bound rather than a drop
#: because a space is a multiset and a silently dropped event is a fact nothing
#: can recover.
#:
#: `repr_items` is how many items a container's repr shows before it counts the
#: rest, which keeps a notebook cell readable.
# closed-set: decides; policy=every bound this seat decides and its shipped value; reads=limit, which boot publishes this table into and which every read goes through afterwards
_DEFAULTS = {
    "stack_limit": 8_000_000_000,
    "heartbeat_interval": 100_000,
    "declaration_limit": 512,
    "display_rows": 100,
    "chunk_cap": 64,
    "subscription_queue": 10_000,
    "repr_items": 4,
}
# closed-set: decides; policy=which bounds a METTA_* variable sets at startup; reads=none, it is the source
_ENVIRONMENT = {
    "stack_limit": "METTA_STACK_LIMIT",
    "heartbeat_interval": "METTA_HEARTBEAT_INTERVAL",
    "declaration_limit": "METTA_DECLARATION_LIMIT",
    "display_rows": "METTA_DISPLAY_ROWS",
}
_STARTUP_SETTINGS = frozenset({"stack_limit", "heartbeat_interval"})

#: Which settings are published as `(limit <name> <value>)` rows and read back
#: from them. Every setting except the two the boot itself takes, whose value
#: is needed before the space the rows live in exists.
_ROW_BACKED = frozenset(_DEFAULTS) - _STARTUP_SETTINGS

#: The MeTTa spelling of a setting name, which is this package's own map: a
#: name is a name and only its casing changes at the boundary.
_ROW_HEAD = "limit"


def _row_name(setting: str) -> str:
    """`display_rows` as the row's own `display-rows`."""
    return setting.replace("_", "-")


def _positive_integer(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{name} must be a positive integer, got {value!r}"
        raise TypeError(msg)
    if value <= 0:
        msg = f"{name} must be positive, got {value!r}"
        raise ValueError(msg)
    return value


def _environment_value(environment: Mapping[str, str], setting: str) -> int:
    """One setting's starting value: its own METTA_* variable, or the default.

    A bound with no variable of its own is set through `configure()` or through
    its `(limit ...)` row, so there is nothing to read here for it.
    """
    variable = _ENVIRONMENT.get(setting)
    raw = None if variable is None else environment.get(variable)
    if raw is None or variable is None:
        return _DEFAULTS[setting]
    try:
        value = int(raw)
    except ValueError as exc:
        msg = f"{variable} must be a positive integer, got {raw!r}"
        raise ValueError(msg) from exc
    try:
        return _positive_integer(variable, value)
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


class Config:
    """Process-wide settings read by the engine and presentation layer.

    ``stack_limit`` and ``heartbeat_interval`` take effect when the first
    embedded engine starts, then become immutable. ``declaration_limit`` and
    ``display_rows`` are read at each operation and may change at any time.
    """

    def __init__(
        self, environment: Mapping[str, str] | None = None, *, published: bool = False
    ) -> None:
        source = os.environ if environment is None else environment
        self._lock = threading.RLock()
        self._runtime_started = False
        #: Whether this object's bounds are the PROCESS's, published into
        #: `&metta` at boot and read back from there. One object is: the
        #: `config` singleton below. A Config a caller builds is a private
        #: settings bag and must not answer another one's rows, which is what
        #: made a standalone `Config({})` report the running engine's numbers.
        self._published = published
        self._values = {setting: _environment_value(source, setting) for setting in _DEFAULTS}

    def configure(
        self,
        *,
        stack_limit: int | object = _UNSET,
        heartbeat_interval: int | object = _UNSET,
        declaration_limit: int | object = _UNSET,
        display_rows: int | object = _UNSET,
        chunk_cap: int | object = _UNSET,
        subscription_queue: int | object = _UNSET,
        repr_items: int | object = _UNSET,
    ) -> None:
        """Validate and atomically replace the supplied settings.

        A row-backed setting is written to its `(limit ...)` row as well, when
        an engine is running, so the row and this object never say different
        things. Its longhand is the write itself:
        `m.catalog.add(S.limit(S["display-rows"], 5))`.
        """
        supplied = {
            "stack_limit": stack_limit,
            "heartbeat_interval": heartbeat_interval,
            "declaration_limit": declaration_limit,
            "display_rows": display_rows,
            "chunk_cap": chunk_cap,
            "subscription_queue": subscription_queue,
            "repr_items": repr_items,
        }
        updates = {
            name: _positive_integer(name, value)
            for name, value in supplied.items()
            if value is not _UNSET
        }
        with self._lock:
            frozen = [
                name
                for name, value in updates.items()
                if self._runtime_started
                and name in _STARTUP_SETTINGS
                and value != self._values[name]
            ]
            if frozen:
                names = ", ".join(sorted(frozen))
                msg = f"cannot change {names} after the MeTTa runtime has started"
                raise RuntimeError(msg)
            self._values.update(updates)
        if self._published:
            for name, value in updates.items():
                if name in _ROW_BACKED:
                    _write_row(name, value)

    def as_dict(self) -> dict[str, int]:
        """Return an independent snapshot of every setting.

        Row-backed settings answer from their rows when an engine is running,
        so a bound a MeTTa program rewrote reads back here.
        """
        with self._lock:
            held = self._values.copy()
        if not self._published:
            return held
        rows = _read_rows()
        held.update({name: value for name, value in rows.items() if name in held})
        return held

    @contextmanager
    def _startup(self) -> Iterator[tuple[int, int]]:
        """Freeze startup settings only after a successful engine consult."""
        with self._lock:
            values = self._values["stack_limit"], self._values["heartbeat_interval"]
            completed = False
            try:
                yield values
                completed = True
            finally:
                if completed:
                    self._runtime_started = True

    def _get(self, name: str) -> int:
        """One setting: its row when an engine holds one, else what is set here."""
        if self._published and name in _ROW_BACKED:
            standing = _read_row(name)
            if standing is not None:
                return standing
        with self._lock:
            return self._values[name]

    @property
    def stack_limit(self) -> int:
        return self._get("stack_limit")

    @stack_limit.setter
    def stack_limit(self, value: int) -> None:
        self.configure(stack_limit=value)

    @property
    def heartbeat_interval(self) -> int:
        return self._get("heartbeat_interval")

    @heartbeat_interval.setter
    def heartbeat_interval(self, value: int) -> None:
        self.configure(heartbeat_interval=value)

    @property
    def declaration_limit(self) -> int:
        return self._get("declaration_limit")

    @declaration_limit.setter
    def declaration_limit(self, value: int) -> None:
        self.configure(declaration_limit=value)

    @property
    def display_rows(self) -> int:
        return self._get("display_rows")

    @display_rows.setter
    def display_rows(self, value: int) -> None:
        self.configure(display_rows=value)

    @property
    def chunk_cap(self) -> int:
        """The largest chunk one crossing carries; see the table above."""
        return self._get("chunk_cap")

    @chunk_cap.setter
    def chunk_cap(self, value: int) -> None:
        self.configure(chunk_cap=value)

    @property
    def subscription_queue(self) -> int:
        """How many undelivered events a queueing subscription holds."""
        return self._get("subscription_queue")

    @subscription_queue.setter
    def subscription_queue(self, value: int) -> None:
        self.configure(subscription_queue=value)

    @property
    def repr_items(self) -> int:
        """How many items a container's repr shows before counting the rest."""
        return self._get("repr_items")

    @repr_items.setter
    def repr_items(self, value: int) -> None:
        self.configure(repr_items=value)

    def __repr__(self) -> str:
        options = ", ".join(f"{name}={value}" for name, value in self.as_dict().items())
        return f"Config({options})"


#: The catalog space the rows live in, and the two goals that read and replace
#: one. Direct runtime goals rather than `Space.match`, deliberately: a match
#: opens a CURSOR, a cursor asks for its own chunk-cap bound, and that bound is
#: read from here -- the read would call itself forever. One findall over the
#: whole table is also one crossing where a cursor is several.
_CATALOG = "&metta"
_READ_GOAL = f"findall([_N, _V], metta_catalog_row([{_ROW_HEAD}, _N, _V]), Rows)"
#: One bound's rows, which is what every READ asks for: the whole table is for
#: `as_dict` alone, and a cursor asking for its chunk cap should not walk every
#: other bound to find it [measured 2026-09-08: 47 inferences against 69 for
#: the whole-table read, over one cursor's open].
_ONE_GOAL = f"findall(_V, metta_catalog_row([{_ROW_HEAD}, Name, _V]), Values)"


def _runtime():
    """The running engine, or None. Nothing here ever starts one."""
    from . import _engine  # noqa: PLC0415  -- the runtime, which imports this module

    return _engine.active_runtime()


#: This process's mirror of the standing bounds, keyed by this seat's own
#: setting name and holding None for a bound the catalog carries no row for.
#: A hit is the whole read. The ENGINE keeps it in step: shim.pl's
#: `seam:catalog_row_changed/2` clause calls `bound_row_changed` for every
#: `(limit ...)` row that lands or leaves, whoever wrote it, so a MeTTa
#: program's own `!(add-atom &metta (limit chunk-cap 8))` drops the entry it
#: changed and the next read sees 8.
#:
#: Reading the catalog per read instead cost 21 inferences and 3.2 of the 35
#: microseconds a one-answer `match` takes, because a cursor reads its chunk
#: cap when it opens [measured 2026-09-08; command=python
#: extensions/python/benchmarks/probes/bound_row_cost.py --read;
#: fixture=a 50-atom space, 20,000 matches per arm, min of five].
_MIRROR: dict[str, int | None] = {}
#: How many times a bound has changed, and the lock the count and the mirror
#: move under. A filling read does its crossing with neither held and stores
#: what it read only if the count has not moved since it started, so a write
#: that lands on another thread mid-read cannot be overwritten by the value
#: that read began with. The count is an int rather than a flag because two
#: changes either side of one read must not cancel out.
_CHANGES = [0]
_MIRROR_LOCK = threading.Lock()


def bound_row_changed(name: object) -> None:
    """A `(limit <name> ...)` row landed or left; forget what was mirrored.

    The engine calls this, not Python: `seam:catalog_row_changed/2` in
    `shim.pl` is the only caller. It INVALIDATES rather than updating,
    because a removal leaves whatever row was written before it standing and
    only the catalog knows what that is. A name this seat does not know --
    a library's own bound, or the unbound position a pattern write leaves --
    forgets everything, which refreshes a mirror for nothing at worst.
    """
    setting = str(name).replace("-", "_")
    with _MIRROR_LOCK:
        _CHANGES[0] += 1
        if setting in _DEFAULTS:
            _MIRROR.pop(setting, None)
        else:
            _MIRROR.clear()


def _forget_bounds() -> None:
    """Drop the mirror whole: a new engine's rows are not the last one's."""
    with _MIRROR_LOCK:
        _CHANGES[0] += 1
        _MIRROR.clear()


def _fill_bounds(began: int, standing: Mapping[str, int]) -> None:
    """Seed every row-backed bound from one whole-table read.

    Boot does this so the FIRST read in a program is a hit like every other
    one. A read that fills the mirror itself costs 61 inferences rather than
    the steady 21, because it is also the first time its goal crosses, and a
    twin's own first `match` was paying all of it [measured 2026-09-08: 96
    against 35 inferences for the first match in a fresh process, 33 either
    way for the second]. `began` is the change count before the read that
    produced `standing`, so a write that landed during it is not overwritten.
    """
    with _MIRROR_LOCK:
        if _CHANGES[0] != began:
            return
        for setting in _ROW_BACKED:
            _MIRROR[setting] = standing.get(setting)


def _read_row(setting: str) -> int | None:
    """One bound's standing value: the last row written for it, or None.

    The mirror answers every read after the first, which is why a bound may
    be a row at all: a cursor reads its chunk cap when it opens, and a
    crossing there is a crossing per cursor.

    A hit answers without asking whether an engine is running, which it does
    not have to: an entry only exists because a read filled it while one was,
    and `active_runtime()` is set once and never unset, so a process that has
    booted stays booted. Before it has, the mirror is empty and every read
    falls through to the question.
    """
    try:
        return _MIRROR[setting]
    except KeyError:
        pass
    runtime = _runtime()
    if runtime is None:
        return None
    with _MIRROR_LOCK:
        began = _CHANGES[0]
    standing = _standing(setting, runtime)
    value = standing[-1] if standing else None
    with _MIRROR_LOCK:
        if _CHANGES[0] == began:
            _MIRROR[setting] = value
    return value


def _standing(setting: str, runtime=None) -> list[int]:
    """Every value standing for one bound, in the order they were written.

    A space is a multiset, so `!(add-atom &metta (limit display-rows 5))`
    beside the shipped row leaves TWO, and which one is the bound has to be
    decided rather than left to whichever the reader saw first. The LAST is,
    which is the ordinary reading of a write: the most recent one wins, and
    `configure()` leaves exactly one behind.
    """
    if runtime is None:
        runtime = _runtime()
        if runtime is None:
            return []
    answered = runtime.must(_ONE_GOAL, Name=_row_name(setting))["Values"]
    return [
        value
        for value in answered
        if isinstance(value, int) and not isinstance(value, bool)
    ]


def _read_rows(runtime=None) -> dict[str, int]:
    """Every bound the running engine holds, keyed by this seat's own name.

    The runtime is a parameter because `publish` runs INSIDE the Runtime's own
    construction, where `active_runtime()` is still None: asking for it there
    answered an empty table, so boot wrote a row for every bound whether the
    catalog carried it or not.
    """
    if runtime is None:
        runtime = _runtime()
        if runtime is None:
            return {}
    found: dict[str, int] = {}
    for name, value in runtime.must(_READ_GOAL)["Rows"]:
        if isinstance(value, int) and not isinstance(value, bool):
            found[str(name).replace("-", "_")] = value
    return found


def _row_atom(setting: str, value: int):
    """One `(limit <name> <value>)` row as the atom it crosses as."""
    from .atoms import S, ground  # noqa: PLC0415  -- atoms, above this module

    return S[_ROW_HEAD](S[_row_name(setting)], ground(value))


def _write_row(setting: str, value: int) -> None:
    """Replace one bound's rows with one, so the catalog and this object agree."""
    runtime = _runtime()
    if runtime is None:
        return
    standing = _standing(setting)
    if standing == [value]:
        return
    for held in standing:
        runtime.apply_must(
            "metta_py_remove", _CATALOG, _row_atom(setting, held).to_wire()
        )
    runtime.do("metta_py_add", _CATALOG, _row_atom(setting, value).to_wire())


def publish(runtime) -> int:
    """Write every row-backed bound into `&metta`, answering how many landed.

    Called once per engine, after `&metta` exists. A bound the catalog already
    carries is left alone, so a re-consulted engine meets its own rows and a
    program's own override survives.

    It also turns the engine's own announcement on, and SEEDS the mirror from
    what it wrote, so the first bound a program reads is a hit like every one
    after it. Boot is where that read belongs: a program's own first `match`
    was paying for it otherwise, and a first read costs three times a steady
    one because its goal is also crossing for the first time.
    """
    _forget_bounds()
    runtime.must("metta_py_mirror_bounds")
    standing = _read_rows(runtime)
    written = 0
    for setting in sorted(_ROW_BACKED):
        if setting in standing:
            continue

        value = config._values[setting]
        runtime.do("metta_py_add", _CATALOG, _row_atom(setting, value).to_wire())
        standing[setting] = value
        written += 1
    # AFTER the writes, because each of them announced itself and `standing`
    # already carries what they wrote. Nothing else can be writing here:
    # `active_runtime()` is still None, so this engine is not reachable yet.
    with _MIRROR_LOCK:
        began = _CHANGES[0]
    _fill_bounds(began, standing)
    return written


config = Config(published=True)
