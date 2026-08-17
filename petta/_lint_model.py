"""Purpose: represent lint findings and cache one engine registry snapshot.
Assumes:
  - translator.pl's metta_translated_head/1 answers true for every head the
    translator compiles instead of a function defining it, across both of
    its routes [source src/translator.pl:686]
Guarantees:
  - each function, special-form and arity query crosses the engine once per
    distinct name in a lint pass [tested
    test_registry_queries_are_native_and_cached_per_name]
  - a head the translator compiles is known to the registry even though it
    answers false to fun/1 [tested test_a_special_form_is_a_known_head]
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

    __slots__ = ("_arities", "_functions", "_runtime", "_special", "_tabled")

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime
        self._functions: dict[str, bool] = {}
        self._special: dict[str, bool] = {}
        self._arities: dict[str, frozenset[int]] = {}
        self._tabled: frozenset[str] | None = None

    def tabled(self) -> frozenset[str]:
        """The function names tabled right now, in any space.

        lib_tabling reflects each live declaration into &petta as a
        (tabled Space Name Arity) fact, so this is one query rather than a
        walk. A space with tabling never loaded holds none and answers the
        empty set, which is why the query is over &petta and not over a
        predicate that would not exist.
        """
        if self._tabled is None:
            row = self._runtime.once(
                "findall(_N, 'get-atoms'('&petta', [tabled, _S, _N, _A]), L)"
            )
            raw = row.get("L")
            names = raw if isinstance(raw, (list, tuple)) else []
            self._tabled = frozenset(str(name) for name in names)
        return self._tabled

    def is_function(self, name: str) -> bool:
        known = self._functions.get(name)
        if known is None:
            row = self._runtime.once("( fun(F) -> T = true ; T = false )", F=name)
            known = row.get("T") in ("true", True)
            self._functions[name] = known
        return known

    def is_special_form(self, name: str) -> bool:
        """Whether the translator compiles this head rather than equations defining it.

        fun/1 alone is not the question "does anything give this head
        meaning". A special form is compiled by the translator, and most are
        never registered as functions: of the 47 heads translate_special_dl/5
        carries, 29 answer false to fun/1, `if`, `case`, `collapse`, `unify`,
        `chain`, `once` and `forall` among them, and the 6 heads
        rewrite_streamops/2 carries answer false as well [measured
        2026-08-17]. The engine already asks this question for its own
        reasons, and metta_translated_head/1 reads both sets of clause heads
        rather than keeping a list, so a form added to the translator is
        covered the day it is added.
        """
        known = self._special.get(name)
        if known is None:
            row = self._runtime.once(
                "( metta_translated_head(F) -> T = true ; T = false )", F=name
            )
            known = row.get("T") in ("true", True)
            self._special[name] = known
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
