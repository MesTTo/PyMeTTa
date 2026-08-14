"""Purpose: represent lint findings and cache one engine registry snapshot.
Guarantees:
  - each function and arity query crosses the engine once per distinct name
    in a lint pass [tested test_registry_queries_are_native_and_cached_per_name]
  - malformed engine arity rows raise EngineError instead of changing a
    diagnosis [tested test_registry_queries_are_native_and_cached_per_name]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .atoms import Atom
from .errors import EngineError


@dataclass(frozen=True)
class Finding:
    """One diagnostic with its kind, subject, explanation, and evidence."""

    kind: str
    subject: str
    detail: str
    atom: Atom

    def __str__(self) -> str:
        return f"[{self.kind}] {self.subject}: {self.detail}"


class EngineRegistry:
    """One cached view of engine function facts during a lint pass."""

    __slots__ = ("_arities", "_functions", "_runtime")

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime
        self._functions: dict[str, bool] = {}
        self._arities: dict[str, frozenset[int]] = {}

    def is_function(self, name: str) -> bool:
        known = self._functions.get(name)
        if known is None:
            row = self._runtime.once("( fun(F) -> T = true ; T = false )", F=name)
            known = row.get("T") in ("true", True)
            self._functions[name] = known
        return known

    def arities(self, name: str) -> frozenset[int]:
        cached = self._arities.get(name)
        if cached is not None:
            return cached
        row = self._runtime.once("findall(_A, arity(F, _A), L)", F=name)
        raw = row.get("L")
        if not isinstance(raw, (list, tuple)) or any(
            isinstance(value, bool) or not isinstance(value, int) for value in raw
        ):
            raise EngineError(
                f"engine arity registry returned an invalid list for {name!r}: {raw!r}"
            )
        result = frozenset(raw)
        self._arities[name] = result
        return result
