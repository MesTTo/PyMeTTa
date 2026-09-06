"""Purpose: validate and hold process-wide MeTTa runtime settings, and the one
crossing-chunk policy number every boundary door doubles up to.
Assumes:
  - startup settings are configured before the first engine consult [tested
    test_runtime_settings_freeze_after_startup]
Guarantees:
  - configuration updates are validated and applied atomically [tested
    test_configuration_updates_are_atomic]
  - invalid METTA_* environment values stop package import with a named error
    [tested test_configuration_reads_and_validates_environment]
Guarded by: Config._lock protects settings and the startup freeze.
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

#: The largest chunk one crossing carries, for every door that pulls a
#: sequence over a boundary: the engine cursor's janus crossings
#: (`_space_objects.Cursor._refill`, `_space_execution.evaluate_answers`) and
#: the record batches an Arrow capsule hands a consumer (`_arrow.batch_bounds`).
#: Growth is geometric, so the cap only decides where doubling stops, and the
#: sweep says it stops mattering at 16: speedup against a chunk of one, drained
#: at four sizes, 1 / 1.24x / 1.53x / 1.86x / 1.80x / 1.91x / 1.88x / 1.91x for
#: caps 1, 2, 4, 16, 64, 256, 1024, 4096 at ten thousand answers [tested:
#: extensions/python/tests/ch18_performance/test_cursor_chunking.py::test_draining_amortises_the_crossing].
#: Everything from 16 up is one flat band, so
#: this takes the smallest cap comfortably past its start rather than the
#: largest: 64 reaches the whole win while a refill holds a quarter of what
#: 256 would. SQL Server's cursors pick 128 by the same reasoning and Lemire
#: measures 64 as the batch where prefetching stops paying.
#: It lives here rather than beside either consumer because a second copy of a
#: measured policy number is a second thing to move.
_CHUNK_CAP = 64

_DEFAULTS = {
    "stack_limit": 8_000_000_000,
    "heartbeat_interval": 100_000,
    "declaration_limit": 512,
    "display_rows": 100,
}
_ENVIRONMENT = {
    "stack_limit": "METTA_STACK_LIMIT",
    "heartbeat_interval": "METTA_HEARTBEAT_INTERVAL",
    "declaration_limit": "METTA_DECLARATION_LIMIT",
    "display_rows": "METTA_DISPLAY_ROWS",
}
_STARTUP_SETTINGS = frozenset({"stack_limit", "heartbeat_interval"})


def _positive_integer(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{name} must be a positive integer, got {value!r}"
        raise TypeError(msg)
    if value <= 0:
        msg = f"{name} must be positive, got {value!r}"
        raise ValueError(msg)
    return value


def _environment_value(environment: Mapping[str, str], setting: str) -> int:
    variable = _ENVIRONMENT[setting]
    raw = environment.get(variable)
    if raw is None:
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

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        source = os.environ if environment is None else environment
        self._lock = threading.RLock()
        self._runtime_started = False
        self._values = {setting: _environment_value(source, setting) for setting in _DEFAULTS}

    def configure(
        self,
        *,
        stack_limit: int | object = _UNSET,
        heartbeat_interval: int | object = _UNSET,
        declaration_limit: int | object = _UNSET,
        display_rows: int | object = _UNSET,
    ) -> None:
        """Validate and atomically replace the supplied settings."""
        supplied = {
            "stack_limit": stack_limit,
            "heartbeat_interval": heartbeat_interval,
            "declaration_limit": declaration_limit,
            "display_rows": display_rows,
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

    def as_dict(self) -> dict[str, int]:
        """Return an independent snapshot of every setting."""
        with self._lock:
            return self._values.copy()

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

    def __repr__(self) -> str:
        options = ", ".join(f"{name}={value}" for name, value in self.as_dict().items())
        return f"Config({options})"


config = Config()
