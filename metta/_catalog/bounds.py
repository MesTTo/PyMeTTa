"""Purpose: the bounds this seat decides, as `(limit <name> <value>)` rows in
`&metta` once an engine is running, and as validated process settings before
one is.

Every number here used to sit beside whichever door read it: the crossing chunk
cap in this module, the subscription queue bound in `metta.subscribe`, the repr
row count in `metta._spaces.results`. A program could read none of them and change none
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
  - a setting declaration supplies validation, environment input, help and
    generated configure parameters [tested:
    test_setting_declaration_reaches_every_projection; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
  - omitted configuration values retain precise integer parameter types
    [tested: test_setting_configuration_preserves_the_public_value_type; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
  - configuration writes roll back as a unit, including their shared mirror
    [tested: test_configuration_publication_failure_restores_every_setting,
    test_configuration_rows_and_mirror_follow_outer_rollback; commit=8358dfc233bf299bb23eceddd94593a62372fe4b]
  - independent native engines on one Python thread keep the mirror suspended
    until every pending owner finishes [tested:
    test_bound_watches_transfer_until_outer_completion; commit=8358dfc233bf299bb23eceddd94593a62372fe4b]
  - invalid METTA_* environment values stop package import with a named error
    [tested test_configuration_reads_and_validates_environment]
  - every row-backed setting is a `(limit ...)` row once an engine runs, a
    program that rewrites the row changes what the seat reads, and the two
    startup settings are absent from the rows [tested:
    test_the_bounds_are_rows_a_program_can_read_and_replace; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
  - a bound costs no crossing to read after the first, and a row a program
    adds or removes reaches the next read whatever wrote it [tested:
    test_a_bound_read_after_the_first_costs_no_crossing,
    test_a_bound_a_program_rewrites_reaches_the_next_read,
    test_a_bound_this_seat_does_not_know_forgets_every_mirrored_bound;
    commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
  - reading a bound costs 0 inferences where the catalog read it replaced cost
    21, and a one-answer `match` is back to what it cost with the bound as a
    module constant [measured 2026-09-08: 24.0 inferences either way, and 33.5
    and 35.5 microseconds as a row against 33.7 and 34.6 as a constant, where
    the catalog read measured 45.1 inferences and 42.0 microseconds;
    command=python extensions/python/benchmarks/probes/bound_row_cost.py --read;
    fixture=a 50-atom space, 20,000 matches per arm, min of five, two runs;
    commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58]
Guarded by: Config._lock protects settings and the startup freeze;
  _MIRROR_LOCK protects the mirror, its change count and pending writers.
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
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, overload

from metta._errors.errors import EngineError, MettaError
from metta._lazy import lazy

__all__ = ["Config", "config"]

# An enum singleton keeps an omitted argument distinct from every input type.
# https://github.com/python/peps/blob/b39aefe6614b4e8a925d07c4b3ed47e147236dbe/peps/pep-0484.rst#support-for-singleton-types-in-unions
class _Unset(Enum):
    """A setting omitted from a configure call."""

    token = 0


_UNSET = _Unset.token

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


class Setting:
    """One integer bound, including its validation and startup policy.

    Python calls __set_name__ when the owning class is built. Descriptor
    discovery follows the MRO, including a subclass that shadows a setting.
    https://docs.python.org/3.12/howto/descriptor.html#customized-names
    """

    def __init__(
        self, default: int, documentation: str, *, environment: str | None = None,
        startup: bool = False,
        validate: Callable[[str, Any], int] = _positive_integer,
    ) -> None:
        self.default = default
        self.__doc__ = documentation
        self.environment = environment
        self.startup = startup
        self.validate = validate
        self.name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        if self.name and self.name != name:
            msg = f"setting {self.name!r} cannot also be named {name!r}"
            raise TypeError(msg)
        self.name = name
        self.validate(name, self.default)

    @overload
    def __get__(self, instance: None, owner: type | None = None) -> Setting: ...

    @overload
    def __get__(self, instance: Config, owner: type | None = None) -> int: ...

    def __get__(self, instance: Config | None, owner: type | None = None) -> Setting | int:
        return self if instance is None else instance._get(self.name)

    def __set__(self, instance: Config, value: int) -> None:
        instance._configure({self.name: value})

    def initial(self, environment: Mapping[str, str]) -> int:
        """Read this declaration's environment input, or its validated default."""
        raw = None if self.environment is None else environment.get(self.environment)
        if raw is None:
            return self.validate(self.name, self.default)
        try:
            value = int(raw)
        except ValueError as exc:
            msg = f"{self.environment} must be a positive integer, got {raw!r}"
            raise ValueError(msg) from exc
        try:
            return self.validate(self.environment or self.name, value)
        except (TypeError, ValueError) as exc:
            raise ValueError(str(exc)) from exc


def settings(owner: type) -> Mapping[str, Setting]:
    """Read effective descriptors without invoking them or assuming slots."""
    members: dict[str, Any] = {}
    for base in reversed(owner.__mro__):
        members.update(vars(base))
    return MappingProxyType({
        name: field for name, field in members.items() if isinstance(field, Setting)
    })


class Config:
    """Process-wide settings read by the engine and presentation layer.

    ``stack_limit`` and ``heartbeat_interval`` take effect when the first
    embedded engine starts, then become immutable. ``declaration_limit`` and
    ``display_rows`` are read at each operation and may change at any time.
    """

    stack_limit = Setting(
        8_000_000_000, "Maximum SWI stack size in bytes.",
        environment="METTA_STACK_LIMIT", startup=True,
    )
    heartbeat_interval = Setting(
        100_000, "Engine inferences between Python signal checks.",
        environment="METTA_HEARTBEAT_INTERVAL", startup=True,
    )
    declaration_limit = Setting(
        512, "Maximum combinations expanded by one declaration.",
        environment="METTA_DECLARATION_LIMIT",
    )
    display_rows = Setting(
        100, "Maximum rows shown in a result display.",
        environment="METTA_DISPLAY_ROWS",
    )
    chunk_cap = Setting(64, "Maximum items carried by one boundary refill.")
    subscription_queue = Setting(10_000, "Undelivered events held before refusing a write.")
    repr_items = Setting(4, "Items shown before a container representation counts the rest.")

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
        self._settings = settings(type(self))
        self._values = {name: field.initial(source) for name, field in self._settings.items()}

    # begin generated configure (tools/boundsgen.py; source=Setting declarations)
    def configure(
        self,
        *,
        stack_limit: int | _Unset = _UNSET,
        heartbeat_interval: int | _Unset = _UNSET,
        declaration_limit: int | _Unset = _UNSET,
        display_rows: int | _Unset = _UNSET,
        chunk_cap: int | _Unset = _UNSET,
        subscription_queue: int | _Unset = _UNSET,
        repr_items: int | _Unset = _UNSET,
    ) -> None:
        """Validate every supplied setting and replace its local or catalog value.

        Live values use one engine transaction. An enclosing transaction
        owns its commit; private configurations only change their own bag.
        """
        self._configure({
            "stack_limit": stack_limit,
            "heartbeat_interval": heartbeat_interval,
            "declaration_limit": declaration_limit,
            "display_rows": display_rows,
            "chunk_cap": chunk_cap,
            "subscription_queue": subscription_queue,
            "repr_items": repr_items,
        })
    # end generated configure

    def _configure(self, supplied: Mapping[str, object]) -> None:
        """Validate every value before replacing the local bag or catalog rows."""
        updates = {
            name: self._settings[name].validate(name, value)
            for name, value in supplied.items() if value is not _UNSET
        }
        if not updates:
            return

        def apply() -> None:
            with self._lock:
                frozen = [
                    name for name, value in updates.items()
                    if (self._runtime_started or runtime is not None) and self._settings[name].startup
                    and value != self._values[name]
                ]
                if frozen:
                    names = ", ".join(sorted(frozen))
                    msg = f"cannot change {names} after the MeTTa runtime has started"
                    raise RuntimeError(msg)
                if runtime is None:
                    self._values.update(updates)
                else:
                    # Live values belong to the engine. Keeping a second local
                    # copy would survive an enclosing transaction's rollback.
                    for name, value in updates.items():
                        if not self._settings[name].startup:
                            _write_row(name, value)

        runtime = _runtime() if self._published else None
        if runtime is None:
            apply()
            return
        # Acquire the engine before the settings lock: callbacks may configure
        # while already holding the engine. SWI owns nesting and row rollback.
        # https://www.swi-prolog.org/pldoc/man?predicate=transaction/1
        with runtime._relational_lock():
            try:
                runtime.must("metta_py_transaction(F, R)", F=apply)
            except MettaError as error:
                term = getattr(error.__cause__, "term", None)
                original = runtime._original_python_error(term, base=BaseException) if term is not None else None
                if original is not None and original is not error:
                    raise original from error
                raise

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
        if self._published and not self._settings[name].startup:
            standing = _read_row(name)
            if standing is not None:
                return standing
        with self._lock:
            return self._values[name]

    def __repr__(self) -> str:
        options = ", ".join(f"{name}={value}" for name, value in self.as_dict().items())
        return f"Config({options})"


# Derived views retained for catalog inspection; the descriptors own policy.
_SETTINGS = settings(Config)
_DEFAULTS = MappingProxyType({name: field.default for name, field in _SETTINGS.items()})
_ENVIRONMENT = MappingProxyType({name: field.environment for name, field in _SETTINGS.items() if field.environment})
_STARTUP_SETTINGS = frozenset(name for name, field in _SETTINGS.items() if field.startup)
_ROW_BACKED = frozenset(name for name, field in _SETTINGS.items() if not field.startup)


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


def _runtime() -> _binding.runtime.Runtime | None:
    """The running engine, or None. Nothing here ever starts one."""
    return lazy('metta._binding.runtime').active_runtime()


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
# Independent native engines can nest on the same Python thread. Keep their
# multiplicity so an inner engine finishing cannot release the outer mirror.
_PENDING_TRANSACTIONS: dict[int, int] = {}


def bound_transaction_started() -> None:
    """Suspend shared cache fills until this writer's outer transaction ends."""
    with _MIRROR_LOCK:
        owner = threading.get_ident()
        _PENDING_TRANSACTIONS[owner] = _PENDING_TRANSACTIONS.get(owner, 0) + 1
        _CHANGES[0] += 1
        _MIRROR.clear()


def bound_transaction_finished() -> None:
    """Forget both committed and discarded views before reads can cache again."""
    with _MIRROR_LOCK:
        owner = threading.get_ident()
        remaining = _PENDING_TRANSACTIONS[owner] - 1
        if remaining:
            _PENDING_TRANSACTIONS[owner] = remaining
        else:
            del _PENDING_TRANSACTIONS[owner]
        _CHANGES[0] += 1
        _MIRROR.clear()



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
        if setting in config._settings:
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
        for setting, field in config._settings.items():
            if not field.startup:
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
    if not _PENDING_TRANSACTIONS:
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
        if _CHANGES[0] == began and not _PENDING_TRANSACTIONS:
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
    from metta._atoms.factories import S, ground  # noqa: PLC0415  -- atoms, above this module

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
    if not runtime.do("metta_py_add", _CATALOG, _row_atom(setting, value).to_wire()):
        msg = f"the engine refused setting {setting!r}"
        raise EngineError(msg)


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
    for setting, field in sorted(config._settings.items()):
        if field.startup:
            continue
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

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta._binding.runtime  # noqa: F401 -- child of the annotation namespace
if TYPE_CHECKING:
    from metta import _binding
else:
    _binding = lazy('metta._binding')
